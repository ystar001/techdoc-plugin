"""웹북(Web Book) 렌더러 — 카드 JSON → file:// 정적 다중 페이지 HTML (LLM 0회).

자식 프로젝트마다 복붙되던 `build_webbook.py`를 plugin으로 승격 (F52, 워크스트림 A).
routing_config(F21)로 Part 버킷팅, split 카드는 parent_id로 병합(F13), 기존 렌더러를
재사용한다: 트리/그룹핑은 `markdown_tree`(F15·F17), md→html은 `webbook_md2html`
(수식 F38·mermaid F48 보호 포함).

출력: output_dir/
  ├── index.html                (표지 + 전체 목차)
  ├── assets/webbook.css
  └── <Part-dir>/<card_id>.html  (Part별 카드/병합 페이지)

단일 파일 render(`scripts.render`)와 독립 — opt-in 경로.
"""
from __future__ import annotations

import html as _html
from pathlib import Path

from techdoc_core.formal_blocks import render_formal_blocks
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

_CSS = """\
:root { --fg:#1a1a1a; --muted:#666; --accent:#1f4e79; --line:#e2e2e2; }
* { box-sizing: border-box; }
body { max-width: 860px; margin: 0 auto; padding: 2rem 1.2rem 4rem;
  font: 16px/1.75 -apple-system, "Segoe UI", "Malgun Gothic", sans-serif; color: var(--fg); }
h1, h2, h3 { line-height: 1.3; color: var(--accent); }
a { color: var(--accent); }
.crumbs { margin-bottom: 1.5rem; font-size: .9rem; }
.card { }
.table-wrap { overflow-x: auto; margin: 1rem 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid var(--line); padding: .4rem .6rem; text-align: left; }
th { background: #f5f7fa; }
pre.mermaid { text-align: center; }
.toc-section { margin: 1.5rem 0; }
.toc-section h2 { border-bottom: 2px solid var(--line); padding-bottom: .3rem; }
.toc-section ul { list-style: none; padding-left: 0; }
.toc-section li { padding: .2rem 0; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e6e6e6; --muted:#999; --accent:#7fb0e0; --line:#333; }
  body { background: #16181c; }
  th { background: #22262e; }
}
"""

_HEAD = """\
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{css_href}">
<script>window.MathJax={{tex:{{inlineMath:[["$","$"]],displayMath:[["$$","$$"]]}}}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";mermaid.initialize({{startOnLoad:true}});</script>\
"""


def _page_shell(title: str, body_html: str, css_href: str, home_href: str) -> str:
    head = _HEAD.format(css_href=css_href)
    return (
        f"<!doctype html>\n<html lang=\"ko\">\n<head>\n{head}\n"
        f"<title>{_html.escape(title)}</title>\n</head>\n<body>\n"
        f'<nav class="crumbs"><a href="{home_href}">← 목차</a></nav>\n'
        f'<main class="card">\n{body_html}\n</main>\n</body>\n</html>\n'
    )


def _index_shell(doc_title: str, index_entries: list, css_href: str,
                 version: str = "", edition: str = "") -> str:
    head = _HEAD.format(css_href=css_href)
    badges = []
    if edition:
        badges.append(f'<span class="badge edition">{_html.escape(edition)}</span>')
    if version:
        badges.append(f'<span class="badge version">{_html.escape(version)}</span>')
    badge_html = f'<p class="badges">{" ".join(badges)}</p>' if badges else ""
    sections = []
    for part_label, pages in index_entries:
        items = "\n".join(
            f'<li><a href="{url}">{_html.escape(name)}</a></li>' for url, name in pages
        )
        sections.append(
            f'<section class="toc-section"><h2>{_html.escape(part_label)}</h2>\n'
            f"<ul>\n{items}\n</ul></section>"
        )
    body = "\n".join(sections)
    return (
        f"<!doctype html>\n<html lang=\"ko\">\n<head>\n{head}\n"
        f"<title>{_html.escape(doc_title)}</title>\n</head>\n<body>\n"
        f"<header><h1>{_html.escape(doc_title)}</h1>\n{badge_html}</header>\n"
        f"<main>\n{body}\n</main>\n</body>\n</html>\n"
    )


def _first_heading(md: str) -> str:
    """md 첫 `# ` 헤딩 텍스트 (페이지 제목용). 없으면 빈 문자열."""
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


