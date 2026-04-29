"""export_wiki.py 단위·통합 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.wiki.markers import (
    AUTO_START, AUTO_END,
    extract_ai_region, replace_ai_region, has_markers,
)
from scripts.wiki.frontmatter import (
    serialize_frontmatter, parse_frontmatter, split_page,
)


def test_pytest_infra(fake_vault_dir: Path, fake_document_final: dict):
    """fixtures 정상 로드 확인."""
    assert fake_vault_dir.exists()
    assert fake_document_final["title"] == "노지 스마트농업 기술 분석"
    assert len(fake_document_final["tech_cards"]) == 1


def test_markers_constants():
    assert AUTO_START == "<!-- techdoc:auto-start -->"
    assert AUTO_END == "<!-- techdoc:auto-end -->"


def test_has_markers_true():
    page = f"intro\n{AUTO_START}\nai\n{AUTO_END}\nouter"
    assert has_markers(page) is True


def test_has_markers_false():
    assert has_markers("just plain text without markers") is False


def test_extract_ai_region():
    page = f"user note\n{AUTO_START}\nAI managed area\n{AUTO_END}\nmore user note"
    assert extract_ai_region(page) == "AI managed area"


def test_extract_ai_region_no_markers():
    """마커가 없으면 None."""
    assert extract_ai_region("plain page") is None


def test_replace_ai_region_existing():
    """기존 AI 영역 치환, 외부 메모 보존."""
    page = f"USER MEMO TOP\n\n{AUTO_START}\nold ai\n{AUTO_END}\n\nUSER MEMO BOTTOM"
    new = replace_ai_region(page, "new ai content")
    assert "USER MEMO TOP" in new
    assert "USER MEMO BOTTOM" in new
    assert "old ai" not in new
    assert "new ai content" in new
    assert AUTO_START in new
    assert AUTO_END in new


def test_replace_ai_region_no_markers():
    """마커가 없는 페이지면 마커 + AI 영역을 끝에 추가, 기존 내용 100% 보존."""
    page = "USER MEMO\n\nmore notes"
    new = replace_ai_region(page, "ai content")
    assert "USER MEMO" in new
    assert "more notes" in new
    assert AUTO_START in new
    assert AUTO_END in new
    assert "ai content" in new


def test_replace_ai_region_empty_page():
    """빈 페이지 처리."""
    new = replace_ai_region("", "ai content")
    assert AUTO_START in new
    assert "ai content" in new
    assert AUTO_END in new


def test_serialize_frontmatter():
    data = {"type": "tech", "name": "점적관개", "tags": ["smart-farming"]}
    out = serialize_frontmatter(data)
    assert out.startswith("---\n")
    assert out.endswith("---\n")
    assert "type: tech" in out
    assert "점적관개" in out


def test_parse_frontmatter_with_data():
    page = "---\ntype: tech\nname: 점적관개\n---\n\nbody content"
    fm, body = parse_frontmatter(page)
    assert fm == {"type": "tech", "name": "점적관개"}
    assert body.strip() == "body content"


def test_parse_frontmatter_no_frontmatter():
    page = "just body, no frontmatter"
    fm, body = parse_frontmatter(page)
    assert fm == {}
    assert body == "just body, no frontmatter"


def test_split_page_combines():
    """split_page는 frontmatter dict와 body 문자열을 받아 완전한 페이지 생성."""
    fm = {"type": "tech", "name": "점적관개"}
    body = "## 본문\n내용"
    page = split_page(fm, body)
    parsed_fm, parsed_body = parse_frontmatter(page)
    assert parsed_fm == fm
    assert parsed_body.strip() == body
