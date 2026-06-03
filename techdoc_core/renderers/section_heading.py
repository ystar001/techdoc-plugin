"""self-model 섹션 키 → 한글 헤딩 매핑 (F12).

Plan G의 위치 기본 헤딩(constants.DEFAULT_SECTION_TITLES)을 재사용한다.
구 서술형 키(sec3_trends_*)도 위치(sec3)로 정규화해 매핑한다.
"""
from __future__ import annotations

import re

from techdoc_core.constants import DEFAULT_SECTION_TITLES

_SEC_PREFIX_RE = re.compile(r"^(sec[1-6])")


def section_key_to_heading(key: str, fallback: str = "") -> str:
    """섹션 키 → 한글 헤딩. 위치(sec1~6) 매핑 우선, 없으면 fallback 또는 키."""
    m = _SEC_PREFIX_RE.match(key)
    if m and m.group(1) in DEFAULT_SECTION_TITLES:
        return DEFAULT_SECTION_TITLES[m.group(1)]
    return fallback or key
