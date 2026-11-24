"""standard 모드 산출물 읽기 (v1.11-c — Review Focus 1).

writer_state.json + document_draft.json(또는 document_final.json·sections/section_*.json)만 있는
플러그인 기본 산출물에서도 /techdoc-qc가 「입력 없음」이 아니라 카드로 읽어 게이트를 돌린다.
"""
import json

from scripts.qc import main as qc_main
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.card_text import sections_of
from techdoc_core.qc.config import default_config

_CITATION_GATES = ("V8", "V13")


def _w(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _standard_project(tmp_path, doc: dict, doc_name="document_draft.json",
                      refs=("REF-001", "REF-002", "REF-003", "REF-004")):
    out = tmp_path / "output"
    _w(out / "writer_state.json", {"section_states": {}})
    if doc_name:
        _w(out / doc_name, doc)
    _w(out / "reference_list.json", {"refs": [{"id": r, "title": f"문헌 {r}"} for r in refs]})
    return tmp_path


def test_standard_draft_cards_are_read(tmp_path, fake_document_final):
    """conftest의 Document 꼴(블록이 카드 최상위에 펼쳐진 옛 꼴) — 카드 3장 + 절 1."""
    root = _standard_project(tmp_path, fake_document_final)
    model = build_model(root, default_config(root))
    assert not model.is_empty()
    assert {"1.1.1", "2.1.1", "3.1.1"} <= set(model.cards)
    # 본문 블록은 blocks dict로 모이고 card_text.sections_of가 그대로 읽는다
    keys = [k for k, _, _ in sections_of(model.cards["1.1.1"])]
    assert keys == ["overview", "principle", "components", "performance", "pros_cons",
                    "differentiation", "references"]
    assert "ref_ids" not in model.cards["1.1.1"]  # 선언 목록은 본문 인용이 아니다
    assert "1.1" in model.cards  # 절 html_content도 읽는다


def test_standard_blocks_dict_cards(tmp_path):
    """models.TechCard.to_dict 꼴(blocks dict)."""
    doc = {"sections": [], "tech_cards": [
        {"id": "1.1.1", "name": "가", "blocks": {"overview": "개요[REF-001].",
                                                 "references": "[REF-001]"},
         "ref_ids": ["REF-001"]}]}
    root = _standard_project(tmp_path, doc, refs=("REF-001",))
    model = build_model(root, default_config(root))
    assert sections_of(model.cards["1.1.1"]) == [("overview", "", "개요[REF-001]."),
                                                 ("references", "", "[REF-001]")]


def test_standard_cli_runs_gates_not_input_empty(tmp_path, fake_document_final):
    root = _standard_project(tmp_path, fake_document_final)
    code = qc_main([str(root)])
    assert code != 2
    rep = json.loads((root / "output" / "qc_report.json").read_text(encoding="utf-8"))
    assert rep["input_empty"] is False
    rows = {r["gate"]: r for r in rep["results"]}
    for g in _CITATION_GATES:
        assert rows[g]["targets_read"] > 0, g


def test_standard_final_and_section_files_fallback(tmp_path, fake_document_final):
    root = _standard_project(tmp_path, fake_document_final, doc_name="document_final.json")
    assert "1.1.1" in build_model(root, default_config(root)).cards

    root2 = tmp_path / "p2"
    _standard_project(root2, {}, doc_name=None)
    _w(root2 / "output" / "sections" / "section_1.1.json",
       {"tech_cards": [{"id": "1.1.1", "blocks": {"overview": "가"}}]})
    _w(root2 / "output" / "sections" / "section_1.2.json",
       {"tech_cards": [{"id": "1.2.1", "blocks": {"overview": "나"}}]})
    assert {"1.1.1", "1.2.1"} <= set(build_model(root2, default_config(root2)).cards)


def test_standard_draft_wins_over_final(tmp_path):
    root = _standard_project(tmp_path, {"tech_cards": [{"id": "1.1.1", "blocks": {"o": "draft"}}]})
    _w(root / "output" / "document_final.json",
       {"tech_cards": [{"id": "9.9.9", "blocks": {"o": "final"}}]})
    assert set(build_model(root, default_config(root)).cards) == {"1.1.1"}


def test_standard_id_collision_keeps_both(tmp_path):
    doc = {"tech_cards": [{"id": "1.1.1", "blocks": {"o": "t"}}],
           "project_cards": [{"id": "1.1.1", "blocks": {"o": "p"}}]}
    root = _standard_project(tmp_path, doc)
    assert {"1.1.1", "1.1.1~project"} <= set(build_model(root, default_config(root)).cards)


def test_self_model_cards_take_precedence(tmp_path, fake_document_final):
    root = _standard_project(tmp_path, fake_document_final)
    _w(root / "output" / "cards" / "1.1_card.json", {"sections": {"s": {"body": "가"}}})
    assert set(build_model(root, default_config(root)).cards) == {"1.1"}
