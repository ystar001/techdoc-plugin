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


def check_card_failures(state: dict, max_failures: int) -> str | None:
    """누적 카드 실패가 max_failures 초과 시 halt."""
    if state.get("consecutive_card_failures", 0) > max_failures:
        return "card_failures_exceeded"
    return None


def check_wall_clock(state: dict) -> str | None:
    """started_at + max_wall_clock_seconds 초과 시 halt."""
    started_at = state.get("started_at")
    config = state.get("config", {})
    max_seconds = config.get("max_wall_clock_seconds", 14400)
    if not started_at:
        return None
    start = datetime.fromisoformat(started_at)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    if elapsed > max_seconds:
        return "wall_clock_exceeded"
    return None


def check_state_corruption(output_dir: Path) -> str | None:
    """writer_state.json·autopilot_state.json parse 또는 schema_version 점검."""
    output_dir = Path(output_dir)

    # writer_state.json (존재 시만)
    ws_path = output_dir / "writer_state.json"
    if ws_path.exists():
        try:
            ws = json.loads(ws_path.read_text(encoding="utf-8"))
            if "schema_version" not in ws:
                return "state_corruption"
        except (OSError, json.JSONDecodeError):
            return "state_corruption"

    # autopilot_state.json (존재 시만)
    as_path = output_dir / "autopilot_state.json"
    if as_path.exists():
        try:
            ap = json.loads(as_path.read_text(encoding="utf-8"))
            if ap.get("schema_version") != "0.1.0":
                return "state_corruption"
        except (OSError, json.JSONDecodeError):
            return "state_corruption"

    return None
