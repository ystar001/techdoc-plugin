"""Runner end-to-end (chunk dispatch mock) 회귀."""

from __future__ import annotations

import json
from pathlib import Path


def test_run_iteration_halts_on_manual_stop(tmp_path):
    """autopilot.stop이 있으면 즉시 halt 반환."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)
    (tmp_path / "autopilot.stop").write_text("", encoding="utf-8")

    result = run_iteration(tmp_path, dispatcher=None)  # dispatcher 미사용
    assert result["status"] == "halt"
    assert result["reason"] == "manual_stop"


def test_run_iteration_done_when_all_complete(tmp_path):
    """모든 stage completed → done."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    for k in state["stages"]:
        state["stages"][k] = "completed"
    save_state(tmp_path, state)

    result = run_iteration(tmp_path, dispatcher=None)
    assert result["status"] == "done"


def test_run_iteration_returns_next_wake_up_when_chunk_dispatched(tmp_path):
    """dispatcher가 success 반환 → state 갱신 + next_wake_up_seconds."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)

    def fake_dispatcher(chunk_id: str, output_dir: Path) -> dict:
        return {"result": "success", "duration_s": 60, "quality_fail": 0, "quality_warn": 0}

    result = run_iteration(tmp_path, dispatcher=fake_dispatcher)
    assert result["status"] == "continue"
    assert result["next_wake_up_seconds"] >= 60
    assert result["next_wake_up_seconds"] <= 1500

    # state 확인
    saved = json.loads((tmp_path / "autopilot_state.json").read_text(encoding="utf-8"))
    assert saved["stages"]["outline"] == "completed"
    assert len(saved["wake_ups"]) == 1


def test_run_iteration_rate_limited_uses_longer_delay(tmp_path):
    """dispatcher가 rate_limited 반환 → 1200s 이상 지연."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)

    def fake_dispatcher(chunk_id, output_dir):
        return {"result": "rate_limited", "duration_s": 5, "quality_fail": 0, "quality_warn": 0}

    result = run_iteration(tmp_path, dispatcher=fake_dispatcher)
    assert result["status"] == "continue"
    assert result["next_wake_up_seconds"] >= 1200


def test_default_dispatcher_returns_command_hint(tmp_path):
    """기본 dispatcher는 chunk_id에 매핑된 명령 hint 반환."""
    from scripts.autopilot.runner import default_dispatcher

    result = default_dispatcher("outline", tmp_path)
    assert "result" in result
    assert "command_hint" in result or result["result"] in ("success", "partial", "failure", "rate_limited")


def test_run_iteration_with_default_dispatcher_records_attempt(tmp_path):
    """default_dispatcher 사용 시에도 state 갱신 동작."""
    from scripts.autopilot.runner import run_iteration, default_dispatcher
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)

    result = run_iteration(tmp_path, dispatcher=default_dispatcher)
    assert result["status"] == "continue"
    saved = json.loads((tmp_path / "autopilot_state.json").read_text(encoding="utf-8"))
    assert len(saved["wake_ups"]) == 1
