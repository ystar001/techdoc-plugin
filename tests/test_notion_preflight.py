# techdoc-plugin/tests/test_notion_preflight.py
"""parent page 권한 사전 점검 회귀."""

from __future__ import annotations

import httpx


def test_check_notion_access_passes_on_200():
    from scripts.notion.client import NotionClient
    from scripts.notion.preflight import check_notion_access

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"object": "page", "id": "abc"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    ok, reason = check_notion_access(client, "abc")
    assert ok is True


def test_check_notion_access_fails_on_404():
    """page 미존재 또는 integration이 page에 추가되지 않음."""
    from scripts.notion.client import NotionClient
    from scripts.notion.preflight import check_notion_access

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"object": "error", "code": "object_not_found"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    ok, reason = check_notion_access(client, "missing-id")
    assert ok is False
    assert "integration" in reason
    assert "Add connections" in reason


def test_check_notion_access_fails_on_401():
    """invalid token."""
    from scripts.notion.client import NotionClient
    from scripts.notion.preflight import check_notion_access

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"object": "error", "code": "unauthorized"})

    client = NotionClient(token="bad", transport=httpx.MockTransport(handler))
    ok, reason = check_notion_access(client, "x")
    assert ok is False
    assert "401" in reason or "unauthorized" in reason.lower()
