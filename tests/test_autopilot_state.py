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
        "review", "deepdive", "render",
    }
    assert set(state["stages"].keys()) == expected_stages
    # deepdive는 config에 요청 없으면 skipped, 나머지는 pending (F9-i)
    assert state["stages"]["deepdive"] == "skipped"
    assert all(
        v == "pending"
        for k, v in state["stages"].items()
        if k != "deepdive"
    )
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


def test_update_stage_changes_status():
    from scripts.autopilot.state import init_state, update_stage

    s = init_state(Path("/tmp"), title="T", config={}, num_section_groups=3)
    update_stage(s, "outline", "completed")
    assert s["stages"]["outline"] == "completed"


def test_update_stage_ignores_unknown_chunk():
    from scripts.autopilot.state import init_state, update_stage

    s = init_state(Path("/tmp"), title="T", config={}, num_section_groups=3)
    update_stage(s, "nonexistent_chunk", "completed")
    assert "nonexistent_chunk" not in s["stages"]


def test_append_wake_up_records_entry():
    from scripts.autopilot.state import init_state, append_wake_up

    s = init_state(Path("/tmp"), title="T", config={}, num_section_groups=3)
    append_wake_up(s, {"ts": "x", "chunk": "outline", "duration_s": 80, "result": "success"})
    assert len(s["wake_ups"]) == 1
    assert s["wake_ups"][0]["chunk"] == "outline"


def test_mark_completed_sets_timestamp():
    from scripts.autopilot.state import init_state, mark_completed

    s = init_state(Path("/tmp"), title="T", config={}, num_section_groups=3)
    assert s["completed_at"] is None
    mark_completed(s)
    assert s["completed_at"] is not None


def test_mark_halted_sets_reason():
    from scripts.autopilot.state import init_state, mark_halted

    s = init_state(Path("/tmp"), title="T", config={}, num_section_groups=3)
    mark_halted(s, "quality_fail")
    assert s["halt_reason"] == "quality_fail"


# ---------------------------------------------------------------------------
# F9-i: deepdive stage conditional in init_state
# ---------------------------------------------------------------------------


def test_init_state_includes_deepdive_pending_when_requested(tmp_path):
    from scripts.autopilot.state import init_state

    state = init_state(tmp_path, "T", {"deep_dive_auto": 5})
    assert state["stages"]["deepdive"] == "pending"


def test_init_state_skips_deepdive_when_not_requested(tmp_path):
    from scripts.autopilot.state import init_state

    state = init_state(tmp_path, "T", {"deep_dive_auto": 0})
    assert state["stages"]["deepdive"] == "skipped"


def test_init_state_deepdive_before_render(tmp_path):
    from scripts.autopilot.state import init_state

    keys = list(init_state(tmp_path, "T", {"deep_dive_auto": 3})["stages"])
    assert keys.index("deepdive") < keys.index("render")


# ---------------------------------------------------------------------------
# F9-ii: scan_completed_stages + resume_from_disk (중반 재개)
# ---------------------------------------------------------------------------


def _touch(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}", encoding="utf-8")


def test_scan_detects_outline_and_refs(tmp_path):
    from scripts.autopilot.state import scan_completed_stages

    _touch(tmp_path / "draft_outline.json")
    _touch(tmp_path / "reference_list.json")
    done = scan_completed_stages(tmp_path)
    assert "outline" in done and "merge_research" in done


def test_scan_detects_review_dir(tmp_path):
    from scripts.autopilot.state import scan_completed_stages

    (tmp_path / "reviews").mkdir()
    (tmp_path / "reviews" / "tech.md").write_text("x", encoding="utf-8")
    assert "review" in scan_completed_stages(tmp_path)


def test_init_state_resume_marks_completed(tmp_path):
    from scripts.autopilot.state import init_state

    _touch(tmp_path / "draft_outline.json")
    state = init_state(tmp_path, "T", {"deep_dive_auto": 0}, resume_from_disk=True)
    assert state["stages"]["outline"] == "completed"
    # 산출물 없는 stage는 pending 유지
    assert state["stages"]["review"] == "pending"
