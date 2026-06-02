import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.migrate import (
    apply_migration_path,
    normalize_sections,
    split_title_notes,
)
from techdoc_core import constants
from techdoc_core.schemas import SelfModelCardSchema, SelfModelSection

FIXTURE = Path(__file__).parent / "fixtures" / "cards" / "self_model_0_1_0.json"


def test_default_section_titles_cover_sec1_to_sec6():
    titles = constants.DEFAULT_SECTION_TITLES
    assert set(titles) == {"sec1", "sec2", "sec3", "sec4", "sec5", "sec6"}
    assert titles["sec1"] == "정의·범위"
    assert titles["sec6"] == "전망"


def test_section_key_regex_accepts_only_sec1_to_sec6():
    assert constants.SECTION_KEY_RE.match("sec1")
    assert constants.SECTION_KEY_RE.match("sec6")
    assert not constants.SECTION_KEY_RE.match("sec7")
    assert not constants.SECTION_KEY_RE.match("sec3_trends_international")


def test_self_model_section_has_title_and_body():
    s = SelfModelSection(title="정의·범위", body="본문")
    assert s.title == "정의·범위"
    assert s.body == "본문"


def test_self_model_section_defaults_empty():
    s = SelfModelSection()
    assert s.title == "" and s.body == ""


def test_card_schema_accepts_canonical():
    card = SelfModelCardSchema(
        card_id="A-14.1.L1",
        parent_id="14.1",
        title="농업 데이터 표준",
        split_summary="분할 1/3",
        sections={"sec1": {"title": "정의·범위", "body": "x"}},
    )
    assert card.card_id == "A-14.1.L1"
    assert card.parent_id == "14.1"
    assert card.sections["sec1"].body == "x"


def test_card_schema_rejects_noncanonical_section_keys():
    with pytest.raises(ValidationError):
        SelfModelCardSchema(
            card_id="1.1",
            sections={"sec3_trends_international": {"body": "x"}},
        )


def test_card_schema_card_id_required():
    with pytest.raises(ValidationError):
        SelfModelCardSchema(sections={})


def test_split_title_notes_extracts_division():
    title, note = split_title_notes("농업 데이터 표준 — 분할 1/3")
    assert title == "농업 데이터 표준"
    assert note == "분할 1/3"


def test_split_title_notes_extracts_section_summary():
    title, note = split_title_notes("수확 로봇 — §1 정의·범위 + §2 기술 원리")
    assert title == "수확 로봇"
    assert "§1" in note


def test_split_title_notes_extracts_page_label():
    title, note = split_title_notes("농업 데이터 표준 (L1, 10p)")
    assert title == "농업 데이터 표준"
    assert note == "(L1, 10p)"


def test_split_title_notes_clean_title_unchanged():
    title, note = split_title_notes("관개 자동화 시스템")
    assert title == "관개 자동화 시스템" and note == ""


def test_normalize_sections_unifies_body_variants():
    old = {
        "sec1_definition_scope": {"narrative": "정의 본문"},
        "sec3_trends_international": {"content": "동향 본문"},
    }
    new = normalize_sections(old)
    assert new["sec1"]["body"] == "정의 본문"
    assert new["sec3"]["body"] == "동향 본문"


def test_normalize_sections_fills_default_title():
    old = {"sec1_definition_scope": {"body": "x"}}
    new = normalize_sections(old)
    assert new["sec1"]["title"] == "정의·범위"   # 위치 기본 헤딩


def test_normalize_sections_preserves_existing_title():
    old = {"sec2_principles": {"title": "작동 원리", "body": "x"}}
    new = normalize_sections(old)
    assert new["sec2"]["title"] == "작동 원리"


def test_migrate_self_model_0_1_to_0_2_full():
    old = {
        "schema_version": "0.1.0",
        "section_id": "14.1",
        "appendix_id": "A-14.1.L1",
        "title": "농업 데이터 표준 — 분할 1/3",
        "sections": {
            "sec1_definition_scope": {"narrative": "정의 본문"},
            "sec3_trends_international": {"content": "동향 본문"},
        },
    }
    new = apply_migration_path(old, "0.2.0")
    assert new["schema_version"] == "0.2.0"
    assert new["card_id"] == "A-14.1.L1"      # appendix_id 우선
    assert new["parent_id"] == "14.1"          # section_id → parent
    assert new["title"] == "농업 데이터 표준"
    assert new["split_summary"] == "분할 1/3"
    assert new["sections"]["sec1"]["body"] == "정의 본문"
    assert new["sections"]["sec3"]["title"] == "국내외 동향"
    # 변환 결과가 엄격 스키마를 통과해야 함
    SelfModelCardSchema(**{k: v for k, v in new.items() if k != "schema_version"})


def test_migrate_ignores_standard_blocks_card():
    std = {"schema_version": "0.1.0", "id": "1.1.1", "blocks": {"overview": "x"}}
    new = apply_migration_path(std, "0.2.0")
    assert "card_id" not in new            # 변환 안 함
    assert new["blocks"]["overview"] == "x"


def test_real_fixture_migrates_and_validates():
    old = json.loads(FIXTURE.read_text(encoding="utf-8"))
    new = apply_migration_path(old, "0.2.0")
    assert new["card_id"] == "A-14.1.L1"
    assert new["parent_id"] == "14.1"
    assert "(§1~§3)" in new["split_summary"]
    assert set(new["sections"]) == {"sec1", "sec3", "sec5"}
    assert new["sections"]["sec5"]["title"] == "한계와 과제"  # 기존 title 보존
    # 엄격 스키마 통과
    card = SelfModelCardSchema(**{k: v for k, v in new.items() if k != "schema_version"})
    assert all(s.body for s in card.sections.values())
