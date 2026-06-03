"""최종 렌더링 오케스트레이터 — Document → HTML + PDF + DOCX + MD.

사용법:
    python -m scripts.render --input ./output/document_final.json \
        --refs ./output/reference_list.json \
        -o ./output/ \
        --formats html,pdf,docx,md
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from techdoc_core.models import Document, ReferenceList
from techdoc_core.renderers.card_renderer import (
    has_math_or_mermaid,
    render_all_appendices,
    render_mathjax_header,
    render_mermaid_header,
    render_product_card,
    render_project_card,
    render_tech_card,
)
from techdoc_core.renderers.html_renderer import HTMLRenderer
from techdoc_core.schemas import format_error


def inject_cards_into_sections(document: Document) -> None:
    """섹션 html_content 끝에 해당 섹션의 카드 HTML을 추가."""
    for section in document.sections:
        cards_html = ""
        sid_prefix = section.section_id + "."

        for c in document.tech_cards:
            if c.id.startswith(sid_prefix):
                cards_html += render_tech_card(c) + "\n"
        for c in document.project_cards:
            if c.id.startswith(sid_prefix):
                cards_html += render_project_card(c) + "\n"
        for c in document.product_cards:
            if c.id.startswith(sid_prefix):
                cards_html += render_product_card(c) + "\n"

        if cards_html:
            section.html_content = (section.html_content or "") + "\n" + cards_html


def build_final_html(document: Document, css: str, ref_list: ReferenceList | None = None) -> str:
    """카드·별첨을 포함한 최종 HTML 빌드 (HTMLRenderer 재사용)."""
    # 1. 카드를 섹션 HTML에 주입
    inject_cards_into_sections(document)

    # 2. 별첨 섹션 HTML 생성
    appendices_html = render_all_appendices(document.tech_appendices, document.project_appendices)

    # 3. document.metadata에 별첨·시각화 헤더 추가
    headers = ""
    all_appendices = list(document.tech_appendices) + list(document.project_appendices)
    all_cards = (
        list(document.tech_cards)
        + list(document.project_cards)
        + list(document.product_cards)
    )
    if has_math_or_mermaid(all_appendices, cards=all_cards):
        headers += render_mathjax_header() + "\n" + render_mermaid_header() + "\n"

    # 별첨·헤더를 metadata에 임시 저장 (HTMLRenderer가 사용할 수 있도록)
    document.metadata["_appendices_html"] = appendices_html
    document.metadata["_extra_headers"] = headers

    # HTMLRenderer.render는 파일로 저장하므로, 내부 로직을 수동 구성
    return ""  # placeholder; 실제 HTML은 renderer.render()를 호출해 파일로


def render_html(
    document: Document, css: str, output_dir: Path, filename: str,
    ref_list: ReferenceList | None = None,
) -> Path:
    """HTML 파일 생성 (HTMLRenderer + 카드·별첨 주입)."""
    inject_cards_into_sections(document)
    renderer = HTMLRenderer()
    html_path = renderer.render(document, css, output_dir, filename, ref_list=ref_list)

    # 별첨 HTML을 </body> 직전에 삽입
    appendices_html = render_all_appendices(document.tech_appendices, document.project_appendices)
    all_appendices = list(document.tech_appendices) + list(document.project_appendices)
    all_cards = (
        list(document.tech_cards)
        + list(document.project_cards)
        + list(document.product_cards)
    )
    extra_headers = ""
    if has_math_or_mermaid(all_appendices, cards=all_cards):
        extra_headers = render_mathjax_header() + "\n" + render_mermaid_header()

    if appendices_html or extra_headers:
        html = html_path.read_text(encoding="utf-8")
        if extra_headers:
            html = html.replace("</head>", f"{extra_headers}\n</head>", 1)
        if appendices_html:
            html = html.replace("</body>", f"{appendices_html}\n</body>", 1)
        html_path.write_text(html, encoding="utf-8")

    return html_path


def render_pdf(html_path: Path, output_dir: Path, filename: str) -> Path | None:
    """PDF 생성 (playwright 선택적). 실패 시 경고만 출력."""
    try:
        from techdoc_core.renderers.pdf_export import PDFExporter
        exporter = PDFExporter()
        return exporter.export(html_path, output_dir, filename)
    except ImportError:
        print("  [SKIP] PDF: playwright 미설치 — `pip install techdoc-plugin[pdf]`", file=sys.stderr)
        return None
    except Exception as e:
        print(format_error("TECHDOC-E060", str(e), "playwright install chromium"), file=sys.stderr)
        return None


def render_docx(html_path: Path, output_dir: Path, title: str, filename: str) -> Path | None:
    """DOCX 생성 (python-docx 선택적)."""
    try:
        from techdoc_core.renderers.docx_export import DOCXExporter
        exporter = DOCXExporter()
        return exporter.export(html_path, output_dir, title=title, filename=filename)
    except ImportError:
        print("  [SKIP] DOCX: python-docx 미설치 — `pip install techdoc-plugin[docx]`", file=sys.stderr)
        return None
    except Exception as e:
        print(format_error("TECHDOC-E061", str(e)), file=sys.stderr)
        return None


def render_md(document: Document, output_dir: Path, filename: str,
              ref_list: ReferenceList | None = None) -> Path:
    """Markdown 생성."""
    from techdoc_core.renderers.md_export import MarkdownExporter
    exporter = MarkdownExporter()
    return exporter.export(document, output_dir, filename, ref_list=ref_list)


def render_md_tree(
    cards_dir: Path | str, output_dir: Path | str,
    routing_config: dict | None = None, emit_series_index: bool = False,
) -> dict:
    """카드 JSON 디렉토리 → config 기반 markdown 트리 (F15 + F17).

    LLM 호출 0회·결정론적. MarkdownTreeExporter를 호출해 Part/시리즈 트리 +
    계층 INDEX를 생성하고 통계 dict를 반환한다.
    """
    from techdoc_core.renderers.markdown_tree import MarkdownTreeExporter
    from techdoc_core.routing_config import DEFAULT_ROUTING

    exporter = MarkdownTreeExporter(routing_config or DEFAULT_ROUTING)
    return exporter.export(Path(cards_dir), Path(output_dir), emit_series_index=emit_series_index)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Document to HTML/PDF/DOCX/MD")
    ap.add_argument("-i", "--input", help="document_final.json")
    ap.add_argument("--refs", help="reference_list.json")
    ap.add_argument("--type", dest="design_type", help="디자인 타입 (auto-detect)")
    ap.add_argument("-o", "--output", default="./output", help="출력 디렉토리")
    ap.add_argument("--formats", default="html,pdf,docx,md", help="생성 형식 (콤마 구분)")
    # ── F15: config 기반 트리 디렉토리 출력 (opt-in) ──
    ap.add_argument("--tree", action="store_true",
                    help="카드 디렉토리를 Part/시리즈 트리 + 계층 INDEX로 출력 (F15)")
    ap.add_argument("--cards-dir", help="--tree 입력 카드 디렉토리 (*_card.json)")
    ap.add_argument("--routing-config", help="--tree part 라우팅 config JSON (F21)")
    ap.add_argument("--with-series-index", action="store_true",
                    help="단일 카드 시리즈를 제외한 시리즈 폴더에 INDEX 생성 (F17)")
    args = ap.parse_args()

    # ── 트리 모드: 단일파일 render 경로와 독립 (non-breaking) ──
    if args.tree:
        if not args.cards_dir:
            ap.error("--tree 사용 시 --cards-dir 필수")
        from techdoc_core.routing_config import load_routing_config
        routing = load_routing_config(args.routing_config) if args.routing_config else None
        out_dir = Path(args.output)
        stats = render_md_tree(args.cards_dir, out_dir, routing, args.with_series_index)
        print(f"OK: {out_dir / 'INDEX.md'} ({sum(stats.values())} 문서)")
        return 0

    if not args.input:
        ap.error("-i/--input 필수 (또는 --tree 사용)")

    doc = Document.load(Path(args.input))
    ref_list = None
    if args.refs and Path(args.refs).exists():
        import json as _json
        ref_data = _json.loads(Path(args.refs).read_text(encoding="utf-8"))
        # ReferenceList 재구성 (간이)
        from techdoc_core.models import Reference
        refs = [Reference.from_dict(r) for r in ref_data.get("refs", [])]
        ref_list = ReferenceList(references=refs)

    # 디자인 선택
    from scripts.select_design import detect_type, load_design_config, load_design_css
    type_key = args.design_type or detect_type(doc.title)
    config = load_design_config(type_key)
    css = load_design_css(config)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    title_clean = re.sub(r"[^\w가-힣]", "", doc.title)[:40]
    base = f"{title_clean}_{timestamp}"

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    html_path = None

    if "html" in formats:
        html_path = render_html(doc, css, output_dir, f"{base}.html", ref_list=ref_list)
        print(f"OK: {html_path}")

    if "pdf" in formats and html_path:
        pdf_path = render_pdf(html_path, output_dir, f"{base}.pdf")
        if pdf_path:
            print(f"OK: {pdf_path}")

    if "docx" in formats and html_path:
        docx_path = render_docx(html_path, output_dir, doc.title, f"{base}.docx")
        if docx_path:
            print(f"OK: {docx_path}")

    if "md" in formats:
        md_path = render_md(doc, output_dir, f"{base}.md", ref_list=ref_list)
        print(f"OK: {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
