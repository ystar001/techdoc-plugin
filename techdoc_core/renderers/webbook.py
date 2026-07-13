"""웹북(Web Book) 렌더러 — 카드 JSON → file:// 정적 다중 페이지 HTML (LLM 0회).

자식 프로젝트마다 복붙되던 `build_webbook.py`를 plugin으로 승격 (F52, 워크스트림 A).
routing_config(F21)로 Part 버킷팅, split 카드는 parent_id로 병합(F13), 기존 렌더러를
재사용한다: 트리/그룹핑은 `markdown_tree`(F15·F17), md→html은 `webbook_md2html`
(수식 F38·mermaid F48 보호 포함).

디자인: 테마 선택식(`--theme`) — 구조(사이드바·표지·지면 시트·검색·pager)는 공유,
색 팔레트만 테마로 교체. premium(다크 에디토리얼)·light(정갈 라이트)·slate(다크) 3종.

출력: output_dir/
  ├── index.html                (표지 + 전체 목차)
  ├── assets/{webbook.css, webbook.js, search-index.js}
  └── <Part-dir>/<card_id>.html  (Part별 카드/병합 페이지)

단일 파일 render(`scripts.render`)와 독립 — opt-in 경로.
"""
from __future__ import annotations

import html as _html
import json
import re
from pathlib import Path

from techdoc_core.formal_blocks import render_formal_blocks
from techdoc_core.localize import localize_terms
from techdoc_core.renderers.markdown_tree import (
    MarkdownTreeExporter,
    _card_title,
    bucket_cards,
    group_by_parent,
    load_card,
    render_card_md,
    render_merged_md,
    safe_dirname,
)
from techdoc_core.renderers.webbook_md2html import md_to_html
from techdoc_core.routing_config import DEFAULT_ROUTING

# ── 테마(색 팔레트) — 구조는 _STRUCT 공유, :root 변수만 교체 ──────────
_RADIAL_HERO = ("radial-gradient(1200px 500px at 78% -10%,var(--accent-soft),transparent 60%),"
                "radial-gradient(900px 500px at 0% 110%,rgba(199,154,61,.12),transparent 55%),var(--ink)")
_THEMES: dict[str, str] = {
    # 기존 웹북 결과물 디자인 — 의성 스마트농업 CI 그린 리포트 (기본)
    "classic": """:root{
  --ink:#0e3a26;--ink-2:#164a32;--ink-line:#1e5238;--ink-fg:#d7e8dd;--ink-mut:#9fc0ae;
  --page:#fafcfc;--sheet:#fff;--soft:#f0f6f3;--line:#dde7e6;
  --fg:#3c3c3b;--mut:#6e6e6c;--heading:#0e3a26;
  --accent:#147646;--accent-2:#009e4d;--gold:#baa660;--accent-soft:rgba(0,158,77,.10);
  --th-bg:#147646;--th-fg:#ffffff;--nav-active-fg:#fff;--hero-fg:#fff;
  --pre-bg:#0e3a26;--pre-fg:#dfeee6;--code-fg:#147646;
  --hero-bg:linear-gradient(135deg,#0e3a26 0%,#147646 52%,#009e4d 100%);}""",
    # 프리미엄 다크 에디토리얼 (먹 + 청록 + 골드)
    "premium": """:root{
  --ink:#0c0f16;--ink-2:#141924;--ink-line:#232a38;--ink-fg:#e9edf4;--ink-mut:#8b95a7;
  --page:#eceef2;--sheet:#fff;--soft:#f6f7f9;--line:#e6e9ef;
  --fg:#171b23;--mut:#5f6875;--heading:#0f1420;
  --accent:#0e9384;--accent-2:#12b3a0;--gold:#c79a3d;--accent-soft:rgba(14,147,132,.10);
  --th-bg:#0c0f16;--th-fg:#eef2f8;--nav-active-fg:#fff;--hero-fg:#fff;
  --pre-bg:#0e131c;--pre-fg:#dfe6f0;--code-fg:#b0492e;--hero-bg:%RADIAL%;}""",
    # 정갈한 라이트 (백지 + 네이비블루 + 앰버) — 공공문서 정석
    "light": """:root{
  --ink:#f5f7fb;--ink-2:#eef1f7;--ink-line:#e3e8f0;--ink-fg:#1a2130;--ink-mut:#6b7688;
  --page:#eef1f5;--sheet:#fff;--soft:#f6f8fb;--line:#e6eaf1;
  --fg:#1a2130;--mut:#5c6676;--heading:#0f1626;
  --accent:#2f5fe0;--accent-2:#4a76ef;--gold:#b7791f;--accent-soft:rgba(47,95,224,.10);
  --th-bg:#243244;--th-fg:#f2f5fa;--nav-active-fg:#12294f;--hero-fg:#141b2b;
  --pre-bg:#101725;--pre-fg:#dbe4f2;--code-fg:#b0492e;--hero-bg:%RADIAL%;}""",
    # 뉴트럴 다크 (전체 다크 + 블루 액센트)
    "slate": """:root{
  --ink:#111318;--ink-2:#1a1d24;--ink-line:#2a2e37;--ink-fg:#e8eaf0;--ink-mut:#98a0ad;
  --page:#181a1f;--sheet:#1f232b;--soft:#20242d;--line:#2c313b;
  --fg:#e6e9f0;--mut:#98a0ad;--heading:#f3f5fa;
  --accent:#6aa1ff;--accent-2:#8bb8ff;--gold:#d6a95a;--accent-soft:rgba(106,161,255,.14);
  --th-bg:#0c0e12;--th-fg:#e8eaf0;--nav-active-fg:#fff;--hero-fg:#fff;
  --pre-bg:#0c0e12;--pre-fg:#dfe6f0;--code-fg:#e0956f;--hero-bg:%RADIAL%;}""",
}
_THEMES = {k: v.replace("%RADIAL%", _RADIAL_HERO) for k, v in _THEMES.items()}
_DEFAULT_THEME = "classic"

