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


# ---------------------------------------------------------------------------
# F9-i: deepdive command hint
# ---------------------------------------------------------------------------


def test_deepdive_command_hint_present():
    from scripts.autopilot.runner import CHUNK_TO_COMMAND_HINT

    assert "deepdive" in CHUNK_TO_COMMAND_HINT
    assert "techdoc-deepdive" in CHUNK_TO_COMMAND_HINT["deepdive"]


# ---------------------------------------------------------------------------
# Task 10: autopilot.py CLI entry
# ---------------------------------------------------------------------------


def test_main_init_creates_state_file(tmp_path, monkeypatch):
    """autopilot main이 state 파일을 생성."""
    from scripts import autopilot
    import sys

    monkeypatch.chdir(tmp_path)
    argv_bak = list(sys.argv)
    try:
        sys.argv = [
            "autopilot", "Test Title",
            "--doc", str(tmp_path),
            "--print-loop-prompt",  # 실제 /loop 진입 안 함
        ]
        rc = autopilot.main()
    finally:
        sys.argv = argv_bak

    assert rc == 0
    state_path = tmp_path / "autopilot_state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["title"] == "Test Title"


def test_main_aborts_if_lock_exists(tmp_path, monkeypatch):
    """autopilot.lock 존재 시 abort."""
    from scripts import autopilot
    import sys

    (tmp_path / "autopilot.lock").write_text("", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    argv_bak = list(sys.argv)
    try:
        sys.argv = ["autopilot", "Test", "--doc", str(tmp_path), "--print-loop-prompt"]
        rc = autopilot.main()
    finally:
        sys.argv = argv_bak

    assert rc != 0  # lock 충돌로 종료


# ---------------------------------------------------------------------------
# Task 11: autopilot_step.py — 단일 step JSON 출력
# ---------------------------------------------------------------------------


def test_autopilot_step_prints_json(tmp_path, monkeypatch, capsys):
    """autopilot_step.main()이 결과를 JSON으로 stdout에 출력."""
    from scripts import autopilot_step
    from scripts.autopilot.state import init_state, save_state
    import sys

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)

    argv_bak = list(sys.argv)
    try:
        sys.argv = ["autopilot_step", "--doc", str(tmp_path)]
        rc = autopilot_step.main()
    finally:
        sys.argv = argv_bak

    out = capsys.readouterr().out.strip()
    parsed = json.loads(out)
    assert parsed["status"] in ("done", "halt", "continue")


def test_autopilot_step_halt_outputs_reason(tmp_path, monkeypatch, capsys):
    """halt 시 reason 포함."""
    from scripts import autopilot_step
    from scripts.autopilot.state import init_state, save_state
    import sys

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)
    (tmp_path / "autopilot.stop").write_text("", encoding="utf-8")

    argv_bak = list(sys.argv)
    try:
        sys.argv = ["autopilot_step", "--doc", str(tmp_path)]
        autopilot_step.main()
    finally:
        sys.argv = argv_bak

    out = capsys.readouterr().out.strip()
    parsed = json.loads(out)
    assert parsed["status"] == "halt"
    assert parsed["reason"] == "manual_stop"


# ---------------------------------------------------------------------------
# C1: lock cleanup regression tests
# ---------------------------------------------------------------------------


def test_run_iteration_deletes_lock_on_done(tmp_path):
    """모든 stage completed → done 반환 시 autopilot.lock 삭제."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    for k in state["stages"]:
        state["stages"][k] = "completed"
    save_state(tmp_path, state)
    (tmp_path / "autopilot.lock").write_text("", encoding="utf-8")

    result = run_iteration(tmp_path, dispatcher=None)
    assert result["status"] == "done"
    assert not (tmp_path / "autopilot.lock").exists()


def test_run_iteration_deletes_lock_on_halt(tmp_path):
    """manual_stop halt 시 autopilot.lock 삭제."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)
    (tmp_path / "autopilot.lock").write_text("", encoding="utf-8")
    (tmp_path / "autopilot.stop").write_text("", encoding="utf-8")

    result = run_iteration(tmp_path, dispatcher=None)
    assert result["status"] == "halt"
    assert not (tmp_path / "autopilot.lock").exists()


# ---------------------------------------------------------------------------
# C2: consecutive_card_failures regression tests
# ---------------------------------------------------------------------------


def test_run_iteration_increments_card_failures_on_failure(tmp_path):
    """dispatcher failure → consecutive_card_failures 1 증가."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    save_state(tmp_path, state)

    def failing_dispatcher(chunk_id, output_dir):
        return {"result": "failure", "duration_s": 5, "quality_fail": 0, "quality_warn": 0}

    run_iteration(tmp_path, dispatcher=failing_dispatcher)
    saved = json.loads((tmp_path / "autopilot_state.json").read_text(encoding="utf-8"))
    assert saved["consecutive_card_failures"] == 1


def test_run_iteration_resets_card_failures_on_success(tmp_path):
    """dispatcher success → consecutive_card_failures 0 초기화."""
    from scripts.autopilot.runner import run_iteration
    from scripts.autopilot.state import init_state, save_state

    state = init_state(tmp_path, title="T", config={}, num_section_groups=2)
    state["consecutive_card_failures"] = 3  # 과거 실패 있음
    save_state(tmp_path, state)

    def ok_dispatcher(chunk_id, output_dir):
        return {"result": "success", "duration_s": 5, "quality_fail": 0, "quality_warn": 0}

    run_iteration(tmp_path, dispatcher=ok_dispatcher)
    saved = json.loads((tmp_path / "autopilot_state.json").read_text(encoding="utf-8"))
    assert saved["consecutive_card_failures"] == 0


# ---------------------------------------------------------------------------
# I1: NOTION_TOKEN validation regression tests
# ---------------------------------------------------------------------------


def test_main_aborts_when_push_notion_without_token(tmp_path, monkeypatch):
    """--push-notion 인자에 NOTION_TOKEN 미설정 시 abort."""
    from scripts.autopilot import main
    import sys

    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    argv_bak = list(sys.argv)
    try:
        sys.argv = [
            "autopilot", "Test",
            "--doc", str(tmp_path),
            "--push-notion", "abc123",
            "--print-loop-prompt",
        ]
        rc = main()
    finally:
        sys.argv = argv_bak
    assert rc == 1


def test_main_proceeds_when_push_notion_with_token(tmp_path, monkeypatch):
    """--push-notion + NOTION_TOKEN 설정 시 정상 진행."""
    from scripts.autopilot import main
    import sys

    monkeypatch.setenv("NOTION_TOKEN", "test_token")
    argv_bak = list(sys.argv)
    try:
        sys.argv = [
            "autopilot", "Test",
            "--doc", str(tmp_path),
            "--push-notion", "abc123",
            "--print-loop-prompt",
        ]
        rc = main()
    finally:
        sys.argv = argv_bak
    assert rc == 0
