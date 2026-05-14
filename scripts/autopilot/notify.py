"""파일 로그 + chat 메시지 빌드 (v1.3.0).

매 wake-up에 log.append. chat 메시지는 string으로 반환 — 호출자(runner/loop prompt)가
실제 chat 출력.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

LOG_FILENAME = "autopilot.log"


def append_log(output_dir: Path, message: str) -> None:
    """autopilot.log에 timestamp 접두사로 1줄 append."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}\n"
    log_path = output_dir / LOG_FILENAME
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def build_start_message(title: str, num_expected_chunks: int, max_hours: int) -> str:
    return (
        f"[techdoc-autopilot 시작] \"{title}\", "
        f"예상 ~{num_expected_chunks} wake-ups, 예산 max {max_hours}h"
    )


def build_complete_message(state: dict) -> str:
    title = state.get("title", "")
    wake_ups = state.get("wake_ups", [])
    total_fail = sum(w.get("quality_fail", 0) for w in wake_ups)
    total_warn = sum(w.get("quality_warn", 0) for w in wake_ups)

    duration = ""
    if state.get("started_at") and state.get("completed_at"):
        try:
            start = datetime.fromisoformat(state["started_at"])
            end = datetime.fromisoformat(state["completed_at"])
            elapsed = (end - start).total_seconds()
            duration = f"{int(elapsed // 3600)}h{int((elapsed % 3600) // 60)}m"
        except (ValueError, TypeError):
            duration = "?"

    return (
        f"[techdoc-autopilot 완료] \"{title}\", "
        f"실제 {duration}, chunks {len(wake_ups)}, "
        f"quality(fail={total_fail},warn={total_warn}), 출력: output/"
    )


def build_halt_message(state: dict, log_path: str) -> str:
    title = state.get("title", "")
    reason = state.get("halt_reason", "unknown")
    completed_chunks = sum(
        1 for s in state.get("stages", {}).values() if s == "completed"
    )
    total_chunks = len(state.get("stages", {}))
    last_chunk = "?"
    if state.get("wake_ups"):
        last_chunk = state["wake_ups"][-1].get("chunk", "?")

    return (
        f"[techdoc-autopilot HALT] \"{title}\" "
        f"reason={reason}, "
        f"completed_chunks={completed_chunks}/{total_chunks}, "
        f"last_chunk={last_chunk}, "
        f"log={log_path}"
    )
