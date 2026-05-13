"""Plan C (F6) — Write 권한 사전 점검.

researcher subagent가 KeyRef·research_round_*.json을 디스크에 쓰기 전에,
메인 세션이 target 디렉토리에 실제 쓸 수 있는지 검증한다.

2026-04-29 cat13/14 사고 — researcher가 Write 권한 거부 후 메인 세션이
generator로 우회하여 `KeyRef_overlap_*` 중복 산출을 만들었던 사고의 재발 방지.
"""

from __future__ import annotations

import uuid
from pathlib import Path


def check_write_permission(target_dir: Path) -> tuple[bool, str]:
    """target_dir에 임시 파일 생성·삭제로 Write 권한 검증.

    Returns (ok, reason).
    - target_dir이 없으면 생성 시도.
    - 임시 파일 생성·정리 모두 성공해야 ok=True.
    - 실패 시 reason에 OS 에러 메시지를 담아 반환.
    """
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"디렉토리 생성 실패: {e}"

    probe = target_dir / f".techdoc-preflight-{uuid.uuid4().hex}"
    try:
        probe.write_bytes(b"preflight")
    except OSError as e:
        return False, f"파일 쓰기 실패: {e}"

    try:
        probe.unlink()
    except OSError as e:
        return False, f"파일 삭제 실패: {e}"

    return True, "OK"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.preflight <target_dir>", file=sys.stderr)
        sys.exit(2)
    ok, reason = check_write_permission(Path(sys.argv[1]))
    print(reason)
    sys.exit(0 if ok else 1)
