"""Tech/Projects 별첨 페이지 빌더 (10/11 블록)."""

from __future__ import annotations

from scripts.wiki.filename import sanitize_name
from scripts.wiki.frontmatter import parse_frontmatter, split_page
from scripts.wiki.markers import replace_ai_region


def appendix_filename(appendix: dict, parent_name: str) -> str:
    return f"{sanitize_name(parent_name)}_appendix.md"


_TECH_APPENDIX_BLOCKS = [
    ("overview", "개요"),
    ("theory", "이론적 배경"),
    ("algorithms", "알고리즘"),
    ("architecture", "아키텍처"),
    ("benchmark", "벤치마크"),
    ("implementations", "구현 사례"),
    ("timeline", "발전 타임라인"),
    ("limitations", "한계"),
    ("future", "향후 발전"),
    ("references", "참고문헌"),
]

_PROJECT_APPENDIX_BLOCKS = [
    ("chronicle", "연대기"),
    ("structure", "구조"),
    ("phases", "단계"),
    ("experiment", "실험"),
    ("datasets", "데이터셋"),
    ("results_deep", "심층 결과"),
    ("followup", "후속 영향"),
    ("comparison", "비교"),
    ("industry", "산업 영향"),
    ("researchers", "연구진"),
    ("references", "참고문헌"),
]


def _render_blocks(appendix: dict, blocks: list[tuple[str, str]]) -> str:
    parts = []
    for key, header in blocks:
        content = (appendix.get(key, "") or "").strip()
        if content:
            parts.append(f"## {header}\n\n{content}\n")
    return "\n".join(parts)


def _build(appendix: dict, parent_name: str, report_title: str, existing_page: str | None,
           type_label: str, parent_type: str, blocks: list[tuple[str, str]]) -> str:
    safe_parent = sanitize_name(parent_name)
    fm = {
        "type": type_label,
        "name": appendix.get("name", ""),
        "appendix_id": appendix.get("id", ""),
        "parent_card_id": appendix.get("source_card_id", ""),
        "parent_page": f"[[{parent_type.capitalize()}/{safe_parent}]]",
        "blocks_fulfilled": appendix.get("blocks_fulfilled", 0),
        "length_chars": appendix.get("length_chars", 0),
        "reports": [f"[[Reports/{sanitize_name(report_title)}]]"],
        "techdoc_auto": True,
    }
    ai_body = _render_blocks(appendix, blocks)
    if existing_page is None:
        return replace_ai_region(split_page(fm, ""), ai_body)
    _, body = parse_frontmatter(existing_page)
    return replace_ai_region(split_page(fm, body), ai_body)


def build_tech_appendix_page(appendix: dict, parent_name: str, report_title: str, existing_page: str | None) -> str:
    return _build(appendix, parent_name, report_title, existing_page,
                  type_label="tech_appendix", parent_type="tech", blocks=_TECH_APPENDIX_BLOCKS)


def build_project_appendix_page(appendix: dict, parent_name: str, report_title: str, existing_page: str | None) -> str:
    return _build(appendix, parent_name, report_title, existing_page,
                  type_label="project_appendix", parent_type="project", blocks=_PROJECT_APPENDIX_BLOCKS)
