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
