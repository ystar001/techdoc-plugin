"""Autopilot 6 safety 트리거 회귀."""

from __future__ import annotations

import json
from pathlib import Path


def test_quality_fail_trigger_returns_reason(tmp_path):
    from scripts.autopilot.triggers import check_quality_fail

    quality_report = {"total_fail": 1, "total_warning": 0}
    reason = check_quality_fail(quality_report, max_warnings=10)
    assert reason == "quality_fail"


def test_quality_fail_trigger_no_match_when_zero(tmp_path):
    from scripts.autopilot.triggers import check_quality_fail

    reason = check_quality_fail({"total_fail": 0, "total_warning": 0}, max_warnings=10)
    assert reason is None


def test_quality_warn_exceeded_trigger(tmp_path):
    from scripts.autopilot.triggers import check_quality_fail

    reason = check_quality_fail({"total_fail": 0, "total_warning": 11}, max_warnings=10)
    assert reason == "quality_warn_exceeded"


def test_quality_warn_within_threshold(tmp_path):
    from scripts.autopilot.triggers import check_quality_fail

    reason = check_quality_fail({"total_fail": 0, "total_warning": 10}, max_warnings=10)
    assert reason is None  # 10 == 10 (초과 아님)


def test_card_failures_exceeded():
    from scripts.autopilot.triggers import check_card_failures

    state = {"consecutive_card_failures": 6}
    reason = check_card_failures(state, max_failures=5)
    assert reason == "card_failures_exceeded"


def test_card_failures_within_threshold():
    from scripts.autopilot.triggers import check_card_failures

    state = {"consecutive_card_failures": 5}
    reason = check_card_failures(state, max_failures=5)
    assert reason is None


def test_wall_clock_exceeded():
    from scripts.autopilot.triggers import check_wall_clock
    from datetime import datetime, timezone, timedelta

    long_ago = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    state = {"started_at": long_ago, "config": {"max_wall_clock_seconds": 14400}}  # 4h
    reason = check_wall_clock(state)
    assert reason == "wall_clock_exceeded"


def test_wall_clock_within_budget():
    from scripts.autopilot.triggers import check_wall_clock
    from datetime import datetime, timezone, timedelta

    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    state = {"started_at": recent, "config": {"max_wall_clock_seconds": 14400}}
    reason = check_wall_clock(state)
    assert reason is None


def test_state_corruption_when_no_schema_version(tmp_path):
    from scripts.autopilot.triggers import check_state_corruption

    writer_state_path = tmp_path / "writer_state.json"
    writer_state_path.write_text('{"section_states": {}}', encoding="utf-8")  # no schema_version
    reason = check_state_corruption(tmp_path)
    assert reason == "state_corruption"


def test_state_corruption_when_writer_state_parse_fails(tmp_path):
    from scripts.autopilot.triggers import check_state_corruption

    (tmp_path / "writer_state.json").write_text("not valid json", encoding="utf-8")
    reason = check_state_corruption(tmp_path)
    assert reason == "state_corruption"


def test_state_corruption_passes_when_valid(tmp_path):
    from scripts.autopilot.triggers import check_state_corruption

    (tmp_path / "writer_state.json").write_text(
        json.dumps({"schema_version": "0.1.0", "section_states": {}}),
        encoding="utf-8",
    )
    reason = check_state_corruption(tmp_path)
    assert reason is None


def test_state_corruption_skips_when_writer_state_missing(tmp_path):
    """outline 단계 전에는 writer_state.json이 없음 — 정상."""
    from scripts.autopilot.triggers import check_state_corruption

    assert check_state_corruption(tmp_path) is None


def test_manual_stop_detected(tmp_path):
    from scripts.autopilot.triggers import check_manual_stop

    (tmp_path / "autopilot.stop").write_text("", encoding="utf-8")
    reason = check_manual_stop(tmp_path)
    assert reason == "manual_stop"


def test_manual_stop_not_detected(tmp_path):
    from scripts.autopilot.triggers import check_manual_stop

    assert check_manual_stop(tmp_path) is None


def test_evaluate_all_returns_first_trigger_found(tmp_path):
    """모든 트리거를 순회. 첫 번째 위반 반환."""
    from scripts.autopilot.triggers import evaluate_all

    (tmp_path / "autopilot.stop").write_text("", encoding="utf-8")
    state = {
        "started_at": (
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            .isoformat()
        ),
        "config": {"max_wall_clock_seconds": 14400, "max_warnings": 10, "max_consecutive_card_failures": 5},
        "consecutive_card_failures": 0,
    }
    quality_report = {"total_fail": 0, "total_warning": 0}
    reason = evaluate_all(state, tmp_path, quality_report)
    # manual_stop 또는 다른 위반 — 최소 1개 발견됨
    assert reason is not None


def test_evaluate_all_returns_none_when_clean(tmp_path):
    """모든 트리거 통과."""
    from scripts.autopilot.triggers import evaluate_all
    from datetime import datetime, timezone

    state = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "config": {"max_wall_clock_seconds": 14400, "max_warnings": 10, "max_consecutive_card_failures": 5},
        "consecutive_card_failures": 0,
    }
    quality_report = {"total_fail": 0, "total_warning": 0}
    reason = evaluate_all(state, tmp_path, quality_report)
    assert reason is None