# 구조·컴포넌트 CSS (색은 전부 var()) — 모든 테마 공유
_STRUCT = """\
:root{--sb:296px;--radius:16px;
  --mono:ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
  --serif:"Iowan Old Style","Apple Garamond",Georgia,"Nanum Myeongjo","Batang",serif;}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--page);color:var(--fg);
  font:16px/1.75 var(--sans);-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.layout{display:grid;grid-template-columns:var(--sb) 1fr;min-height:100vh}
.sidebar{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--ink);
  color:var(--ink-fg);border-right:1px solid var(--ink-line)}
.sidebar::-webkit-scrollbar{width:8px}.sidebar::-webkit-scrollbar-thumb{background:var(--ink-line);border-radius:8px}
.content{min-width:0;display:flex;flex-direction:column;background:var(--page)}
.topbar{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:1rem;
  padding:.85rem 2rem;background:color-mix(in srgb,var(--page) 86%,transparent);
  backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.topbar .doc-title{font-weight:700;font-size:.9rem;color:var(--mut);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.topbar .search{flex:1;max-width:440px;margin-left:auto;position:relative}
.topbar .search::before{content:"⌕";position:absolute;left:.7rem;top:50%;transform:translateY(-50%);
  color:var(--mut);font-size:1.05rem}
.topbar input{width:100%;padding:.55rem .9rem .55rem 2rem;border-radius:11px;border:1px solid var(--line);
  background:var(--soft);color:var(--fg);font:inherit;font-size:.9rem}
.topbar input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}

main.article{max-width:860px;width:calc(100% - 3rem);margin:2.4rem auto 5rem;background:var(--sheet);
  border:1px solid var(--line);border-radius:var(--radius);padding:3.4rem 3.6rem 4rem;
  box-shadow:0 1px 2px rgba(16,24,40,.04),0 12px 40px -12px rgba(16,24,40,.14)}

.brand{display:flex;align-items:center;gap:.7rem;padding:1.4rem 1.4rem;
  border-bottom:1px solid var(--ink-line);color:var(--ink-fg);font-weight:750;letter-spacing:-.01em}
.brand .mark{width:30px;height:30px;border-radius:9px;flex:none;
  background:linear-gradient(135deg,var(--accent-2),var(--accent));display:grid;place-items:center;
  color:#04211d;font-weight:900;font-size:.95rem}
.brand small{display:block;font-weight:500;font-size:.7rem;color:var(--ink-mut);
  letter-spacing:.12em;text-transform:uppercase;margin-top:.15rem}
.nav{padding:1rem .7rem 3rem}
.nav .part{margin:.2rem 0 .6rem}
.nav .part>.plabel{display:flex;align-items:center;gap:.45rem;width:100%;padding:.5rem .7rem;
  background:none;border:0;color:var(--gold);font:inherit;font-weight:700;font-size:.68rem;
  letter-spacing:.13em;text-transform:uppercase;cursor:pointer}
.nav .part>.plabel .chev{transition:transform .15s;font-size:.62rem;color:var(--ink-mut)}
.nav .part.collapsed .chev{transform:rotate(-90deg)}
.nav .part.collapsed ul{display:none}
.nav ul{list-style:none;margin:.15rem 0 .4rem;padding:0}
.nav li a{display:block;padding:.46rem .8rem;border-radius:9px;color:var(--ink-mut);
  font-size:.9rem;line-height:1.45;border-left:2px solid transparent}
.nav li a:hover{background:var(--ink-2);color:var(--ink-fg);text-decoration:none}
.nav li a.active{background:linear-gradient(90deg,var(--accent-soft),transparent);
  border-left-color:var(--accent-2);color:var(--nav-active-fg);font-weight:600}

.article h1{font-family:var(--serif);font-size:2.35rem;line-height:1.16;letter-spacing:-.01em;
  margin:0 0 .3rem;font-weight:800;color:var(--heading)}
.article h1+p,.article h1+h2{margin-top:1.3rem}
.article>h1::after{content:"";display:block;width:56px;height:4px;margin:1.1rem 0 0;
  border-radius:3px;background:linear-gradient(90deg,var(--gold),transparent)}
.article h2{font-size:1.42rem;margin:2.6rem 0 .9rem;font-weight:750;letter-spacing:-.01em;
  padding-left:.9rem;border-left:4px solid var(--accent);color:var(--heading)}
.article h3{font-size:1.13rem;margin:1.9rem 0 .5rem;font-weight:700;color:var(--fg)}
.article p{margin:.9rem 0}
.article ul,.article ol{margin:.8rem 0;padding-left:1.35rem}
.article li{margin:.32rem 0}
.article li::marker{color:var(--accent)}
.article strong{color:var(--heading);font-weight:700}
.article blockquote{margin:1.4rem 0;padding:.9rem 1.2rem;background:var(--soft);
  border-left:3px solid var(--gold);border-radius:0 10px 10px 0;color:var(--mut)}
.ref{font-size:.78em;color:var(--accent);font-weight:600;vertical-align:.18em;
  padding:0 .1em;text-decoration:none}

.table-wrap{overflow-x:auto;margin:1.6rem 0;border:1px solid var(--line);border-radius:12px;
  box-shadow:0 1px 2px rgba(16,24,40,.04)}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:.68rem .95rem;text-align:left;border-bottom:1px solid var(--line)}
thead th{background:var(--th-bg);color:var(--th-fg);font-weight:650;letter-spacing:.01em;
  border-bottom:0;white-space:nowrap}
tbody tr:nth-child(even){background:var(--soft)}
tbody tr:hover{background:var(--accent-soft)}
tbody tr:last-child td{border-bottom:0}

pre{background:var(--pre-bg);color:var(--pre-fg);border-radius:12px;padding:1.1rem 1.3rem;
  overflow-x:auto;font:.85rem/1.6 var(--mono);margin:1.4rem 0}
:not(pre)>code{background:var(--soft);border:1px solid var(--line);border-radius:6px;
  padding:.08em .42em;font:.85em var(--mono);color:var(--code-fg)}
pre.mermaid{background:var(--soft);color:inherit;text-align:center;padding:1.6rem;border:1px solid var(--line)}

.pager{display:flex;gap:1rem;margin-top:3.6rem;padding-top:1.8rem;border-top:1px solid var(--line)}
.pager a{flex:1;display:block;padding:1rem 1.2rem;border:1px solid var(--line);border-radius:12px;
  background:var(--sheet);transition:.16s}
.pager a:hover{border-color:var(--accent);box-shadow:0 8px 24px -10px var(--accent-soft);
  transform:translateY(-2px);text-decoration:none}
.pager a.next{text-align:right}
.pager .dir{display:block;font-size:.7rem;color:var(--mut);text-transform:uppercase;letter-spacing:.09em}
.pager .lbl{display:block;font-weight:700;margin-top:.25rem;color:var(--fg)}

.cover{background:var(--ink);color:var(--ink-fg);min-height:100vh}
.hero{position:relative;overflow:hidden;padding:9vh 8vw 7vh;background:var(--hero-bg)}
.hero::after{content:"";position:absolute;inset:0;pointer-events:none;
  background-image:linear-gradient(color-mix(in srgb,var(--ink-fg) 6%,transparent) 1px,transparent 1px),
    linear-gradient(90deg,color-mix(in srgb,var(--ink-fg) 6%,transparent) 1px,transparent 1px);
  background-size:44px 44px;mask-image:radial-gradient(80% 60% at 60% 20%,#000,transparent)}
.hero>*{position:relative}
.eyebrow{font-size:.78rem;font-weight:800;letter-spacing:.24em;text-transform:uppercase;color:var(--gold)}
.hero h1{font-family:var(--serif);font-size:clamp(2.6rem,7vw,5rem);line-height:1.02;
  letter-spacing:-.02em;margin:1rem 0 .2rem;font-weight:850;color:var(--hero-fg);max-width:16ch}
.hero .rule{width:120px;height:3px;margin:1.6rem 0 1.3rem;
  background:linear-gradient(90deg,var(--gold),transparent)}
.badges{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.4rem}
.badge{display:inline-flex;align-items:center;padding:.36rem .95rem;border-radius:999px;font-size:.78rem;
  font-weight:650;border:1px solid var(--ink-line);color:var(--ink-fg)}
.badge.edition{background:linear-gradient(135deg,var(--accent),var(--accent-2));border-color:transparent;color:#04211d}
.badge.version{color:var(--ink-mut)}
.cover .meta{color:var(--ink-mut);font-size:.92rem;margin-top:1.4rem;letter-spacing:.01em}
.stat-row{display:flex;flex-wrap:wrap;gap:.9rem;margin:2.2rem 0 .3rem}
.stat-chip{flex:1;min-width:118px;background:color-mix(in srgb,var(--ink-fg) 7%,transparent);
  border:1px solid var(--ink-line);border-radius:12px;padding:1rem 1.2rem}
.stat-chip .num{font-family:var(--serif);font-size:1.85rem;font-weight:800;color:var(--gold);line-height:1}
.stat-chip .lbl{font-size:.75rem;color:var(--ink-mut);margin-top:.45rem;letter-spacing:.05em}
.btn-primary{display:inline-flex;align-items:center;gap:.5rem;margin-top:1.8rem;padding:.72rem 1.5rem;
  border-radius:999px;background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;
  font-weight:750;font-size:.95rem;box-shadow:0 8px 24px -10px var(--accent-soft)}
.btn-primary:hover{text-decoration:none;filter:brightness(1.08)}
.toc{padding:4vh 8vw 8vh}
.toc-h{font-size:.8rem;font-weight:800;letter-spacing:.2em;text-transform:uppercase;
  color:var(--ink-mut);margin-bottom:1.6rem}
.part-row{display:grid;grid-template-columns:88px 1fr;gap:1.4rem;padding:1.8rem 0;
  border-top:1px solid var(--ink-line)}
.part-row .num{font-family:var(--serif);font-size:2.6rem;font-weight:800;line-height:1;
  color:transparent;-webkit-text-stroke:1.4px color-mix(in srgb,var(--gold) 65%,transparent)}
.part-row .plabel{font-size:1.15rem;font-weight:750;color:var(--hero-fg);margin:.2rem 0 1rem}
.part-row ul{list-style:none;margin:0;padding:0;columns:2;column-gap:2.2rem}
.part-row li{break-inside:avoid;margin:.15rem 0}
.part-row li a{display:block;padding:.4rem .1rem;color:var(--ink-mut);font-size:.94rem;
  border-bottom:1px solid var(--ink-line)}
.part-row li a:hover{color:var(--accent-2)}

.menu-btn{display:none;background:var(--soft);border:1px solid var(--line);border-radius:9px;
  color:var(--fg);font-size:1.1rem;padding:.3rem .6rem;cursor:pointer}
@media (max-width:900px){
  .layout{grid-template-columns:1fr}
  .sidebar{position:fixed;left:0;top:0;width:var(--sb);z-index:20;transform:translateX(-100%);
    transition:transform .2s;box-shadow:0 0 50px rgba(0,0,0,.5)}
  .sidebar.open{transform:none}
  .menu-btn{display:inline-block}
  main.article{padding:2rem 1.4rem 3rem;width:calc(100% - 1.6rem)}
  .part-row{grid-template-columns:1fr}.part-row ul{columns:1}
}
"""


