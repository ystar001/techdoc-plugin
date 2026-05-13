"""Notion REST API 래퍼 (v1.2.0).

LLM 호출 0회. httpx 기반. rate limit + 재시도 내장.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


@dataclass
class NotionAPIError(Exception):
    status_code: int
    body: str

    def __str__(self) -> str:
        return f"Notion API {self.status_code}: {self.body[:200]}"


class NotionClient:
    """Notion REST API 클라이언트.

    transport: 테스트에서 httpx.MockTransport 주입용. 실제 호출 시 None.
    rate_limit_per_sec: 초당 호출 횟수 상한 (기본 3, Notion 공식 제약).
    """

    def __init__(
        self,
        token: str,
        transport: httpx.BaseTransport | None = None,
        rate_limit_per_sec: int = 3,
        timeout: float = 30.0,
    ):
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout,
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )
        self._min_interval = 1.0 / max(rate_limit_per_sec, 1)
        self._last_call_at = 0.0

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call_at
        sleep_for = self._min_interval - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last_call_at = time.monotonic()

    def _request(self, method: str, path: str, max_retries: int = 3, **kwargs) -> dict:
        backoff = 1.0
        last_error: NotionAPIError | None = None
        for attempt in range(max_retries):
            self._wait_for_rate_limit()
            resp = self._client.request(method, path, **kwargs)
            if 200 <= resp.status_code < 300:
                return resp.json()
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue
            if 500 <= resp.status_code < 600:
                last_error = NotionAPIError(status_code=resp.status_code, body=resp.text)
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise last_error
            # 4xx (429 제외) — 즉시 실패
            raise NotionAPIError(status_code=resp.status_code, body=resp.text)
        if last_error:
            raise last_error
        raise NotionAPIError(status_code=0, body="exhausted retries")

    # ── Public methods ──

    def get_page(self, page_id: str) -> dict:
        return self._request("GET", f"/pages/{page_id}")

    def create_page(
        self,
        parent_page_id: str | None = None,
        parent_database_id: str | None = None,
        properties: dict | None = None,
        children: list | None = None,
    ) -> dict:
        body: dict = {"properties": properties or {}}
        if parent_page_id:
            body["parent"] = {"type": "page_id", "page_id": parent_page_id}
        elif parent_database_id:
            body["parent"] = {"type": "database_id", "database_id": parent_database_id}
        else:
            raise ValueError("parent_page_id 또는 parent_database_id 중 하나 필요")
        if children is not None:
            body["children"] = children
        return self._request("POST", "/pages", json=body)

    def update_page(self, page_id: str, properties: dict | None = None, archived: bool | None = None) -> dict:
        body: dict = {}
        if properties is not None:
            body["properties"] = properties
        if archived is not None:
            body["archived"] = archived
        return self._request("PATCH", f"/pages/{page_id}", json=body)

    def update_block_children(self, block_id: str, children: list) -> dict:
        return self._request("PATCH", f"/blocks/{block_id}/children", json={"children": children})

    def create_database(self, parent_page_id: str, title: str, properties: dict) -> dict:
        body = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        return self._request("POST", "/databases", json=body)

    def archive_page(self, page_id: str) -> dict:
        return self._request("PATCH", f"/pages/{page_id}", json={"archived": True})

    def close(self) -> None:
        self._client.close()
