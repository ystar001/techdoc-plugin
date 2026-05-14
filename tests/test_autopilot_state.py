"""Autopilot state 회귀 (v1.3.0)."""

from __future__ import annotations

import json
from pathlib import Path


def test_load_state_returns_empty_when_missing(tmp_path):
    from scripts.autopilot.state import load_state

    state = load_state(tmp_path)
    assert state["schema_version"] == "0.1.0"
    assert state["title"] is None
    assert state["stages"] == {}
    assert state["wake_ups"] == []
    assert state["halt_reason"] is None
    assert state["completed_at"] is None


def test_init_state_creates_default_stages(tmp_path):
    from scripts.autopilot.state import init_state

    config = {"max_wall_clock_seconds": 14400, "max_warnings": 10}
    state = init_state(tmp_path, title="T", config=config, num_section_groups=3)

    expected_stages = {
        "outline", "research_A", "research_B", "research_C",
        "merge_research", "write_A", "write_B", "write_C",
        "review", "render",
    }
    assert set(state["stages"].keys()) == expected_stages
    assert all(v == "pending" for v in state["stages"].values())
    assert state["title"] == "T"
    assert state["config"]["max_wall_clock_seconds"] == 14400


def test_init_state_handles_fewer_section_groups(tmp_path):
    from scripts.autopilot.state import init_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    # 2 그룹이면 research_C·write_C 생략
    assert "research_A" in state["stages"]
    assert "research_B" in state["stages"]
    assert "research_C" not in state["stages"]
    assert "write_C" not in state["stages"]


def test_save_and_load_round_trip(tmp_path):
    from scripts.autopilot.state import init_state, load_state, save_state

    s = init_state(tmp_path, title="T", config={}, num_section_groups=3)
    s["stages"]["outline"] = "completed"
    s["wake_ups"].append({"ts": "2026-05-13T10:00:00Z", "chunk": "outline", "duration_s": 80})
    save_state(tmp_path, s)

    s2 = load_state(tmp_path)
    assert s2["stages"]["outline"] == "completed"
    assert len(s2["wake_ups"]) == 1


def test_save_state_writes_pretty_json(tmp_path):
    """디버깅 편의 위해 indent=2로 저장."""
    from scripts.autopilot.state import init_state, save_state

    s = init_state(tmp_path, title="T", config={}, num_section_groups=3)
    save_state(tmp_path, s)
    raw = (tmp_path / "autopilot_state.json").read_text(encoding="utf-8")
    assert "  " in raw  # indented
    assert raw.endswith("\n") or raw.endswith("}")