def _css(theme: str) -> str:
    return _THEMES.get(theme, _THEMES[_DEFAULT_THEME]) + "\n" + _STRUCT


_JS = """\
(function(){
  document.querySelectorAll('.nav .plabel').forEach(function(b){
    b.addEventListener('click',function(){ b.closest('.part').classList.toggle('collapsed'); });
  });
  var mb=document.querySelector('.menu-btn'), sb=document.querySelector('.sidebar');
  if(mb&&sb){ mb.addEventListener('click',function(){ sb.classList.toggle('open'); }); }
  var input=document.querySelector('.search input');
  var idx=(window.SEARCH_INDEX||[]);
  if(input){ input.addEventListener('input',function(){
    var q=input.value.trim().toLowerCase();
    if(!q){ document.querySelectorAll('.nav li').forEach(function(li){li.style.display='';}); return; }
    var hit={};
    idx.forEach(function(r){ if((r.t+' '+r.x).toLowerCase().indexOf(q)>=0) hit[r.u]=1; });
    document.querySelectorAll('.nav li a').forEach(function(a){
      a.closest('li').style.display = hit[a.getAttribute('data-url')]?'':'none'; });
  }); }
})();
"""

_HEAD = """\
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{p}assets/webbook.css">
<script>window.MathJax={{tex:{{inlineMath:[["$","$"]],displayMath:[["$$","$$"]]}}}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";mermaid.initialize({{startOnLoad:true}});</script>\
"""


