"""DocModel과 어댑터 (v1.11-a)."""
import json

from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.card_text import card_level_fields, sections_of
from techdoc_core.qc.config import default_config


def test_sections_of_four_schema_variants():
    assert sections_of({"sections": {"s1": {"title": "가제", "body": "가"}}}) == [("s1", "가제", "가")]
    assert sections_of({"sections": {"s2": {"content": "나"}}}) == [("s2", "", "나")]
    assert sections_of({"blocks": {"b1": {"narrative": "다"}, "meta": {"body": "빼기"}}}) == [("b1", "", "다")]
    assert sections_of({"blocks": [{"block_id": "x", "title": "t", "body": "라"}]}) == [("x", "t", "라")]


def test_sections_of_joins_string_fields_when_no_body_key():
    assert sections_of({"sections": {"s": {"title": "t", "a": "첫", "b": "둘"}}}) == [("s", "t", "첫\n\n둘")]


def test_card_level_fields_quick_summary_lists_and_scope_note():
    card = {"quick_summary": {"goal": "목표", "questions": ["물음1", "물음2"]}, "scope_note": "범위"}
    assert card_level_fields(card) == [("quick_summary", "[핵심요약]", "목표\n물음1\n물음2"),
                                       ("scope_note", "[범위 메모]", "범위")]


def _w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_build_model_reads_cards_tree_refs(tmp_path):
    out = tmp_path / "output"
    _w(out / "cards" / "1.1_card.json", json.dumps({"sections": {"s": {"body": "본문"}}}))
    _w(out / "cards" / "_old" / "9.9_card.json", "{}")
    _w(out / "render" / "tree" / "제1부" / "1.1. 서론.md", "# 1.1 서론\n")
    _w(out / "render" / "tree" / "참고문헌.md", "- 참고\n")
    _w(out / "render" / "tree" / "_draft.md", "빼기\n")
    _w(out / "reference_list.json", json.dumps({"refs": [{"id": "REF-001"}]}))
    m = build_model(tmp_path, default_config(tmp_path))
    assert list(m.cards) == ["1.1"]
    assert [t.rel for t in m.tree] == ["제1부/1.1. 서론.md"]
    assert [t.rel for t in m.reference_md] == ["참고문헌.md"]
    assert m.references[0]["id"] == "REF-001"
    assert not m.is_empty()


def test_broken_card_json_is_reported_not_crash(tmp_path):
    _w(tmp_path / "output" / "cards" / "1.1_card.json", "{깨짐")
    m = build_model(tmp_path, default_config(tmp_path))
    assert m.cards == {} and m.load_errors and "1.1_card.json" in m.load_errors[0]


def test_missing_paths_give_empty_model(tmp_path):
    assert build_model(tmp_path, default_config(tmp_path)).is_empty()


def test_draft_is_loaded_separately(tmp_path):
    _w(tmp_path / "output" / "draft" / "part1.md", "본문 [REF-001]\n")
    _w(tmp_path / "output" / "draft" / "_superseded_x.md", "빼기\n")
    m = build_model(tmp_path, default_config(tmp_path))
    assert [t.rel for t in m.draft] == ["part1.md"]


def test_reference_md_by_name_contains_and_full_md_fallback(tmp_path):
    _w(tmp_path / "output" / "render" / "tree" / "99_참고문헌.md", "- a\n")
    m = build_model(tmp_path, default_config(tmp_path))
    assert [t.rel for t in m.reference_md] == ["99_참고문헌.md"] and m.tree == []
    t2 = tmp_path / "b"
    _w(t2 / "output" / "render" / "tree" / "1.md", "# 1\n")
    _w(t2 / "output" / "render" / "doc_full.md", "# 1\n본문\n# 참고문헌\n- x\n")
    m2 = build_model(t2, default_config(t2))
    assert m2.reference_md[0].rel == "doc_full.md 참고문헌"
    assert m2.reference_md[0].text.startswith("\n# 참고문헌")


def test_non_utf8_md_is_reported_not_crash(tmp_path):
    p = tmp_path / "output" / "render" / "tree" / "a.md"
    p.parent.mkdir(parents=True)
    p.write_bytes("가나다".encode("cp949"))
    m = build_model(tmp_path, default_config(tmp_path))
    assert m.tree == [] and any("a.md" in e for e in m.load_errors)
