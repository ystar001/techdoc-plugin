"""번호 꼴 모듈 (v1.11-b — 설계 D3.2·F82)."""
from techdoc_core.card_id import parse_card_id_parts, size_id
from techdoc_core.qc.numbering import appendix_letters, caption_num_re, head_re, section_ref_re


def test_section_ref_arabic_unchanged():
    rx = section_ref_re("arabic")
    assert rx.search("자세한 것은 3.2절에서").group(1) == "3.2"
    assert rx.search("II.6.3절") is None


def test_section_ref_roman():
    rx = section_ref_re("roman")
    assert rx.search("앞의 II.6.3절을 보라").group(1) == "II.6.3"


def test_section_ref_letter_middle():
    assert section_ref_re("letter_middle").search("2.A.7절 참고").group(1) == "2.A.7"


def test_head_re_by_style():
    assert head_re("arabic").match("## 3.2 방법").group(3) == "방법"
    assert head_re("arabic").match("## II.6.3 방법") is None
    assert head_re("roman").match("## II.6.3 방법").group(2) == "II.6.3"


def test_caption_num_roman_f82():
    rx = caption_num_re("roman")
    assert rx.fullmatch("II.8-1") and rx.fullmatch("I.2-1")
    assert caption_num_re("arabic").fullmatch("3-2")


def test_appendix_letters_default_and_config():
    assert appendix_letters({}) == "A-Z"
    assert appendix_letters({"structure": {"appendix_letters": "A-H"}}) == "A-H"


def test_card_id_roman_body():
    cid = parse_card_id_parts("II.6.L2", {"section": "roman"})
    assert cid.kind == "body" and size_id(cid) == "L2"
    assert parse_card_id_parts("II.6.L2").kind == "appendix"  # 기본값은 지금과 같다
