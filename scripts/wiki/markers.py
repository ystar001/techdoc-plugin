"""auto-start/end 마커 파싱·치환.

사용자가 옵시디언에서 페이지에 직접 메모를 추가해도 보존되도록,
AI가 관리하는 영역과 사용자 영역을 마커로 구분한다.
"""

from __future__ import annotations

import re

AUTO_START = "<!-- techdoc:auto-start -->"
AUTO_END = "<!-- techdoc:auto-end -->"

_MARKER_PATTERN = re.compile(
    re.escape(AUTO_START) + r"\n?(.*?)\n?" + re.escape(AUTO_END),
    re.DOTALL,
)


def has_markers(page: str) -> bool:
    """페이지에 마커가 있는가."""
    return AUTO_START in page and AUTO_END in page


def extract_ai_region(page: str) -> str | None:
    """마커 사이의 AI 영역 텍스트 반환. 없으면 None."""
    m = _MARKER_PATTERN.search(page)
    return m.group(1).strip() if m else None


def replace_ai_region(page: str, new_ai_content: str) -> str:
    """마커 사이 AI 영역을 새 내용으로 치환. 외부 영역은 보존.

    마커가 없으면 페이지 끝에 마커 블록을 추가하고 기존 내용을 100% 보존.
    """
    new_block = f"{AUTO_START}\n{new_ai_content}\n{AUTO_END}"
    if has_markers(page):
        return _MARKER_PATTERN.sub(new_block, page, count=1)
    if page and not page.endswith("\n"):
        page += "\n"
    return f"{page}\n{new_block}\n" if page else f"{new_block}\n"
