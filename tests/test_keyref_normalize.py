"""KeyRef 정규화 — 조용히 버리지 않음 (v1.10.2 — F55·F61·F78)."""
from techdoc_core.keyref_normalize import normalize_keyref
from techdoc_core.schemas import KeyRefSchema


def _minimal(**kw):
    d = {"id": "REF-001", "category": "학술", "source": "출처", "year": 2020,
         "title": "제목", "reliability": "확인됨"}
    d.update(kw)
    return d


def test_key_numbers_dict_is_stringified():
    d, notes = normalize_keyref({"key_numbers": [{"ISO 11783 유지": "TC23/SC19"}, "30%"]})
    assert d["key_numbers"] == ["ISO 11783 유지: TC23/SC19", "30%"]
    assert len(notes) == 1


def test_reliability_alias_mapped():
    d, _ = normalize_keyref({"reliability": "교차확인필요"})
    assert d["reliability"] == "단일출처"


def test_unknown_reliability_demoted_not_dropped():
    d, notes = normalize_keyref({"reliability": "애매함"})
    assert d["reliability"] == "미확인"
    assert "애매함" in notes[0]


def test_valid_data_untouched_and_input_not_mutated():
    src = _minimal(key_numbers=["a"])
    d, notes = normalize_keyref(src)
    assert d == src and notes == []
    src2 = {"key_numbers": [{"k": "v"}]}
    normalize_keyref(src2)
    assert src2 == {"key_numbers": [{"k": "v"}]}


def test_year_numeric_string_coerced():
    d, _ = normalize_keyref({"year": "1985"})
    assert d["year"] == 1985


def test_keyref_accepts_pre_1990_year():
    KeyRefSchema(**_minimal(year=1985))
