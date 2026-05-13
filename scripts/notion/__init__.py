"""scripts.notion — Notion push integration (v1.2.0).

Public API:
    NotionClient  — REST 래퍼 (rate limit 3 req/sec, 429/5xx retry)
    NotionAPIError — API 오류 예외
"""

from scripts.notion.client import NotionAPIError, NotionClient

__all__ = ["NotionAPIError", "NotionClient"]
