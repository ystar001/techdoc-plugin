"""단일 wake-up 흐름 (v1.3.0).

run_iteration(output_dir, dispatcher) → dict:
  {"status": "done"} 또는
  {"status": "halt", "reason": "..."} 또는
  {"status": "continue", "next_wake_up_seconds": int}

dispatcher 인터페이스: (chunk_id, output_dir) -> {"result", "duration_s", "quality_fail", "quality_warn"}.
result ∈ {"success", "failure", "partial", "rate_limited"}.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

__all__ = ["run_iteration", "default_dispatcher", "CHUNK_TO_COMMAND_HINT"]
from pathlib import Path
from typing import Callable

from scripts.autopilot import chunks, notify, state as state_module, triggers


def run_iteration(
    output_dir: Path,
    dispatcher: Callable[[str, Path], dict] | None,
) -> dict:
    """단일 wake-up 처리. 트리거→다음 chunk 결정→dispatcher 호출→state 갱신."""
    output_dir = Path(output_dir)
    state = state_module.load_state(output_dir)

    # Phase 1: pre-flight triggers (manual_stop·wall_clock·state_corruption·card_failures)
    pre_trigger = triggers.evaluate_all(state, output_dir, quality_report=None)
    if pre_trigger:
        state_module.mark_halted(state, pre_trigger)
        state_module.save_state(output_dir, state)
        notify.append_log(output_dir, f"HALT pre-flight: {pre_trigger}")
        return {"status": "halt", "reason": pre_trigger}

    # Phase 2: 다음 chunk 선택
    next_chunk = chunks.pick_next_chunk(state)
    if next_chunk is None:
        state_module.mark_completed(state)
        state_module.save_state(output_dir, state)
        notify.append_log(output_dir, "complete")
        return {"status": "done"}

    # Phase 3: dispatcher 호출
    if dispatcher is None:
        notify.append_log(output_dir, f"NO_DISPATCHER chunk={next_chunk} (test mode)")
        return {"status": "continue", "next_wake_up_seconds": 60}

    state_module.update_stage(state, next_chunk, "in_progress")
    state_module.save_state(output_dir, state)
    notify.append_log(output_dir, f"start chunk={next_chunk}")

    start = time.monotonic()
    try:
        dispatch_result = dispatcher(next_chunk, output_dir)
    except Exception as e:  # noqa: BLE001
        notify.append_log(output_dir, f"DISPATCHER_ERROR chunk={next_chunk} err={e}")
        state_module.update_stage(state, next_chunk, "failed")
        state_module.save_state(output_dir, state)
        return {"status": "continue", "next_wake_up_seconds": 60}

    duration = dispatch_result.get("duration_s", int(time.monotonic() - start))
    result_status = dispatch_result.get("result", "success")
    q_fail = dispatch_result.get("quality_fail", 0)
    q_warn = dispatch_result.get("quality_warn", 0)

    # state 갱신
    if result_status == "success":
        state_module.update_stage(state, next_chunk, "completed")
    elif result_status == "failure":
        state_module.update_stage(state, next_chunk, "failed")
    elif result_status == "partial":
        state_module.update_stage(state, next_chunk, "completed")  # 부분 성공도 진행
    elif result_status == "rate_limited":
        state_module.update_stage(state, next_chunk, "pending")  # 다음 wake-up 재시도

    state_module.append_wake_up(state, {
        "ts": datetime.now(timezone.utc).isoformat(),
        "chunk": next_chunk,
        "duration_s": duration,
        "result": result_status,
        "quality_fail": q_fail,
        "quality_warn": q_warn,
    })

    # Phase 4: post-dispatch quality 트리거 (quality_fail·quality_warn_exceeded)
    quality_report = {"total_fail": q_fail, "total_warning": q_warn}
    post_trigger = triggers.check_quality_fail(
        quality_report,
        state.get("config", {}).get("max_warnings", 10),
    )
    state_module.save_state(output_dir, state)
    notify.append_log(
        output_dir,
        f"complete chunk={next_chunk} duration={duration}s result={result_status} "
        f"quality(fail={q_fail},warn={q_warn})",
    )

    if post_trigger:
        state_module.mark_halted(state, post_trigger)
        state_module.save_state(output_dir, state)
        notify.append_log(output_dir, f"HALT post-quality: {post_trigger}")
        return {"status": "halt", "reason": post_trigger}

    # Phase 5: 다음 wake-up 시점
    if result_status == "rate_limited":
        next_wake = 1200  # 20분 대기 (quota refresh)
    else:
        next_wake = 60  # 즉시 (cache window 안)

    return {"status": "continue", "next_wake_up_seconds": next_wake}


# ---------------------------------------------------------------------------
# Chunk → 슬래시 명령 매핑 (메인 loop prompt가 실행)
# ---------------------------------------------------------------------------

CHUNK_TO_COMMAND_HINT: dict[str, str] = {
    "outline": "/techdoc-outline ...",
    "research_A": "/techdoc-research --group A ...",
    "research_B": "/techdoc-research --group B ...",
    "research_C": "/techdoc-research --group C ...",
    "merge_research": "python -m scripts.merge_research + scripts.build_reflist",
    "write_A": "/techdoc-write --group A ...",
    "write_B": "/techdoc-write --group B ...",
    "write_C": "/techdoc-write --group C ...",
    "review": "/techdoc-review ...",
    "render": "/techdoc-render ...",
}


def default_dispatcher(chunk_id: str, output_dir: Path) -> dict:
    """기본 dispatcher — MVP에서는 hint 반환만 (실제 LLM 작업은 loop prompt가 처리).

    Future v1.3.x: 메인 loop prompt가 이 hint를 받아 슬래시 명령 invoke + result 기록.
    """
    hint = CHUNK_TO_COMMAND_HINT.get(chunk_id, "")
    return {
        "result": "success",  # MVP — 실제 실행 결과는 loop prompt에서 갱신
        "duration_s": 0,
        "quality_fail": 0,
        "quality_warn": 0,
        "command_hint": hint,
    }