def _esc(s: str) -> str:
    return _html.escape(s or "")


def _plain(html_str: str, cap: int = 1500) -> str:
    """검색 인덱스용 평문 추출 (태그 제거·공백 정리)."""
    txt = re.sub(r"<[^>]+>", " ", html_str or "")
    txt = _html.unescape(re.sub(r"\s+", " ", txt)).strip()
    return txt[:cap]


def _sidebar(doc_title: str, nav: list, current_url: str, prefix: str) -> str:
    """좌측 트리 사이드바 HTML (current_url 강조)."""
    parts_html = []
    for part_label, pages in nav:
        lis = "\n".join(
            f'<li><a data-url="{_esc(url)}" href="{prefix}{_esc(url)}"'
            f'{" class=active" if url == current_url else ""}>{_esc(label)}</a></li>'
            for url, label in pages
        )
        parts_html.append(
            '<div class="part">'
            f'<button class="plabel"><span class="chev">▾</span>{_esc(part_label)}</button>'
            f"<ul>{lis}</ul></div>"
        )
    mark = _esc(doc_title[:1]) if doc_title else "T"
    return (
        f'<aside class="sidebar">'
        f'<a class="brand" href="{prefix}index.html"><span class="mark">{mark}</span>'
        f"<span>{_esc(doc_title)}<small>TechDoc 웹북</small></span></a>"
        f'<nav class="nav">{"".join(parts_html)}</nav></aside>'
    )


