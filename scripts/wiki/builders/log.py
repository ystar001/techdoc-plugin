"""log.md 빌더 — append-only 이력. 같은 날짜·보고서 중복 방지."""

from __future__ import annotations

import re

from scripts.wiki.markers import (
    AUTO_END,
    AUTO_START,
    extract_ai_region,
    has_markers,
    replace_ai_region,
)


def _format_entry(date: str, report_title: str, stats: dict) -> str:
    s = stats
    return (
        f"## [{date}] {report_title}\n"
        f"- 신규: {s.get('new_pages', 0)} / 갱신: {s.get('updated_pages', 0)} "
        f"/ 충돌: {s.get('conflicts', 0)}\n"
    )


def append_log(existing_log: str | None, date: str, report_title: str, stats: dict) -> str:
    new_entry = _format_entry(date, report_title, stats)
    if existing_log is None or not existing_log.strip():
        ai_body = f"# Log\n\n{new_entry}"
        return replace_ai_region("# Log\n", ai_body)

    # 기존 동일 헤더가 있으면 그 항목을 새 entry로 치환
    pattern = re.compile(
        rf"^## \[{re.escape(date)}\] {re.escape(report_title)}\n[^#]*",
        re.MULTILINE,
    )
    if pattern.search(existing_log):
        return pattern.sub(new_entry, existing_log, count=1)

    # 기존 마커 영역 안에 항목 추가
    if has_markers(existing_log):
        ai_region = extract_ai_region(existing_log) or ""
        if not ai_region.startswith("# Log"):
            ai_region = f"# Log\n\n{ai_region}"
        new_ai = ai_region.rstrip() + "\n\n" + new_entry
        return replace_ai_region(existing_log, new_ai)

    return existing_log.rstrip() + "\n\n" + new_entry
