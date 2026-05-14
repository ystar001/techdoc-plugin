"""Autopilot의 단일 step 실행 — /loop prompt가 매 wake-up마다 호출.

stdout에 JSON 결과 출력: {"status": ..., "next_wake_up_seconds"?: int, "reason"?: str}.

호출 형식: python -m scripts.autopilot_step --doc <output_dir>.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.autopilot.runner import default_dispatcher, run_iteration


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="autopilot_step")
    ap.add_argument("--doc", required=True, help="output 디렉토리")
    args = ap.parse_args(argv)

    result = run_iteration(Path(args.doc), dispatcher=default_dispatcher)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
