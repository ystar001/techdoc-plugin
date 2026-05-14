"""autopilot_state.json read/write (v1.3.0)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_SCHEMA_VERSION = "0.1.0"
STATE_FILENAME = "autopilot_state.json"

# Stage 정의 (chunk granularity B 결정)
ALL_STAGE_IDS = (
    "outline",
    "research_A", "research_B", "research_C",
    "merge_research",
    "write_A", "write_B", "write_C",
    "review",
    "render",
)


def _empty_state() -> dict:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "started_at": None,
        "title": None,
        "config": {},
        "stages": {},
        "wake_ups": [],
        "consecutive_card_failures": 0,
        "halt_reason": None,
        "completed_at": None,
    }


def init_state(
    output_dir: Path,
    title: str,
    config: dict,
    num_section_groups: int = 3,
) -> dict:
    """신규 autopilot_state 생성. 섹션 그룹 수에 따라 research_*·write_*만 포함."""
    state = _empty_state()
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["title"] = title
    state["config"] = dict(config)
    groups = ["A", "B", "C"][:num_section_groups]
    stages: dict[str, str] = {"outline": "pending"}
    for g in groups:
        stages[f"research_{g}"] = "pending"
    stages["merge_research"] = "pending"
    for g in groups:
        stages[f"write_{g}"] = "pending"
    stages["review"] = "pending"
    stages["render"] = "pending"
    state["stages"] = stages
    return state


def load_state(output_dir: Path) -> dict:
    """state.json 로드. 파일 없으면 빈 state 반환."""
    path = Path(output_dir) / STATE_FILENAME
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # schema_version 누락 보정
        if "schema_version" not in data:
            data["schema_version"] = STATE_SCHEMA_VERSION
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_state()


def save_state(output_dir: Path, state: dict) -> None:
    path = Path(output_dir) / STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_stage(state: dict, chunk_id: str, status: str) -> None:
    """stages[chunk_id] = status. 정의되지 않은 chunk는 무시."""
    if chunk_id in state.get("stages", {}):
        state["stages"][chunk_id] = status


def append_wake_up(state: dict, entry: dict) -> None:
    """wake_ups 배열에 1개 추가."""
    state.setdefault("wake_ups", []).append(entry)


def mark_completed(state: dict) -> None:
    state["completed_at"] = datetime.now(timezone.utc).isoformat()


def mark_halted(state: dict, reason: str) -> None:
    state["halt_reason"] = reason
