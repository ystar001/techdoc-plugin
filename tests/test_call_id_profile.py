"""_parse_call_id 프로파일 테스트 (v1.9.0 워크스트림 G — F45·F47).

F45 — front-matter(0.x) 카드는 간결하므로 하향 임계(P0).
F47 — 별첨 letter 접두(I·J 포함)를 명시적으로 인식.
"""
from scripts.check_quality import _parse_call_id, SIZE_THRESHOLDS


def test_frontmatter_gets_p0_grade():
    """F45 — 0.x front-matter는 P0 등급(하향 임계)."""
    assert _parse_call_id("0.1") == "P0"
    assert _parse_call_id("0.5_card") == "P0"


def test_p0_threshold_is_low():
    """F45 — P0 임계는 본문 카드(S=14000)보다 낮음."""
    assert "P0" in SIZE_THRESHOLDS
    assert SIZE_THRESHOLDS["P0"] < SIZE_THRESHOLDS["S"]


def test_appendix_ij_recognized():
    """F47 — 별첨 I·J 접두가 명시적으로 인식되어 별첨 floor(S) 적용."""
    assert _parse_call_id("I-1.1") == "S"
    assert _parse_call_id("J-2.3") == "S"


def test_appendix_letter_respects_size_suffix():
    """F47 — 별첨도 L 사이즈 suffix를 존중."""
    assert _parse_call_id("A-14.1.L2") == "L2"


def test_regular_cards_unchanged():
    """회귀 — 일반 본문 카드 등급 판정 불변."""
    assert _parse_call_id("1.1") == "S"
    assert _parse_call_id("1.1.L2") == "L2"
    assert _parse_call_id("7.3.L3") == "L3"
