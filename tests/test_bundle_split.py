"""bundle_split — 규칙 대장을 층별 묶음으로 (v1.11-a, 설계 D2). 합성 표본만 쓴다."""
from scripts.bundle_split import domain_word_hits, gate_rule_index, split_report, split_rules


def _r(rid, layer, status="적용됨", gates=(), rule="본문", title="제목"):
    return {"id": rid, "title": title, "rule": rule, "core": ["품질"], "area": rid[:2],
            "layer": layer, "status": status,
            "enforce": [{"gate": g, "level": "막음"} for g in gates]}


RULES = [
    _r("Q1-001", "본체", gates=("V1",)),
    _r("Q1-002", "본체", gates=("V76~V78",)),
    _r("Q6-001", "문서종류"),
    _r("Q3-001", "시리즈"),
    _r("Q3-002", "분야"),
    _r("Q1-003", "본체", status="대체됨", gates=("V9",)),
]


def test_split_by_layer_and_drop_superseded():
    out = split_rules(RULES)
    assert [r["id"] for r in out["core"]] == ["Q1-001", "Q1-002"]
    assert [r["id"] for r in out["kind"]] == ["Q6-001"]
    assert [r["id"] for r in out["domain"]] == ["Q3-002"]
    assert [r["id"] for r in out["series"]] == ["Q3-001"]
    assert out["superseded"] == ["Q1-003"]


def test_gate_rule_index_expands_range_and_skips_superseded():
    idx = gate_rule_index(RULES)
    assert idx["V1"] == ["Q1-001"]
    assert idx["V76"] == idx["V77"] == idx["V78"] == ["Q1-002"]
    assert "V9" not in idx


def test_report_lists_unreferenced_gates_and_no_enforce():
    rep = split_report(RULES, {"V1", "V2", "V76", "V77", "V78"})
    assert rep["unreferenced_gates"] == ["V2"]
    assert rep["no_enforce"] == ["Q3-001", "Q3-002", "Q6-001"]
    assert rep["counts"] == {"core": 2, "kind": 1, "domain": 1, "series": 1, "superseded": 1}


def test_report_blocking_rule_without_gate():
    rules = [{**_r("Q8-001", "본체"), "enforce": [{"review": "디자인", "level": "막음"}]}]
    assert split_report(rules, set())["blocking_rules_without_gate"] == ["Q8-001"]


def test_domain_word_hits_only_core_layer():
    rules = [_r("Q1-001", "본체", rule="가상분야낱말을 쓴다"), _r("Q3-001", "시리즈", rule="가상분야낱말")]
    assert domain_word_hits(rules, ["가상분야낱말"]) == [("Q1-001", "가상분야낱말")]
