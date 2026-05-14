"""6 safety 트리거 평가 (v1.3.0).

quality_fail · quality_warn_exceeded · card_failures_exceeded
· wall_clock_exceeded · state_corruption · manual_stop

각 함수는 위반 시 reason 문자열을 반환, 아니면 None.
evaluate_all(state, output_dir, quality_report) → reason or None (전체 평가).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STOP_FLAG_FILENAME = "autopilot.stop"


def check_quality_fail(quality_report: dict, max_warnings: int) -> str | None:
    """check_quality 결과로 quality_fail / quality_warn_exceeded 평가."""
    if quality_report.get("total_fail", 0) > 0:
        return "quality_fail"
    if quality_report.get("total_warning", 0) > max_warnings:
        return "quality_warn_exceeded"
    return None
