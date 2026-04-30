"""Tech / Projects / Products 본문 카드 페이지 빌더.

document_final.json의 tech_cards/project_cards/product_cards 한 항목 → 페이지 1개.
별첨이 있는 카드는 frontmatter appendix 필드 + 본문 상단 콜아웃 포함 (표준 마크다운).
"""

from __future__ import annotations

from scripts.wiki.filename import sanitize_name
from scripts.wiki.frontmatter import parse_frontmatter, split_page
from scripts.wiki.markers import replace_ai_region


# vault 디렉토리 매핑: spec §3.1 카테고리 (Tech 단수, 나머지 복수)
_VAULT_DIR = {"tech": "Tech", "project": "Projects", "product": "Products"}


def entity_filename(card: dict) -> str:
    """카드 name → '<safe_name>.md'."""
    return f"{sanitize_name(card.get('name', 'unnamed'))}.md"


def _build_common_frontmatter(card: dict, type_: str, report_title: str, has_appendix: bool) -> dict:
    fm = {
        "type": type_,
        "name": card.get("name", ""),
        "importance": card.get("importance", "medium"),
        "source_card_ids": [card.get("id", "")],
        "ref_ids": card.get("ref_ids", []),
        "reports": [f"[[Reports/{sanitize_name(report_title)}]]"],
        "techdoc_auto": True,
    }
    name_en = card.get("name_en")
    if name_en:
        fm["name_en"] = name_en
        fm["aliases"] = [name_en]
    if has_appendix:
        safe = sanitize_name(card.get("name", "unnamed"))
        fm["appendix"] = f"[[{_VAULT_DIR[type_]}/{safe}_appendix]]"
    return fm


def _render_blocks(card: dict, block_keys: list[tuple[str, str]]) -> str:
    """블록 키 목록 → 헤더+본문 마크다운."""
    parts = []
    for key, header in block_keys:
        content = card.get(key, "").strip()
        if content:
            parts.append(f"## {header}\n\n{content}\n")
    return "\n".join(parts)


def _appendix_callout(card: dict, type_: str) -> str:
    """본문 상단 별첨 콜아웃. 표준 마크다운(이모지 + 인용) — 옵시디언·MkDocs·GitHub 모두 호환."""
    safe = sanitize_name(card.get("name", "unnamed"))
    name = card.get("name", "")
    return (
        f"> ℹ️ **심층분석 별첨**: "
        f"[{name} — 심층분석]({safe}_appendix.md)\n"
    )


def _wrap_with_existing(fm: dict, ai_body: str, existing_page: str | None) -> str:
    if existing_page is None:
        page = split_page(fm, "")
        return replace_ai_region(page, ai_body)
    _, body = parse_frontmatter(existing_page)
    page = split_page(fm, body)
    return replace_ai_region(page, ai_body)


_TECH_BLOCKS = [
    ("overview", "개요"),
    ("principle", "작동 원리·알고리즘"),
    ("components", "구성 요소"),
    ("performance", "성능 지표"),
    ("pros_cons", "장단점"),
    ("differentiation", "차별점·한계"),
    ("references", "참고문헌"),
]


def build_tech_page(
    card: dict,
    report_title: str,
    existing_page: str | None,
    has_appendix: bool = False,
) -> str:
    fm = _build_common_frontmatter(card, "tech", report_title, has_appendix)
    parts = []
    if has_appendix:
        parts.append(_appendix_callout(card, "tech"))
    parts.append(_render_blocks(card, _TECH_BLOCKS))
    ai_body = "\n".join(parts)
    return _wrap_with_existing(fm, ai_body, existing_page)


_PROJECT_BLOCKS = [
    ("background", "배경·목적"),
    ("organization", "수행 체계"),
    ("methodology", "연구 방법론"),
    ("results", "핵심 결과"),
    ("implications", "시사점"),
    ("followup", "후속 연구"),
    ("references", "참고문헌"),
]


def build_project_page(
    card: dict,
    report_title: str,
    existing_page: str | None,
    has_appendix: bool = False,
) -> str:
    fm = _build_common_frontmatter(card, "project", report_title, has_appendix)
    meta = card.get("meta", {})
    for k in ("institution", "pi", "period", "budget", "sponsor"):
        if k in meta:
            fm[k] = meta[k]
    parts = []
    if has_appendix:
        parts.append(_appendix_callout(card, "project"))
    parts.append(_render_blocks(card, _PROJECT_BLOCKS))
    return _wrap_with_existing(fm, "\n".join(parts), existing_page)


_PRODUCT_BLOCKS = [
    ("background", "배경"),
    ("features", "핵심 기능"),
    ("specifications", "기술 사양"),
    ("deployment", "도입 사례"),
    ("market", "시장·가격"),
    ("references", "참고문헌"),
]


def build_product_page(
    card: dict,
    report_title: str,
    existing_page: str | None,
) -> str:
    fm = _build_common_frontmatter(card, "product", report_title, has_appendix=False)
    meta = card.get("meta", {})
    for k in ("model", "maker", "country"):
        if k in meta:
            fm[k] = meta[k]
    return _wrap_with_existing(fm, _render_blocks(card, _PRODUCT_BLOCKS), existing_page)