class WebbookExporter:
    """카드 JSON 디렉토리 → Part 트리 HTML 웹북. routing_config로 도메인 명칭 분리."""

    def __init__(self, routing_config: dict = DEFAULT_ROUTING) -> None:
        self.config = routing_config
        self._tree = MarkdownTreeExporter(routing_config)  # config 접근자·part 순서 재사용

    def export(self, cards_dir: Path | str, output_dir: Path | str,
               title: str = "기술보고서", variant: str = "full",
               version: str = "", edition: str = "") -> dict:
        """cards_dir의 `*_card.json` → output_dir 웹북. 통계 dict 반환.

        variant: "full"(전체) | "general"(일반용 — formal_section 카드 제외, F36·F43).
        version·edition: 표지 버전·판본 배지 (F43).
        """
        cards_dir = Path(cards_dir)
        output_dir = Path(output_dir)
        (output_dir / "assets").mkdir(parents=True, exist_ok=True)
        (output_dir / "assets" / "webbook.css").write_text(_CSS, encoding="utf-8")

        # F36·F43: variant='general'은 formal_section(정형 사양) 카드를 제외.
        files = sorted(cards_dir.glob("*_card.json"))
        if variant == "general":
            files = [f for f in files if not load_card(f).get("formal_section")]
        buckets = bucket_cards(files, self.config)

        index_entries: list = []
        page_count = 0
        for part_key in self._tree._ordered_parts(buckets):
            part_dir_name = self._tree._part_dir_name(part_key)
            (output_dir / part_dir_name).mkdir(exist_ok=True)
            pages: list = []
            for parent_id, gfiles in group_by_parent(buckets[part_key]).items():
                cards = [load_card(f) for f in gfiles]
                if len(cards) > 1:
                    md = render_merged_md(parent_id, cards, heading_level=1)
                else:
                    md = render_card_md(cards[0], heading_level=1, card_id=parent_id)
                # F32: 정형 사양 블록(함수 명세·상태벡터·파라미터표)을 본문 뒤에 정형 박스로.
                formal = render_formal_blocks(cards[0])
                if formal:
                    md = md.rstrip() + "\n\n" + formal + "\n"
                body_html, _toc = md_to_html(md, refs_href="")
                title_txt = _card_title(cards[0], parent_id)
                page_label = f"{parent_id} {title_txt}".strip()
                page_name = safe_dirname(parent_id) + ".html"
                (output_dir / part_dir_name / page_name).write_text(
                    _page_shell(page_label, body_html, "../assets/webbook.css", "../index.html"),
                    encoding="utf-8",
                )
                pages.append((f"{part_dir_name}/{page_name}", page_label))
                page_count += 1
            index_entries.append((self._tree._part_label(part_key), pages))

        (output_dir / "index.html").write_text(
            _index_shell(title, index_entries, "assets/webbook.css",
                         version=version, edition=edition), encoding="utf-8"
        )
        return {"parts": len(index_entries), "pages": page_count}

    def export_md_dir(self, md_dir: Path | str, output_dir: Path | str,
                      title: str = "기술보고서", version: str = "", edition: str = "") -> dict:
        """편집된 md 디렉토리(--tree 중간물) → 웹북 재렌더 (md 왕복 편집, F51).

        md_dir 하위 `*.md`(INDEX.md 제외)를 트리 구조 그대로 병렬 `.html` 페이지로 변환.
        사용자가 md를 편집한 뒤 최종(웹북)을 재생성하는 경로.
        """
        md_dir = Path(md_dir)
        output_dir = Path(output_dir)
        (output_dir / "assets").mkdir(parents=True, exist_ok=True)
        (output_dir / "assets" / "webbook.css").write_text(_CSS, encoding="utf-8")

        parts: dict[str, list] = {}
        page_count = 0
        for md_file in sorted(md_dir.rglob("*.md")):
            if md_file.name == "INDEX.md":
                continue
            rel = md_file.relative_to(md_dir)
            depth = len(rel.parts) - 1
            css_href = ("../" * depth) + "assets/webbook.css"
            home_href = ("../" * depth) + "index.html"
            content = md_file.read_text(encoding="utf-8")
            body_html, _toc = md_to_html(content, refs_href="")
            page_title = _first_heading(content) or rel.stem
            out_rel = rel.with_suffix(".html")
            dest = output_dir / out_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                _page_shell(page_title, body_html, css_href, home_href), encoding="utf-8"
            )
            part_name = rel.parts[0] if len(rel.parts) > 1 else "본문"
            parts.setdefault(part_name, []).append((out_rel.as_posix(), page_title))
            page_count += 1

        index_entries = list(parts.items())
        (output_dir / "index.html").write_text(
            _index_shell(title, index_entries, "assets/webbook.css",
                         version=version, edition=edition), encoding="utf-8"
        )
        return {"parts": len(index_entries), "pages": page_count}
