"""YAML frontmatter 직렬화·역직렬화 (Dataview 호환)."""

from __future__ import annotations

import yaml


def serialize_frontmatter(data: dict) -> str:
    """dict → YAML frontmatter 블록 (앞뒤 ---)."""
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{body}---\n"


def parse_frontmatter(page: str) -> tuple[dict, str]:
    """페이지를 (frontmatter dict, body 문자열)로 분리.

    frontmatter 없으면 ({}, 원문)을 반환.
    """
    if not page.startswith("---\n"):
        return {}, page
    end = page.find("\n---\n", 4)
    if end == -1:
        return {}, page
    fm_text = page[4:end]
    body = page[end + 5:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, page
    return fm, body


def split_page(frontmatter: dict, body: str) -> str:
    """frontmatter dict + body → 완전한 페이지 텍스트."""
    fm_block = serialize_frontmatter(frontmatter)
    if body and not body.startswith("\n"):
        body = "\n" + body
    return fm_block + body
