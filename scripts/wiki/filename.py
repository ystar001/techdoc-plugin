"""카드 name → 옵시디언 안전 파일명 정규화."""

from __future__ import annotations

import re

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_name(name: str) -> str:
    """파일명에 부적합한 문자(Windows·옵시디언 공통 금지)를 _로 치환.

    한글·공백·영문은 보존. 빈 문자열은 'unnamed'로 폴백.
    """
    if not name or not name.strip():
        return "unnamed"
    cleaned = _INVALID_CHARS.sub("_", name.strip())
    return cleaned