def _pager(prev: dict | None, nxt: dict | None, prefix: str) -> str:
    if not prev and not nxt:
        return ""
    left = (
        f'<a class="prev" href="{prefix}{_esc(prev["url"])}">'
        f'<span class="dir">← 이전</span><span class="lbl">{_esc(prev["title"])}</span></a>'
        if prev else "<span></span>"
    )
    right = (
        f'<a class="next" href="{prefix}{_esc(nxt["url"])}">'
        f'<span class="dir">다음 →</span><span class="lbl">{_esc(nxt["title"])}</span></a>'
        if nxt else "<span></span>"
    )
    return f'<nav class="pager">{left}{right}</nav>'


def _page_html(doc_title: str, rec: dict, nav: list, prev: dict | None, nxt: dict | None) -> str:
    prefix = "../" * rec["url"].count("/")
    return (
        f'<!doctype html>\n<html lang="ko">\n<head>\n{_HEAD.format(p=prefix)}\n'
        f"<title>{_esc(rec['title'])} · {_esc(doc_title)}</title>\n"
        f'<script src="{prefix}assets/search-index.js"></script>\n'
        f'<script defer src="{prefix}assets/webbook.js"></script>\n</head>\n<body>\n'
        f'<div class="layout">\n{_sidebar(doc_title, nav, rec["url"], prefix)}\n'
        f'<div class="content">'
        f'<div class="topbar"><button class="menu-btn">☰</button>'
        f'<span class="doc-title">{_esc(doc_title)}</span>'
        f'<div class="search"><input type="search" placeholder="검색…" aria-label="검색"></div></div>'
        f'<main class="article">\n{rec["body"]}\n{_pager(prev, nxt, prefix)}\n</main>'
        f"</div>\n</div>\n</body>\n</html>\n"
    )


