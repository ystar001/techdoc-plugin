"""bundle_split — 규칙 대장을 층별 묶음으로 (v1.11-a, 설계 D2). 합성 표본만 쓴다."""
import pytest

from scripts.bundle_split import (
    PublicMapError,
    apply_public_map,
    convention_hits,
    domain_word_hits,
    gate_rule_index,
    gate_rules_not_public,
    public_rule,
    split_report,
    split_rules,
    wording_hash,
)


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


def test_domain_word_regex_entry():
    """`re:` 낱말은 정규식 — 낱말 머리가 같은 다른 낱말(가상어치)은 빼고 잡는다."""
    rules = [_r("Q1-001", "본체", rule="가상어 사이클"), _r("Q1-002", "본체", rule="가상어치 보강")]
    assert domain_word_hits(rules, ["re:가상어(?!치)"]) == [("Q1-001", "re:가상어(?!치)")]


# ── 수치·관례가 든 본체 규칙 (v1.11-c, E18 9) ─────────────────────────────────────

def test_convention_hits_number_unit_range_marker():
    rules = [
        _r("Q5-001", "본체", title="헤드라인 36자 안팎", rule="최대 40자로 쓴다."),
        _r("Q6-001", "본체", rule="핵심 질문은 2~4로 둔다."),
        _r("Q6-002", "본체", rule="상자는 일곱 가지만 쓴다."),
        _r("Q7-001", "본체", rule="캡션은 값: tok.caption_max_chars 이하, 설정은 limits.json"),
        _r("Q7-002", "본체", rule="원리만 말하는 규칙."),
        _r("Q7-003", "시리즈", rule="표지는 15편 모두 같은 띠."),  # 본체가 아니면 보지 않음
    ]
    hits = {h["id"]: h for h in convention_hits(rules)}
    assert set(hits) == {"Q5-001", "Q6-001", "Q6-002", "Q7-001"}
    assert hits["Q5-001"]["kinds"] == ["num_unit", "range"]
    assert "36자" in hits["Q5-001"]["matches"] and "40자" in hits["Q5-001"]["matches"]
    assert hits["Q6-001"]["kinds"] == ["range"]
    assert hits["Q6-002"]["kinds"] == ["num_word"]
    assert hits["Q7-001"]["matches"] == ["tok.caption_max_chars", "limits.json"]


def test_convention_hits_ignore_ids_and_title_rule_join():
    """규칙·게이트·단계 id 속 숫자는 수치가 아님, 제목 끝 숫자와 본문 첫 낱말을 잇지 않음."""
    rules = [_r("Q4-001", "본체", title="Q4-026 과 V71 을 따름 — 700·500",
                rule="편 색은 S2 단계에서 R² 값과 함께 본다.")]
    assert convention_hits(rules) == []


# ── 본체 규칙 공개판 (v1.11-c, E15) ───────────────────────────────────────────────

def _ledger_row(rid, rule="원리 문장", **extra):
    return {**_r(rid, "본체", rule=rule, gates=("V1",)), "alias": ["옛 번호"], "source": "출처",
            "note": "내부 메모", "exceptions": "예외", "rel": {"refines": ["옛"]}, **extra}


def _map(**entries):
    return {"schema": "techdoc-core-public-map/1", "rules": entries}


def test_public_rule_keeps_only_public_fields():
    row = public_rule({**_ledger_row("Q1-001", status="보류(내부 사정)"),
                       "enforce": [{"gate": "V1", "level": "막음"}, {"tool": "x.py", "level": "구조"}]})
    assert set(row) == {"id", "title", "rule", "core", "area", "layer", "status", "enforce"}
    assert row["status"] == "보류"
    assert row["enforce"] == [{"gate": "V1", "level": "막음"}]


def test_apply_public_map_keep_reword_move():
    core = [_ledger_row("Q1-001"), _ledger_row("Q1-002", rule="가상분야낱말 규칙"),
            _ledger_row("Q5-001", rule="헤드라인 36자"), _ledger_row("Q1-003")]
    h = {r["id"]: wording_hash(r) for r in core}
    mapping = _map(**{
        "Q1-001": {"action": "keep", "reason": "원리", "hash": h["Q1-001"]},
        "Q1-002": {"action": "reword", "reason": "분야 낱말", "rule": "중립 규칙",
                   "hash": h["Q1-002"]},
        "Q5-001": {"action": "kind", "to": "deck", "reason": "발표자료 관례",
                   "hash": h["Q5-001"]}})
    out = apply_public_map(core, mapping, must_judge={"Q1-001", "Q1-002", "Q5-001"})
    assert [r["id"] for r in out["public"]] == ["Q1-001", "Q1-002", "Q1-003"]
    pub = {r["id"]: r for r in out["public"]}
    assert pub["Q1-002"]["rule"] == "중립 규칙" and pub["Q1-002"]["edition"] == "플러그인 판 문구"
    assert core[1]["rule"] == "가상분야낱말 규칙"  # 대장 원문은 그대로
    assert out["reworded"] == ["Q1-002"] and out["kept"] == ["Q1-001"]
    moved = out["moved"]["kind"][0]
    assert (moved["id"], moved["layer"], moved["moved_kind"]) == ("Q5-001", "문서종류", "deck")


def test_apply_public_map_requires_judgment_and_current_hash():
    core = [_ledger_row("Q1-001"), _ledger_row("Q1-002")]
    stale = _map(**{"Q1-001": {"action": "keep", "reason": "원리", "hash": "0" * 16}})
    with pytest.raises(PublicMapError) as e:
        apply_public_map(core, stale, must_judge={"Q1-001", "Q1-002"})
    assert "Q1-001: 원문이 바뀜" in str(e.value) and "Q1-002: 판정 없음" in str(e.value)


def test_apply_public_map_rejects_reword_without_rule_and_unknown_action():
    core = [_ledger_row("Q1-001"), _ledger_row("Q1-002")]
    h = {r["id"]: wording_hash(r) for r in core}
    bad = _map(**{"Q1-001": {"action": "reword", "reason": "x", "hash": h["Q1-001"]},
                  "Q1-002": {"action": "drop", "reason": "x", "hash": h["Q1-002"]}})
    with pytest.raises(PublicMapError, match="rule"):
        apply_public_map(core, bad, must_judge=set())


def test_gate_rules_not_public():
    gates = [{"id": "V1", "rules": ["Q1-001", "Q6-009"]}, {"id": "V2", "rules": ["Q1-001"]}]
    assert gate_rules_not_public(gates, {"Q1-001"}) == {"V1": ["Q6-009"]}
