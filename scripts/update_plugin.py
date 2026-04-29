"""TechDoc Plugin 온라인 업데이트.

GitHub Releases (ystar001/techdoc-plugin)에서 최신 zip을 받아 plugin 디렉토리를 갱신.

사용법:
    python -m scripts.update_plugin            # 적용 (사용자 [y/N] 확인 후)
    python -m scripts.update_plugin --check    # 체크만
    python -m scripts.update_plugin --force    # 동일 버전이어도 강제 재설치
"""

from __future__ import annotations

import re


def _parse_version(v: str) -> tuple[int, int, int]:
    """semver 문자열을 (major, minor, patch) 정수 튜플로 파싱.

    'v1.1.0', '1.1.0' 모두 처리. pre-release suffix는 무시.
    """
    s = v.strip().lstrip("v")
    s = re.split(r"[-+]", s, maxsplit=1)[0]
    parts = s.split(".")
    if len(parts) != 3:
        raise ValueError(f"invalid semver: {v!r}")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def is_newer(latest: str, current: str) -> bool:
    """latest 가 current 보다 더 새 버전이면 True."""
    return _parse_version(latest) > _parse_version(current)
