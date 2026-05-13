"""KeyRef → Notion DB 변환 회귀."""

from __future__ import annotations


def test_keyref_to_row_basic_fields():
    from scripts.notion.keyref_db import keyref_to_row_properties

    keyref = {
        "id": "REF-023",
        "category": "학술",
        "source": "MIT CSAIL",
        "institution": "MIT CSAIL",
        "authors": ["Park, J.", "Smith, K."],
        "year": 2024,
        "venue": "IEEE IoT Journal",
        "title": "Low-power LoRa mesh for precision irrigation",
        "url": "https://example.com/paper",
        "reliability": "확인됨",
        "related_sections": ["1.1", "2.3"],
        "key_numbers": ["정확도 94.3%"],
    }

    props = keyref_to_row_properties(keyref)

    assert props["Title"]["title"][0]["text"]["content"] == "Low-power LoRa mesh for precision irrigation"
    assert props["ID"]["rich_text"][0]["text"]["content"] == "REF-023"
    assert props["Category"]["select"]["name"] == "학술"
    assert props["Year"]["number"] == 2024
    assert props["URL"]["url"] == "https://example.com/paper"
    assert props["Reliability"]["select"]["name"] == "확인됨"
    # Related Sections — multi_select
    section_names = {opt["name"] for opt in props["Related Sections"]["multi_select"]}
    assert section_names == {"1.1", "2.3"}
    # Authors joined
    assert "Park" in props["Authors"]["rich_text"][0]["text"]["content"]


def test_keyref_to_row_missing_optional_fields():
    """선택 필드 누락 시 빈 값."""
    from scripts.notion.keyref_db import keyref_to_row_properties

    minimal = {"id": "REF-001", "title": "Min", "url": "https://x.test"}
    props = keyref_to_row_properties(minimal)
    assert props["Title"]["title"][0]["text"]["content"] == "Min"
    assert props["Category"].get("select") is None  # 비어있어도 정상
    assert "Year" not in props or props["Year"].get("number") is None


def test_keyref_to_row_key_numbers_truncated_at_2000():
    """key_numbers 합산이 2000자 초과 시 truncate."""
    from scripts.notion.keyref_db import keyref_to_row_properties

    keyref = {
        "id": "REF-x",
        "title": "T",
        "url": "https://x",
        "key_numbers": ["가" * 800, "나" * 800, "다" * 800],
    }
    props = keyref_to_row_properties(keyref)
    text = props["Key Numbers"]["rich_text"][0]["text"]["content"]
    assert len(text) <= 2000


import httpx
import pytest


def test_create_keyref_database_uses_schema():
    """create_keyref_database가 사전 정의 schema로 DB 생성."""
    from scripts.notion.client import NotionClient
    from scripts.notion.keyref_db import create_keyref_database

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"id": "db-new-id", "object": "database"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    db_id = create_keyref_database(client, parent_page_id="parent-x")

    assert db_id == "db-new-id"
    assert "/v1/databases" in captured["url"]
    assert '"Category"' in captured["body"]
    assert '"학술"' in captured["body"]


def test_upsert_keyref_creates_new_when_url_unknown():
    from scripts.notion.client import NotionClient
    from scripts.notion.keyref_db import upsert_keyref

    posts: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/pages" in str(request.url):
            posts.append({"body": request.read().decode()})
            return httpx.Response(200, json={"id": "new-row"})
        return httpx.Response(200, json={"id": "x"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    keyref = {"id": "REF-100", "title": "T", "url": "https://new.test"}
    row_id = upsert_keyref(client, db_id="db-1", keyref=keyref, existing_row_id=None)

    assert row_id == "new-row"
    assert len(posts) == 1


def test_upsert_keyref_updates_when_existing_row_id_provided():
    from scripts.notion.client import NotionClient
    from scripts.notion.keyref_db import upsert_keyref

    patches: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PATCH" and "/pages/" in str(request.url):
            patches.append(str(request.url))
            return httpx.Response(200, json={"id": "existing-row"})
        return httpx.Response(200, json={"id": "x"})

    client = NotionClient(token="t", transport=httpx.MockTransport(handler))
    keyref = {"id": "REF-100", "title": "T-updated", "url": "https://new.test"}
    row_id = upsert_keyref(client, db_id="db-1", keyref=keyref, existing_row_id="existing-row")

    assert row_id == "existing-row"
    assert any("existing-row" in p for p in patches)
