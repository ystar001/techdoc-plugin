"""Concepts/<term>.md 빌더 (glossary 항목 → 단일 페이지)."""

from __future__ import annotations

from scripts.wiki.frontmatter import parse_frontmatter, split_page
from scripts.wiki.markers import replace_ai_region


def build_concept_page(term: str, definition: str, existing_page: str | None) -> str:
    fm = {
        "type": "concept",
        "term": term,
        "definition_short": definition,
        "techdoc_auto": True,
    }
    ai_body = f"## 정의\n\n{definition}\n"
    if existing_page is None:
        return replace_ai_region(split_page(fm, ""), ai_body)
    _, body = parse_frontmatter(existing_page)
    return replace_ai_region(split_page(fm, body), ai_body)
