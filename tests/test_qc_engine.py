"""qc 엔진 — 판정 4값과 집행 수준 5종, 대상 0, 자기검사, 결과 JSON (v1.11-a — F85·F86·F104)."""
import json

import pytest

from techdoc_core.bundles.schema import GateSpec
from techdoc_core.qc import registry
from techdoc_core.qc.config import default_config
from techdoc_core.qc.engine import exit_code, format_report, run_qc, run_selftests
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model


@pytest.fixture
def reg():
    saved = dict(registry.REGISTRY)
    registry.REGISTRY.clear()
    yield registry.REGISTRY
    registry.REGISTRY.clear()
    registry.REGISTRY.update(saved)


def _spec(gid, level="막음", expects=None):
    return GateSpec(id=gid, title=f"{gid} 검사", rules=["Q1-001"], layer="본체", core=["품질"],
                    level=level, inputs=["tree"], expects=expects or {})


def _const(gid, targets, n, loc="x"):
    @gate(gid)
    def _g(model):
        return GateOutput(targets, [Finding(f"{loc}:{i}", "m") for i in range(n)])
    return _g


def _run(model, specs, cfg=None):
    return run_qc(model, {s.id: s for s in specs}, dict(registry.REGISTRY), cfg or default_config(model.root))


def _res(report, gid):
    return next(r for r in report["results"] if r["gate"] == gid)


def test_fail_pass_notarget_verdicts(reg):
    _const("G1", 5, 2)
    _const("G2", 5, 0)
    _const("G3", 0, 0)
    rep = _run(sample_model(tree={"a.md": "x"}), [_spec("G1"), _spec("G2"), _spec("G3")])
    assert (_res(rep, "G1")["verdict"], _res(rep, "G1")["count"]) == ("fail", 2)
    assert _res(rep, "G2")["verdict"] == "pass"
    assert _res(rep, "G3")["verdict"] == "no-target"
    assert rep["summary"]["blocking_total"] == 2 and exit_code(rep) == 1


def test_expects_turns_notarget_into_fail(reg):
    _const("G1", 0, 0)
    rep = _run(sample_model(kind="methodology", tree={"a.md": "x"}),
               [_spec("G1", expects={"methodology": ">=1"})])
    r = _res(rep, "G1")
    assert r["verdict"] == "fail" and "있어야 할 대상" in r["reason"]


def test_spec_without_function_is_skip(reg):
    rep = _run(sample_model(tree={"a.md": "x"}), [_spec("G9")])
    assert (_res(rep, "G9")["verdict"], _res(rep, "G9")["reason"]) == ("skip", "구현 없음")
    assert exit_code(rep) == 0


def test_gates_off_is_skip(reg):
    _const("G1", 5, 3)
    cfg = default_config(sample_model().root)
    cfg.gates_off = ["G1"]
    rep = _run(sample_model(tree={"a.md": "x"}), [_spec("G1")], cfg)
    assert _res(rep, "G1")["verdict"] == "skip" and exit_code(rep) == 0


def test_pilot_level_excluded_from_blocking(reg):
    _const("G1", 10, 5000)
    rep = _run(sample_model(tree={"a.md": "x"}), [_spec("G1", level="시범")])
    assert rep["summary"]["pilot_total"] == 5000
    assert rep["summary"]["blocking_total"] == 0 and exit_code(rep) == 0


def test_level_override_from_config(reg):
    _const("G1", 5, 2)
    cfg = default_config(sample_model().root)
    cfg.level_overrides = {"G1": "경고"}
    rep = _run(sample_model(tree={"a.md": "x"}), [_spec("G1")], cfg)
    assert _res(rep, "G1")["level"] == "경고"
    assert rep["summary"]["warning_total"] == 2 and exit_code(rep) == 0


def test_empty_project_exit_2(reg, tmp_path):
    _const("G1", 5, 1)
    rep = _run(sample_model(root=tmp_path), [_spec("G1")])
    assert exit_code(rep) == 2 and rep["results"] == []
    assert "입력 없음" in rep["warnings"][0]


def test_exempt_removes_card_findings(reg):
    _const("G1", 3, 2, loc="1.1")
    m = sample_model(tree={"a.md": "x"}, exempt={"1.1": ["G1"]})
    rep = _run(m, [_spec("G1")])
    assert _res(rep, "G1")["count"] == 0 and _res(rep, "G1")["verdict"] == "pass"


def test_selftest_mismatch_reported(reg):
    @gate("G1", samples=[Sample(sample_model(tree={"a.md": "x"}), expect=1)])
    def _g(model):
        return GateOutput(1, [])
    errs = run_selftests(dict(registry.REGISTRY))
    assert errs == ["G1: 표본 1 기대 1 실제 0"]
    rep = _run(sample_model(tree={"a.md": "x"}), [_spec("G1")])
    rep["selftest_errors"] = errs
    assert exit_code(rep) == 3


def test_duplicate_registration_rejected(reg):
    _const("G1", 1, 0)
    with pytest.raises(ValueError):
        _const("G1", 1, 0)


def test_report_is_deterministic_and_sorted(reg):
    _const("G10", 1, 1)
    _const("G2", 1, 1)
    m = sample_model(tree={"a.md": "x"})
    a = _run(m, [_spec("G10"), _spec("G2")])
    b = _run(m, [_spec("G2"), _spec("G10")])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert [r["gate"] for r in a["results"]] == ["G2", "G10"]
    assert a["schema"] == "techdoc-qc/1"


def test_format_report_marks(reg):
    _const("G1", 5, 2)
    _const("G2", 0, 0)
    text = format_report(_run(sample_model(tree={"a.md": "x"}), [_spec("G1"), _spec("G2")]))
    assert "✗ 막음" in text and "— 대상 없음" in text
