"""PLG·VC 게이트 ↔ 기존 CLI 결과 동치 (v1.11-c Task 3, 설계 D3.5).

게이트와 CLI 래퍼가 같은 측정 함수(`techdoc_core.qc.legacy`)를 부르므로, 같은 입력에서 지표마다
지적 수가 맞아야 한다. 수준은 FAIL → 막음, WARNING → 경고, 절대 분량 하한은 경고(E18).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.config import default_config
from techdoc_core.qc.engine import run_qc
from techdoc_core.qc.gates.legacy_quality import CQ_GATES, FG_METRICS
from techdoc_core.qc.registry import REGISTRY
from tests.test_legacy_wrapper_contract import self_model_fixture, standard_fixture


def _model(root: Path):
    return build_model(root, default_config(root))


def _count(gid: str, model) -> int:
    return len(REGISTRY[gid](model).findings)


def test_self_model_gates_match_check_quality_and_verify_cards(tmp_path):
    from scripts import check_quality, verify_cards

    out = self_model_fixture(tmp_path)
    model = _model(tmp_path)
    cli = check_quality.run_quality_check(out)
    cards = [c for c in cli["cards"] if not c["path"].endswith("broken_card.json")]
    fmt = Counter(i["metric"] for c in cards for i in c["issues"] if i.get("metric"))
    for m in FG_METRICS:
        assert _count(f"PLG-FG-{m}", model) == fmt.get(m, 0), m
    size = sum(1 for c in cards for i in c["issues"] if "metric" not in i)
    assert _count("PLG-CQ-self_model_length", model) == size == 5
    caps = cli["phase_a"]["caption_issues"]
    for kind in ("duplicate", "gap", "dangling_ref"):
        gid = "PLG-CQ-caption_" + kind
        assert _count(gid, model) == len(caps[kind]), kind

    vc = [verify_cards.check_card(p) for p in sorted((out / "cards").glob("*_card.json"))]
    letters = Counter(lt for r in vc for lt, *_ in r["checks"])
    for lt in "ABCDE":
        assert _count(f"VC-{lt}", model) == letters.get(lt, 0), lt
    assert letters["A"] == 1 and letters["E"] == 1
    # standard 지표 게이트는 self-model 입력에서 대상 없음
    assert REGISTRY["PLG-CQ-section_length"](model).targets_read == 0


def test_standard_gates_match_check_quality(tmp_path):
    from scripts import check_quality

    out = standard_fixture(tmp_path)
    model = _model(tmp_path)
    assert model.standard is not None
    cli = Counter(i["metric"] for i in check_quality.run_quality_check(out)["issues"])
    for metric, gid in CQ_GATES.items():
        assert _count(gid, model) == cli.get(metric, 0), metric
    assert _count("PLG-CQ-caption_dangling_ref", model) == cli["caption_dangling_ref"]
    assert _count("PLG-CQ-caption_duplicate", model) == cli.get("caption_duplicate", 0)
    # self-model 게이트는 standard 입력에서 대상 없음
    for gid in ("PLG-FG-visual_density", "PLG-CQ-self_model_length", "VC-C", "VC-A",
                "PLG-CQ-caption_gap"):
        assert REGISTRY[gid](model).targets_read == 0, gid


def test_size_lower_bounds_are_warnings_in_core():
    """E18 — 도구의 절대 분량 FAIL은 qc 본체 기본에서 경고, 나머지 FAIL은 막음."""
    specs = load_gate_specs([("본체", core_bundle_dir())])
    for gid in ("PLG-CQ-self_model_length", "PLG-CQ-section_length", "PLG-CQ-undersized_cards",
                "VC-C"):
        assert specs[gid].level == "경고", gid
    for gid in ("PLG-CQ-ai_estimate_ratio", "PLG-CQ-academic_ratio", "PLG-CQ-rd_ratio",
                "PLG-CQ-tech_card_block_fill", "VC-A", "VC-E"):
        assert specs[gid].level == "막음", gid
    for m in FG_METRICS:
        assert specs[f"PLG-FG-{m}"].level == "경고"


def test_qc_run_counts_size_shortfall_as_warning(tmp_path):
    self_model_fixture(tmp_path)
    model = _model(tmp_path)
    specs = load_gate_specs([("본체", core_bundle_dir())])
    sub = {g: specs[g] for g in ("PLG-CQ-self_model_length", "VC-C", "VC-A", "VC-E")}
    rep = run_qc(model, sub, dict(REGISTRY), default_config(tmp_path))
    rows = {r["gate"]: r for r in rep["results"]}
    assert rows["PLG-CQ-self_model_length"]["verdict"] == "fail"
    assert rep["summary"]["blocking_total"] == 2  # VC-A 깨진 카드 1 + VC-E citation_count=0 1
    assert rep["summary"]["warning_total"] == rows["PLG-CQ-self_model_length"]["count"] + \
        rows["VC-C"]["count"]


def test_thresholds_override_via_extra(tmp_path):
    self_model_fixture(tmp_path)
    cfg = default_config(tmp_path)
    cfg.extra = {"check_quality": {"size_thresholds": {"S": 10, "L2": 10, "P0": 10}},
                 "verify_cards": {"thresholds": {"S": 10, "L2": 10, "P0": 10}}}
    model = build_model(tmp_path, cfg)
    assert _count("PLG-CQ-self_model_length", model) == 0
    # VC-C: foo(ID 인식 실패 경고)·0.1(front matter 면제 표시)만 남는다
    assert _count("VC-C", model) == 2
