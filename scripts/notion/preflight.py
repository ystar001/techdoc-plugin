# techdoc-plugin/scripts/notion/preflight.py
"""Notion API 권한·접근 사전 점검 (v1.2.0).

`/techdoc-export-notion` 실행 직후, 실제 API 호출을 시작하기 전에
parent page 접근권을 확인해 권한 부재 시 명확한 안내로 abort.

LLM 호출 0회 — 완전 결정론적.
"""

from __future__ import annotations

from .client import NotionAPIError


def check_notion_access(client, parent_page_id: str) -> tuple[bool, str]:
    """parent_page_id를 GET해 권한 확인.

    Returns (ok, reason).
    - 200 OK → ok=True, reason="OK"
    - 401 → ok=False, reason="401 unauthorized: NOTION_TOKEN 유효성 확인"
    - 404 → ok=False, reason contains "integration" and "Add connections"
    - 그 외 → ok=False, reason=에러 메시지
    """
    try:
        client.get_page(parent_page_id)
        return True, "OK"
    except NotionAPIError as e:
        if e.status_code == 401:
            return False, f"401 unauthorized: NOTION_TOKEN 유효성 확인. {e.body[:200]}"
        if e.status_code == 404:
            return False, (
                f"404 object_not_found: parent page에 integration이 추가되지 않음. "
                f"Notion에서 '...' 메뉴 → 'Add connections'에서 integration 등록 필요. "
                f"page_id={parent_page_id}"
            )
        return False, f"{e.status_code}: {e.body[:200]}"
