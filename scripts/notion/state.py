# techdoc-plugin/scripts/notion/state.py
"""notion_state.json 읽기·쓰기 + hash 비교 + delta detection (v1.2.0).

v2 호환 디자인 원칙:
- 원칙 #1: last_edited_time 보존 (v1.3.x에서 conflict 감지에 사용)
- 원칙 #4: schema_version 명시 (v1.3.x·v2.0에서 자동 migration)

LLM 호출 0회 — 완전 결정론적.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STATE_SCHEMA_VERSION = "0.1.0"
STATE_FILENAME = "notion_state.json"


def _empty_state() -> dict:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "parent_page_id": None,
        "report_page_id": None,
        "keyref_db_id": None,
        "report_title": None,
        "sections": {},
        "appendices": {},
        "keyrefs": {},
        "last_pushed_at": None,
    }


def load_state(output_dir: Path) -> dict:
    """notion_state.json 로드. 파일 없으면 빈 state 반환."""
    path = Path(output_dir) / STATE_FILENAME
    if not path.exists():
        return _empty_state()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()


def save_state(output_dir: Path, state: dict) -> None:
    """state를 notion_state.json에 저장."""
    path = Path(output_dir) / STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )


def compute_content_hash(content: Any) -> str:
    """결정론적 SHA-256 hash.

    dict/list는 sort_keys=True JSON serialization 후 hash.
    그 외는 str()로 변환 후 hash.
    """
    if isinstance(content, (dict, list)):
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    else:
        serialized = str(content)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def detect_section_changes(
    old_state: dict, new_sections: dict[str, Any]
) -> dict[str, list[str]]:
    """이전 state와 현재 섹션 dict 비교해 변경 분류.

    new_sections: {section_id: content (str|dict)}
    Returns: {"new": [...], "modified": [...], "unchanged": [...], "stale": [...]}
    """
    old_sections = old_state.get("sections", {})
    new_hashes = {sid: compute_content_hash(content) for sid, content in new_sections.items()}

    new_ids: list[str] = []
    modified_ids: list[str] = []
    unchanged_ids: list[str] = []
    for sid, h in new_hashes.items():
        entry = old_sections.get(sid)
        if not entry:
            new_ids.append(sid)
        elif entry.get("content_hash") != h:
            modified_ids.append(sid)
        else:
            unchanged_ids.append(sid)
    stale_ids = [sid for sid in old_sections if sid not in new_sections]

    return {
        "new": new_ids,
        "modified": modified_ids,
        "unchanged": unchanged_ids,
        "stale": stale_ids,
    }
