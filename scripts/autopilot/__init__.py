"""TechDoc Autopilot (v1.3.0) — self-paced 보고서 자동 생성.

CLI entry:
    python -m scripts.autopilot "<title>" --doc <output_dir> [옵션...]
        → state 초기화 + /loop prompt를 stdout에 출력

옵션:
    --max-wall-clock 4h | --max-warnings 10 | --notify anomalies_only|each-wake-up
    --push-notion <parent_page_id> | --export-wiki <vault>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scripts.autopilot import state as state_module

LOCK_FILENAME = "autopilot.lock"
LOOP_PROMPT_TEMPLATE = """techdoc autopilot loop iteration for output directory: {output_dir}

1. Run python -m scripts.autopilot_step --doc "{output_dir}"
2. Parse stdout JSON: {{"status": "done"|"halt"|"continue", "next_wake_up_seconds": int, "reason": str}}
3. If "done": stop loop (no ScheduleWakeup). Emit chat message: see autopilot.log tail.
4. If "halt": stop loop. Emit chat message with reason.
5. If "continue": ScheduleWakeup with delaySeconds=next_wake_up_seconds, reason="techdoc autopilot continuation"
"""


def _parse_duration_to_seconds(s: str) -> int:
    """'4h'·'30m'·'90' (초) 모두 허용."""
    s = s.strip().lower()
    m = re.match(r"^(\d+)(h|m|s)?$", s)
    if not m:
        raise ValueError(f"invalid duration: {s}")
    n = int(m.group(1))
    unit = m.group(2) or "s"
    return n * {"h": 3600, "m": 60, "s": 1}[unit]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="autopilot")
    ap.add_argument("title", help="보고서 제목")
    ap.add_argument("--doc", default="./output", help="output 디렉토리")
    ap.add_argument("--max-wall-clock", default="4h", help="최대 wall-clock (4h·240m·14400)")
    ap.add_argument("--max-warnings", type=int, default=10)
    ap.add_argument("--notify", choices=["anomalies_only", "each-wake-up"], default="anomalies_only")
    ap.add_argument("--push-notion", default=None, help="Notion parent page ID")
    ap.add_argument("--export-wiki", default=None, help="Wiki vault 디렉토리")
    ap.add_argument("--num-section-groups", type=int, default=3, choices=[1, 2, 3])
    ap.add_argument(
        "--print-loop-prompt",
        action="store_true",
        help="state 초기화 + /loop prompt 출력 후 종료 (실제 loop 진입 안 함)",
    )
    args = ap.parse_args(argv)

    output_dir = Path(args.doc)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lock 점검
    lock_path = output_dir / LOCK_FILENAME
    if lock_path.exists():
        print(
            f"오류: autopilot이 이미 실행 중입니다 (lock: {lock_path}).",
            file=sys.stderr,
        )
        print(
            "다른 세션에서 실행 중이거나 비정상 종료된 흔적입니다. "
            f"문제 없으면 {lock_path}을 삭제 후 재실행하세요.",
            file=sys.stderr,
        )
        return 1

    # State 초기화
    config = {
        "max_wall_clock_seconds": _parse_duration_to_seconds(args.max_wall_clock),
        "max_warnings": args.max_warnings,
        "max_consecutive_card_failures": 5,
        "notify": args.notify,
        "push_notion_parent_page": args.push_notion,
        "export_wiki_vault": args.export_wiki,
    }
    state = state_module.init_state(
        output_dir,
        title=args.title,
        config=config,
        num_section_groups=args.num_section_groups,
    )
    state_module.save_state(output_dir, state)

    # Lock 생성
    lock_path.write_text("", encoding="utf-8")

    # /loop prompt 출력 (호출자가 loop 스킬에 전달)
    prompt = LOOP_PROMPT_TEMPLATE.format(output_dir=output_dir.resolve())
    print(prompt)

    if args.print_loop_prompt:
        return 0

    # 실제 /loop 진입은 슬래시 명령(commands/techdoc-autopilot.md)이 처리
    return 0


if __name__ == "__main__":
    sys.exit(main())