def _cover_html(doc_title: str, nav: list, version: str, edition: str) -> str:
    badges = []
    if edition:
        badges.append(f'<span class="badge edition">{_esc(edition)}</span>')
    if version:
        badges.append(f'<span class="badge version">{_esc(version)}</span>')
    badge_html = f'<div class="badges">{"".join(badges)}</div>' if badges else ""
    total_pages = sum(len(pages) for _label, pages in nav)
    first_url = nav[0][1][0][0] if nav and nav[0][1] else "index.html"
    stat_html = (
        '<div class="stat-row">'
        f'<div class="stat-chip"><div class="num">{total_pages}</div><div class="lbl">문서</div></div>'
        f'<div class="stat-chip"><div class="num">{len(nav)}</div><div class="lbl">구성 Part</div></div>'
        "</div>"
    )
    cta = f'<a class="btn-primary" href="{_esc(first_url)}">처음부터 읽기 →</a>' if nav else ""
    rows = []
    for i, (part_label, pages) in enumerate(nav, 1):
        lis = "\n".join(
            f'<li><a href="{_esc(url)}">{_esc(label)}</a></li>' for url, label in pages
        )
        rows.append(
            f'<div class="part-row"><div class="num">{i:02d}</div>'
            f'<div><div class="plabel">{_esc(part_label)}</div><ul>{lis}</ul></div></div>'
        )
    return (
        f'<!doctype html>\n<html lang="ko">\n<head>\n{_HEAD.format(p="")}\n'
        f"<title>{_esc(doc_title)}</title>\n</head>\n<body>\n"
        f'<div class="cover"><header class="hero">'
        f'<div class="eyebrow">Technical Analysis Report</div>'
        f"<h1>{_esc(doc_title)}</h1><div class=\"rule\"></div>{badge_html}"
        f'<div class="meta">레퍼런스 기반 · 카드 중첩식 구조 · 별첨 논문 수준 심층분석</div>'
        f"{stat_html}{cta}"
        f'</header><section class="toc"><div class="toc-h">Contents · 목차</div>'
        f'{"".join(rows)}</section></div>\n</body>\n</html>\n'
    )


def _first_heading(md: str) -> str:
    """md 첫 `# ` 헤딩 텍스트 (페이지 제목용). 없으면 빈 문자열."""
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


