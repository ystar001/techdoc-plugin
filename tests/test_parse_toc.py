from scripts.parse_toc import (
    SECTION_ID_RE,
    is_pure_id,
    is_separator_row,
    map_sizing,
    parse_toc_file,
    parse_toc_table,
    split_table_row,
)

TABLE_TOC = """\
# 작물 백과 목차

| 항목 | 내용 |
|---|---|
| 작성일 | 2026-06-02 |

## 작물 매핑

| 번호 | 작물 | 라벨코드 |
|---|---|---|
| 1 | 벼 | R |

## 본문

| ID | 제목 | 카드구성 | Sizing | 분량 |
|---|---|---|---|---|
| 1.1 | 노지 용수·관개 | 3카드 | L | 12p |
| G1 | 마늘 생육관리 | 2카드 | S | 6p |
| A-1 | 벼 별첨 | 1카드 | XL | 30p |
"""


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


def test_map_sizing_known_values():
    assert map_sizing("S") == "short"
    assert map_sizing("M") == "medium"
    assert map_sizing("L") == "long"
    assert map_sizing("XL") == "long"
    assert map_sizing(" l ") == "long"   # 공백·소문자 정규화


def test_map_sizing_korean_and_unknown():
    assert map_sizing("대") == "long"
    assert map_sizing("") is None
    assert map_sizing("기타") is None


def test_split_table_row():
    assert split_table_row("| 1.1 | 관개 | L |") == ["1.1", "관개", "L"]
    assert split_table_row("|A-1|벼|XL|") == ["A-1", "벼", "XL"]


def test_is_separator_row():
    assert is_separator_row("|---|---|---|") is True
    assert is_separator_row("| :--- | ---: |") is True
    assert is_separator_row("| 1.1 | 관개 |") is False


def test_is_pure_id():
    assert is_pure_id("1.1") is True
    assert is_pure_id("A-1") is True
    assert is_pure_id("G1") is True
    assert is_pure_id("벼") is False         # 한글 제목
    assert is_pure_id("관개 자동화") is False  # 공백 포함


def test_parse_toc_table_extracts_only_item_table():
    rows = parse_toc_table(TABLE_TOC)
    ids = [r["id"] for r in rows]
    # 메타표(작성일)·매핑표(1 벼)는 '제목' 칼럼이 없어 제외, 항목표 3건만
    assert ids == ["1.1", "G1", "A-1"]


def test_parse_toc_table_maps_sizing_to_length():
    rows = {r["id"]: r for r in parse_toc_table(TABLE_TOC)}
    assert rows["1.1"]["title"] == "노지 용수·관개"
    assert rows["1.1"]["estimated_length"] == "long"    # L
    assert rows["G1"]["estimated_length"] == "short"    # S
    assert rows["A-1"]["estimated_length"] == "long"    # XL→long


def test_parse_toc_file_autodetects_table(tmp_path):
    f = tmp_path / "toc.md"
    f.write_text(TABLE_TOC, encoding="utf-8")
    sections = parse_toc_file(f)
    assert [s["id"] for s in sections] == ["1.1", "G1", "A-1"]


def test_parse_toc_file_still_parses_plaintext(tmp_path):
    f = tmp_path / "toc.txt"
    f.write_text("1.1 관개\n● 점적관수\n● 물수요 예측\n", encoding="utf-8")
    sections = parse_toc_file(f)
    assert sections[0]["id"] == "1.1"
    assert sections[0]["subtopics"] == ["점적관수", "물수요 예측"]
