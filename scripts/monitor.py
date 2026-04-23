"""진행 상황 모니터링 — writer_state.json 기반 카드·별첨 단위 실시간 이벤트.

두 가지 모드:
  - tail: writer_state.json의 events 리스트를 폴링하며 새 이벤트 표시
  - snapshot: 현재 전체 진행률 테이블 표시

사용법:
    python -m scripts.monitor ./output/             # tail 모드 (기본)
    python -m scripts.monitor ./output/ --snapshot  # 현재 상태만
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


def _format_section_progress(state: dict) -> str:
    """섹션별 진행률을 텍스트 표로 포맷."""
    section_states = state.get("section_states", {}) or {}
    lines = []
    lines.append("─" * 70)
    lines.append(f"{'Section':<10}{'Cards':<18}{'Status':<20}{'Chars':<12}")
    lines.append("─" * 70)

    for sid, st in sorted(section_states.items(), key=lambda x: [int(p) if p.isdigit() else p for p in x[0].split(".")]):
        cards = st.get("cards", []) or []
        total = len(cards)
        done = sum(1 for c in cards if c.get("status") == "completed")
        writing = sum(1 for c in cards if c.get("status") == "writing")
        failed = sum(1 for c in cards if c.get("status") == "failed")

        if failed > 0:
            status = f"FAIL {failed}/{total}"
        elif done == total and total > 0:
            status = f"OK 완료 {done}/{total}"
        elif writing > 0:
            status = f"WRITING {done}/{total}"
        else:
            status = f"대기 {done}/{total}"

        total_chars = sum(c.get("chars", 0) for c in cards)
        lines.append(f"{sid:<10}{f'{done}/{total}':<18}{status:<20}{total_chars:<12}")

    appendices = state.get("appendices", []) or []
    if appendices:
        lines.append("─" * 70)
        lines.append(f"{'Appendix':<10}{'Blocks':<18}{'Status':<20}{'Chars':<12}")
        lines.append("─" * 70)
        for a in appendices:
            blocks = f"{a.get('blocks_completed', 0)}/{a.get('blocks_total', 0)}"
            status = a.get("status", "pending")
            chars = a.get("chars", 0)
            lines.append(f"{a.get('id', '?'):<10}{blocks:<18}{status:<20}{chars:<12}")

    lines.append("─" * 70)
    return "\n".join(lines)


def show_snapshot(state_path: Path) -> int:
    if not state_path.exists():
        print(f"writer_state.json not found: {state_path}", file=sys.stderr)
        return 1

    state = json.loads(state_path.read_text(encoding="utf-8"))
    started = state.get("pipeline_started_at", "?")
    updated = state.get("pipeline_updated_at", "?")
    print(f"Pipeline started: {started}")
    print(f"Last updated:     {updated}")
    print()
    print(_format_section_progress(state))

    events = state.get("events", []) or []
    if events:
        print()
        print(f"최근 이벤트 ({min(10, len(events))}건):")
        for e in events[-10:]:
            ts = e.get("ts", "?")
            if "T" in str(ts):
                ts = str(ts).split("T", 1)[1][:8]
            card_id = e.get("card") or e.get("appendix") or e.get("section", "?")
            line = f"  [{ts}] {card_id:<12} {e.get('state', ''):<12} {e.get('chars', '')}"
            print(line)

    return 0


def tail_events(state_path: Path, poll_s: float = 2.0) -> int:
    print(f"Monitoring: {state_path}")
    print("Ctrl+C to stop")
    print("=" * 70)
    last_event_count = 0

    try:
        while True:
            if state_path.exists():
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    time.sleep(poll_s)
                    continue

                events = state.get("events", []) or []
                new_events = events[last_event_count:]
                for e in new_events:
                    ts = e.get("ts", datetime.now().isoformat())
                    if "T" in str(ts):
                        ts = str(ts).split("T", 1)[1][:8]
                    card_id = e.get("card") or e.get("appendix") or e.get("section", "?")
                    state_str = e.get("state", "")
                    chars = e.get("chars", "")
                    print(f"[{ts}] {card_id:<12} {state_str:<12} {chars}")

                last_event_count = len(events)

            time.sleep(poll_s)
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="TechDoc progress monitor")
    ap.add_argument("output_dir", nargs="?", default="./output", help="output directory")
    ap.add_argument("--snapshot", action="store_true", help="현재 상태만 표시 (no polling)")
    ap.add_argument("--poll", type=float, default=2.0, help="tail 폴링 간격 (초)")
    args = ap.parse_args()

    state_path = Path(args.output_dir) / "writer_state.json"
    if args.snapshot:
        return show_snapshot(state_path)
    return tail_events(state_path, args.poll)


if __name__ == "__main__":
    sys.exit(main())