class WebbookExporter:
    """카드 JSON 디렉토리 → Part 트리 HTML 웹북 (테마 선택식 디자인)."""

    def __init__(self, routing_config: dict = DEFAULT_ROUTING) -> None:
        self.config = routing_config
        self._tree = MarkdownTreeExporter(routing_config)  # config 접근자·part 순서 재사용

    def _write_book(self, output_dir: Path, title: str, nav: list, records: list,
                    version: str, edition: str, theme: str) -> dict:
        """nav(사이드바) + records(페이지) → 자산·페이지·표지 기록."""
        (output_dir / "assets").mkdir(parents=True, exist_ok=True)
        (output_dir / "assets" / "webbook.css").write_text(_css(theme), encoding="utf-8")
        (output_dir / "assets" / "webbook.js").write_text(_JS, encoding="utf-8")
        search = [{"u": r["url"], "t": r["title"], "x": _plain(r["body"])} for r in records]
        (output_dir / "assets" / "search-index.js").write_text(
            "window.SEARCH_INDEX=" + json.dumps(search, ensure_ascii=False) + ";",
            encoding="utf-8",
        )
        for i, rec in enumerate(records):
            prev = records[i - 1] if i > 0 else None
            nxt = records[i + 1] if i < len(records) - 1 else None
            dest = output_dir / rec["url"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(_page_html(title, rec, nav, prev, nxt), encoding="utf-8")
        (output_dir / "index.html").write_text(
            _cover_html(title, nav, version, edition), encoding="utf-8"
        )
        return {"parts": len(nav), "pages": len(records), "theme": theme}

    def export(self, cards_dir: Path | str, output_dir: Path | str,
               title: str = "기술보고서", variant: str = "full",
               version: str = "", edition: str = "", term_map: dict | None = None,
               theme: str = _DEFAULT_THEME) -> dict:
        """cards_dir의 `*_card.json` → output_dir 웹북. 통계 dict 반환.

        variant: "full"(전체) | "general"(일반용 — formal_section 카드 제외, F36·F43).
        version·edition: 표지 버전·판본 배지 (F43).
        theme: premium(기본)·light·slate.
        """
        cards_dir = Path(cards_dir)
        output_dir = Path(output_dir)

        # F36·F43: variant='general'은 formal_section(정형 사양) 카드를 제외.
        files = sorted(cards_dir.glob("*_card.json"))
        if variant == "general":
            files = [f for f in files if not load_card(f).get("formal_section")]
        buckets = bucket_cards(files, self.config)

        nav: list = []
        records: list = []
        for part_key in self._tree._ordered_parts(buckets):
            part_dir_name = self._tree._part_dir_name(part_key)
            part_label = self._tree._part_label(part_key)
            pages_meta: list = []
            for parent_id, gfiles in group_by_parent(buckets[part_key]).items():
                cards = [load_card(f) for f in gfiles]
                if len(cards) > 1:
                    md = render_merged_md(parent_id, cards, heading_level=1)
                else:
                    md = render_card_md(cards[0], heading_level=1, card_id=parent_id)
                formal = render_formal_blocks(cards[0])  # F32
                if formal:
                    md = md.rstrip() + "\n\n" + formal + "\n"
                if term_map:  # F29
                    md = localize_terms(md, term_map)
                body_html, toc = md_to_html(md, refs_href="")
                title_txt = _card_title(cards[0], parent_id)
                if term_map:
                    title_txt = localize_terms(title_txt, term_map)
                page_label = f"{parent_id} {title_txt}".strip()
                url = f"{part_dir_name}/{safe_dirname(parent_id)}.html"
                records.append({"url": url, "title": page_label, "body": body_html, "toc": toc})
                pages_meta.append((url, page_label))
            nav.append((part_label, pages_meta))

        return self._write_book(output_dir, title, nav, records, version, edition, theme)

    def export_md_dir(self, md_dir: Path | str, output_dir: Path | str,
                      title: str = "기술보고서", version: str = "", edition: str = "",
                      term_map: dict | None = None, theme: str = _DEFAULT_THEME) -> dict:
        """편집된 md 디렉토리(--tree 중간물) → 웹북 재렌더 (md 왕복 편집, F51).

        md_dir 하위 `*.md`(INDEX.md 제외)를 트리 구조 그대로 병렬 `.html` 페이지로 변환.
        """
        md_dir = Path(md_dir)
        output_dir = Path(output_dir)

        parts: dict[str, list] = {}
        records: list = []
        for md_file in sorted(md_dir.rglob("*.md")):
            if md_file.name == "INDEX.md":
                continue
            rel = md_file.relative_to(md_dir)
            content = md_file.read_text(encoding="utf-8")
            if term_map:  # F29
                content = localize_terms(content, term_map)
            body_html, toc = md_to_html(content, refs_href="")
            page_title = _first_heading(content) or rel.stem
            url = rel.with_suffix(".html").as_posix()
            records.append({"url": url, "title": page_title, "body": body_html, "toc": toc})
            part_name = rel.parts[0] if len(rel.parts) > 1 else "본문"
            parts.setdefault(part_name, []).append((url, page_title))

        nav = list(parts.items())
        return self._write_book(output_dir, title, nav, records, version, edition, theme)
