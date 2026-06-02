from scripts.parse_toc import SECTION_ID_RE


def _match(line):
    m = SECTION_ID_RE.match(line)
    return (m.group(1), m.group(2)) if m else None


def test_numeric_ids_still_parse():
    assert _match("1.1 관개 자동화") == ("1.1", "관개 자동화")
    assert _match("1장. 인프라 기술") == ("1", "인프라 기술")
    assert _match("3.4.2 세부 항목") == ("3.4.2", "세부 항목")


def test_alphanumeric_prefix_ids_parse():
    assert _match("G1 마늘 (한지형)") == ("G1", "마늘 (한지형)")
    assert _match("A-1 벼 별첨") == ("A-1", "벼 별첨")
    assert _match("AP 사과") == ("AP", "사과")
    assert _match("R.1 벼 생육") == ("R.1", "벼 생육")


def test_title_starting_with_alphanumeric_is_not_mistaken_for_id():
    # ID 뒤 구분자(공백/마침표) 없으면 ID 아님 → 제목으로 처리됨(여기선 None)
    assert _match("5G/LTE 기반 농촌 광대역") is None
    assert _match("IoT·센서 기술") is None
