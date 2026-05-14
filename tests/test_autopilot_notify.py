"""Notify (file log + chat) 회귀."""

from __future__ import annotations


def test_append_log_writes_line(tmp_path):
    from scripts.autopilot.notify import append_log

    append_log(tmp_path, "test message")
    log = (tmp_path / "autopilot.log").read_text(encoding="utf-8")
    assert "test message" in log
    assert "[" in log  # timestamp prefix


def test_append_log_appends_multiple(tmp_path):
    from scripts.autopilot.notify import append_log

    append_log(tmp_path, "line 1")
    append_log(tmp_path, "line 2")
    log = (tmp_path / "autopilot.log").read_text(encoding="utf-8")
    assert "line 1" in log and "line 2" in log


def test_build_start_message():
    from scripts.autopilot.notify import build_start_message

    msg = build_start_message(title="My Report", num_expected_chunks=10, max_hours=4)
    assert "My Report" in msg
    assert "10" in msg
    assert "4" in msg


def test_build_complete_message():
    from scripts.autopilot.notify import build_complete_message

    state = {
        "title": "My Report",
        "stages": {"outline": "completed", "render": "completed"},
        "wake_ups": [
            {"chunk": "outline", "duration_s": 60, "quality_fail": 0, "quality_warn": 0},
            {"chunk": "render", "duration_s": 120, "quality_fail": 0, "quality_warn": 1},
        ],
        "started_at": "2026-05-13T10:00:00+00:00",
        "completed_at": "2026-05-13T11:30:00+00:00",
    }
    msg = build_complete_message(state)
    assert "My Report" in msg
    assert "완료" in msg


def test_build_halt_message():
    from scripts.autopilot.notify import build_halt_message

    state = {
        "title": "My Report",
        "halt_reason": "quality_fail",
        "stages": {"outline": "completed", "research_A": "completed"},
        "wake_ups": [{"chunk": "research_A"}],
    }
    msg = build_halt_message(state, log_path="/path/to/log")
    assert "HALT" in msg or "halt" in msg.lower()
    assert "quality_fail" in msg
    assert "/path/to/log" in msg
