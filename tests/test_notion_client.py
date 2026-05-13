"""Notion client tests (Phase 1)."""

from __future__ import annotations

import httpx
import pytest


def test_notion_client_sets_auth_header():
    from scripts.notion.client import NotionClient

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization", "")
        captured["version"] = request.headers.get("Notion-Version", "")
        return httpx.Response(200, json={"object": "page", "id": "abc"})

    client = NotionClient(token="secret_xyz", transport=httpx.MockTransport(handler))
    client.get_page("abc-123")

    assert captured["auth"] == "Bearer secret_xyz"
    assert captured["version"]  # 비어있지 않음 (e.g., "2022-06-28")


def test_notion_client_get_page_returns_json():
    from scripts.notion.client import NotionClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"object": "page", "id": "xyz"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    result = client.get_page("xyz")
    assert result["id"] == "xyz"


def test_notion_client_create_page_posts_to_pages_endpoint():
    from scripts.notion.client import NotionClient

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(200, json={"id": "new-page"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    client.create_page(parent_page_id="p1", properties={"title": [{"text": {"content": "T"}}]}, children=[])

    assert captured["method"] == "POST"
    assert "/v1/pages" in captured["url"]


def test_notion_client_raises_on_4xx():
    from scripts.notion.client import NotionClient, NotionAPIError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"object": "error", "code": "unauthorized"})

    client = NotionClient(token="bad", transport=httpx.MockTransport(handler))
    with pytest.raises(NotionAPIError) as exc:
        client.get_page("x")
    assert exc.value.status_code == 401


import time as _time_mod


def test_notion_client_respects_rate_limit(monkeypatch):
    """3 req/sec 제한 — 4번째 호출까지 1초 이상 걸려야."""
    from scripts.notion.client import NotionClient

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "x"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler), rate_limit_per_sec=3)
    for _ in range(4):
        client.get_page("x")

    # 최소 첫 호출 후 3번은 간격 대기 (1/3초씩)
    assert len([s for s in sleeps if s > 0]) >= 2
    # 각 대기는 0.33초 근처
    for s in sleeps:
        if s > 0:
            assert 0 < s <= 0.4


def test_notion_client_rate_limit_can_be_disabled(monkeypatch):
    """rate_limit_per_sec를 매우 큰 값으로 두면 sleep 거의 없음."""
    from scripts.notion.client import NotionClient

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "x"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler), rate_limit_per_sec=10000)
    for _ in range(5):
        client.get_page("x")
    assert len([s for s in sleeps if s > 0.001]) == 0


def test_notion_client_retries_on_429_with_retry_after(monkeypatch):
    """429 응답 시 Retry-After 헤더 존중 후 재시도."""
    from scripts.notion.client import NotionClient

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={})
        return httpx.Response(200, json={"id": "ok"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    result = client.get_page("x")
    assert result["id"] == "ok"
    assert calls["n"] == 2
    assert any(s >= 2.0 for s in sleeps), f"Retry-After 미준수: {sleeps}"


def test_notion_client_retries_on_500_with_backoff(monkeypatch):
    """5xx 응답 시 exponential backoff (1s, 2s, 4s)."""
    from scripts.notion.client import NotionClient

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"id": "recovered"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    result = client.get_page("x")
    assert result["id"] == "recovered"
    assert calls["n"] == 3
    # backoff 1초, 2초 sleep 검증
    backoff_sleeps = [s for s in sleeps if s >= 1.0]
    assert len(backoff_sleeps) >= 2


def test_notion_client_gives_up_after_max_retries(monkeypatch):
    """5xx가 계속되면 최대 3회 재시도 후 NotionAPIError."""
    from scripts.notion.client import NotionClient, NotionAPIError

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="persistent failure")

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    with pytest.raises(NotionAPIError) as exc:
        client.get_page("x")
    assert exc.value.status_code == 500


def test_notion_client_429_exhaustion_raises_status_429(monkeypatch):
    """429가 계속되면 마지막 NotionAPIError의 status_code가 429."""
    from scripts.notion.client import NotionClient, NotionAPIError

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "1"}, text="rate limited")

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    with pytest.raises(NotionAPIError) as exc:
        client.get_page("x")
    assert exc.value.status_code == 429


def test_notion_client_retry_after_date_string_uses_fallback(monkeypatch):
    """Retry-After가 HTTP-date 형식이면 fallback (60초 default)으로 대기."""
    from scripts.notion.client import NotionClient

    sleeps: list[float] = []
    monkeypatch.setattr(_time_mod, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "Tue, 03 Jul 2026 12:00:00 GMT"},
                text="rate limited",
            )
        return httpx.Response(200, json={"id": "ok"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    result = client.get_page("x")
    assert result["id"] == "ok"
    # fallback 60s가 sleep에 등장
    assert any(s >= 60.0 for s in sleeps)
