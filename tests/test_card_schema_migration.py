import pytest
from pydantic import ValidationError

from techdoc_core import constants
from techdoc_core.schemas import SelfModelCardSchema, SelfModelSection


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
