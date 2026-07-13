"""웹북(Web Book) 렌더러 — 카드 JSON → file:// 정적 다중 페이지 HTML (LLM 0회).

자식 프로젝트마다 복붙되던 `build_webbook.py`를 plugin으로 승격 (F52, 워크스트림 A).
routing_config(F21)로 Part 버킷팅, split 카드는 parent_id로 병합(F13), 기존 렌더러를
재사용한다: 트리/그룹핑은 `markdown_tree`(F15·F17), md→html은 `webbook_md2html`
(수식 F38·mermaid F48 보호 포함).

디자인: 모던 테크 — 좌측 트리 사이드바 + 표지 + 전문 검색 + 이전/다음 pager + 우측 TOC 레일.

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

# ── 모던 테크 디자인 자산 ──────────────────────────────────────────

_CSS = """\
:root{
  --bg:#0f1115; --surface:#171a21; --surface-2:#1e222b; --line:#2a2f3a;
  --fg:#e7ebf3; --muted:#9aa4b2; --accent:#5b8cff; --accent-2:#22d3ee;
  --grad:linear-gradient(90deg,#5b8cff,#22d3ee); --radius:14px; --sb:290px;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
}
@media (prefers-color-scheme:light){
  :root{ --bg:#f6f8fc; --surface:#fff; --surface-2:#f0f3f9; --line:#e4e8f0;
    --fg:#161a22; --muted:#5a6472; --accent:#2f5fe0; --accent-2:#0a92ad; }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.72 var(--sans);
  -webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* 레이아웃 */
.layout{display:grid;grid-template-columns:var(--sb) 1fr;min-height:100vh}
.sidebar{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--surface);
  border-right:1px solid var(--line);padding:0}
.content{min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:1rem;
  padding:.7rem 1.4rem;background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.topbar .doc-title{font-weight:700;font-size:.95rem;color:var(--muted);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.topbar .search{flex:1;max-width:420px;margin-left:auto}
.topbar input{width:100%;padding:.5rem .8rem;border-radius:10px;border:1px solid var(--line);
  background:var(--surface-2);color:var(--fg);font:inherit;font-size:.9rem}
.topbar input:focus{outline:2px solid var(--accent);border-color:transparent}
main.article{max-width:820px;width:100%;margin:0 auto;padding:2.4rem 1.6rem 5rem}

/* 사이드바 브랜드/네비 */
.brand{display:block;padding:1.15rem 1.2rem;border-bottom:1px solid var(--line);
  font-weight:800;font-size:1.02rem;letter-spacing:-.01em}
.brand small{display:block;font-weight:500;font-size:.72rem;color:var(--muted);margin-top:.2rem}
.nav{padding:.6rem .6rem 2rem}
.nav .part{margin:.35rem 0}
.nav .part>.plabel{display:flex;align-items:center;gap:.4rem;width:100%;padding:.4rem .6rem;
  background:none;border:0;color:var(--muted);font:inherit;font-weight:700;font-size:.72rem;
  letter-spacing:.06em;text-transform:uppercase;cursor:pointer}
.nav .part>.plabel .chev{transition:transform .15s;font-size:.7rem}
.nav .part.collapsed .chev{transform:rotate(-90deg)}
.nav .part.collapsed ul{display:none}
.nav ul{list-style:none;margin:.1rem 0 .5rem;padding:0}
.nav li a{display:block;padding:.4rem .7rem;border-radius:9px;color:var(--fg);
  font-size:.9rem;border-left:2px solid transparent}
.nav li a:hover{background:var(--surface-2);text-decoration:none}
.nav li a.active{background:color-mix(in srgb,var(--accent) 16%,transparent);
  border-left-color:var(--accent);color:var(--fg);font-weight:600}
.nav li a.hidden{display:none}

/* 타이포 */
.article h1{font-size:2.05rem;line-height:1.18;letter-spacing:-.02em;margin:.2rem 0 1.4rem;
  font-weight:800}
.article h1::after{content:"";display:block;width:64px;height:4px;margin-top:.7rem;
  border-radius:3px;background:var(--grad)}
.article h2{font-size:1.4rem;margin:2.4rem 0 .9rem;font-weight:750;letter-spacing:-.01em}
.article h3{font-size:1.12rem;margin:1.8rem 0 .6rem;color:var(--muted)}
.article p{margin:.85rem 0}
.article ul,.article ol{margin:.7rem 0;padding-left:1.4rem}
.article li{margin:.28rem 0}
.article strong{color:var(--fg)}
.ref{font-size:.82em;color:var(--accent-2);text-decoration:none;vertical-align:.15em}

/* 표 */
.table-wrap{overflow-x:auto;margin:1.4rem 0;border:1px solid var(--line);border-radius:var(--radius)}
table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{padding:.6rem .85rem;text-align:left;border-bottom:1px solid var(--line)}
thead th{background:var(--surface-2);font-weight:700;color:var(--fg);
  position:sticky;top:0}
tbody tr:hover{background:color-mix(in srgb,var(--accent) 7%,transparent)}
tbody tr:last-child td{border-bottom:0}

/* 코드·mermaid */
pre{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:1rem 1.15rem;overflow-x:auto;font:.86rem/1.6 var(--mono)}
:not(pre)>code{background:var(--surface-2);border:1px solid var(--line);border-radius:6px;
  padding:.08em .4em;font:.86em var(--mono)}
pre.mermaid{background:var(--surface);text-align:center;padding:1.4rem}

/* pager */
.pager{display:flex;gap:1rem;margin-top:3.5rem;padding-top:1.6rem;border-top:1px solid var(--line)}
.pager a{flex:1;display:block;padding:.9rem 1.1rem;border:1px solid var(--line);
  border-radius:var(--radius);background:var(--surface);transition:.15s}
.pager a:hover{border-color:var(--accent);transform:translateY(-2px);text-decoration:none}
.pager a.next{text-align:right}
.pager .dir{display:block;font-size:.72rem;color:var(--muted);text-transform:uppercase;
  letter-spacing:.06em}
.pager .lbl{display:block;font-weight:650;margin-top:.2rem}

/* 표지 */
.cover{max-width:1000px;margin:0 auto;padding:6vh 1.6rem 6rem}
.cover .hero{padding:3rem 0 2.4rem}
.cover .eyebrow{font-size:.8rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent-2)}
.cover h1{font-size:clamp(2.4rem,6vw,4rem);line-height:1.05;letter-spacing:-.03em;
  margin:.6rem 0 1rem;font-weight:850;
  background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.cover .badges{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1.2rem}
.badge{display:inline-block;padding:.32rem .8rem;border-radius:999px;font-size:.78rem;
  font-weight:650;border:1px solid var(--line);background:var(--surface)}
.badge.edition{background:color-mix(in srgb,var(--accent) 18%,transparent);border-color:transparent}
.badge.version{color:var(--muted)}
.cover .meta{color:var(--muted);font-size:.9rem;margin-top:1rem}
.part-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.2rem;
  margin-top:2.4rem}
.part-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:1.3rem 1.4rem}
.part-card h2{margin:0 0 .8rem;font-size:1.05rem;display:flex;align-items:center;gap:.5rem}
.part-card h2::before{content:"";width:10px;height:10px;border-radius:3px;background:var(--grad)}
.part-card ul{list-style:none;margin:0;padding:0}
.part-card li a{display:block;padding:.32rem 0;color:var(--fg);font-size:.92rem;
  border-bottom:1px dashed var(--line)}
.part-card li:last-child a{border-bottom:0}
.part-card li a:hover{color:var(--accent)}

/* 모바일 */
.menu-btn{display:none;background:var(--surface-2);border:1px solid var(--line);border-radius:9px;
  color:var(--fg);font-size:1.1rem;padding:.3rem .6rem;cursor:pointer}
@media (max-width:860px){
  .layout{grid-template-columns:1fr}
  .sidebar{position:fixed;left:0;top:0;width:var(--sb);z-index:20;transform:translateX(-100%);
    transition:transform .2s;box-shadow:0 0 40px rgba(0,0,0,.4)}
  .sidebar.open{transform:none}
  .menu-btn{display:inline-block}
  .article h1{font-size:1.7rem}
}
"""

_JS = """\
(function(){
  // 사이드바 Part 접기/펼치기
  document.querySelectorAll('.nav .plabel').forEach(function(b){
    b.addEventListener('click',function(){ b.closest('.part').classList.toggle('collapsed'); });
  });
  // 모바일 사이드바 토글
  var mb=document.querySelector('.menu-btn'), sb=document.querySelector('.sidebar');
  if(mb&&sb){ mb.addEventListener('click',function(){ sb.classList.toggle('open'); }); }
  // 전문 검색 — SEARCH_INDEX(title+text) 매칭으로 사이드바 링크 필터
  var input=document.querySelector('.search input');
  var idx=(window.SEARCH_INDEX||[]);
  var byUrl={}; document.querySelectorAll('.nav li a').forEach(function(a){
    byUrl[a.getAttribute('data-url')]=a.closest('li'); });
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
<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";mermaid.initialize({{startOnLoad:true,theme:"dark"}});</script>\
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
    return (
        f'<aside class="sidebar">'
        f'<a class="brand" href="{prefix}index.html">{_esc(doc_title)}<small>TechDoc 웹북</small></a>'
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
    cards = []
    for part_label, pages in nav:
        lis = "\n".join(
            f'<li><a href="{_esc(url)}">{_esc(label)}</a></li>' for url, label in pages
        )
        cards.append(f'<div class="part-card"><h2>{_esc(part_label)}</h2><ul>{lis}</ul></div>')
    return (
        f'<!doctype html>\n<html lang="ko">\n<head>\n{_HEAD.format(p="")}\n'
        f"<title>{_esc(doc_title)}</title>\n</head>\n<body>\n"
        f'<div class="cover"><div class="hero">'
        f'<div class="eyebrow">TechDoc · 기술보고서 웹북</div>'
        f"<h1>{_esc(doc_title)}</h1>{badge_html}"
        f'<div class="meta">레퍼런스 기반 · 카드 중첩식 · 별첨 심층분석</div></div>'
        f'<div class="part-grid">{"".join(cards)}</div></div>\n</body>\n</html>\n'
    )


def _first_heading(md: str) -> str:
    """md 첫 `# ` 헤딩 텍스트 (페이지 제목용). 없으면 빈 문자열."""
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


class WebbookExporter:
    """카드 JSON 디렉토리 → Part 트리 HTML 웹북 (모던 테크 디자인)."""

    def __init__(self, routing_config: dict = DEFAULT_ROUTING) -> None:
        self.config = routing_config
        self._tree = MarkdownTreeExporter(routing_config)  # config 접근자·part 순서 재사용

    def _write_book(self, output_dir: Path, title: str, nav: list, records: list,
                    version: str, edition: str) -> dict:
        """nav(사이드바) + records(페이지) → 자산·페이지·표지 기록."""
        (output_dir / "assets").mkdir(parents=True, exist_ok=True)
        (output_dir / "assets" / "webbook.css").write_text(_CSS, encoding="utf-8")
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
        return {"parts": len(nav), "pages": len(records)}

    def export(self, cards_dir: Path | str, output_dir: Path | str,
               title: str = "기술보고서", variant: str = "full",
               version: str = "", edition: str = "", term_map: dict | None = None) -> dict:
        """cards_dir의 `*_card.json` → output_dir 웹북. 통계 dict 반환.

        variant: "full"(전체) | "general"(일반용 — formal_section 카드 제외, F36·F43).
        version·edition: 표지 버전·판본 배지 (F43).
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

        return self._write_book(output_dir, title, nav, records, version, edition)

    def export_md_dir(self, md_dir: Path | str, output_dir: Path | str,
                      title: str = "기술보고서", version: str = "", edition: str = "",
                      term_map: dict | None = None) -> dict:
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
        return self._write_book(output_dir, title, nav, records, version, edition)
