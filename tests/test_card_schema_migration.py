from techdoc_core import constants
from techdoc_core.schemas import SelfModelSection


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
