"""KeyRef YAML → Notion database row + DB schema 정의 (v1.2.0).

URL을 unique key로 사용 (KeyRef의 id는 보고서 내부 식별자라 전역 부적합).
"""

from __future__ import annotations

CATEGORY_OPTIONS = ["학술", "기업R&D", "전문연구기관", "정부공공", "산업시장", "국제기구", "뉴스"]
RELIABILITY_OPTIONS = ["확인됨", "단일출처", "미확인", "AI지식"]

KEYREF_DB_TITLE = "KeyRef"

# DB schema (create_database 호출에 사용)
DB_SCHEMA_PROPERTIES = {
    "Title": {"title": {}},
    "ID": {"rich_text": {}},
    "Category": {"select": {"options": [{"name": n} for n in CATEGORY_OPTIONS]}},
    "Source": {"rich_text": {}},
    "Institution": {"rich_text": {}},
    "Authors": {"rich_text": {}},
    "Year": {"number": {}},
    "Venue": {"rich_text": {}},
    "URL": {"url": {}},
    "Reliability": {"select": {"options": [{"name": n} for n in RELIABILITY_OPTIONS]}},
    "Related Sections": {"multi_select": {"options": []}},
    "Key Numbers": {"rich_text": {}},
}


def _rich_text_prop(value: str | None) -> dict:
    if not value:
        return {"rich_text": []}
    return {"rich_text": [{"type": "text", "text": {"content": value[:2000]}}]}


def _select_prop(value: str | None, allowed: list[str]) -> dict:
    if not value or value not in allowed:
        return {"select": None}
    return {"select": {"name": value}}


def keyref_to_row_properties(keyref: dict) -> dict:
    """KeyRef dict → Notion 페이지 properties dict."""
    props: dict = {}

    title = keyref.get("title", "")
    props["Title"] = {"title": [{"type": "text", "text": {"content": title[:2000]}}]}
    props["ID"] = _rich_text_prop(keyref.get("id", ""))
    props["Category"] = _select_prop(keyref.get("category"), CATEGORY_OPTIONS)
    props["Source"] = _rich_text_prop(keyref.get("source", ""))
    props["Institution"] = _rich_text_prop(keyref.get("institution", ""))

    authors = keyref.get("authors", [])
    if isinstance(authors, list):
        authors_text = ", ".join(str(a) for a in authors)
    else:
        authors_text = str(authors)
    props["Authors"] = _rich_text_prop(authors_text)

    year = keyref.get("year")
    if isinstance(year, int):
        props["Year"] = {"number": year}

    props["Venue"] = _rich_text_prop(keyref.get("venue", ""))
    props["URL"] = {"url": keyref.get("url") or None}
    props["Reliability"] = _select_prop(keyref.get("reliability"), RELIABILITY_OPTIONS)

    related = keyref.get("related_sections", [])
    if isinstance(related, list) and related:
        props["Related Sections"] = {
            "multi_select": [{"name": str(s)} for s in related],
        }

    key_nums = keyref.get("key_numbers", [])
    if isinstance(key_nums, list):
        kn_text = " · ".join(str(k) for k in key_nums)
    else:
        kn_text = str(key_nums)
    props["Key Numbers"] = _rich_text_prop(kn_text)

    return props


def create_keyref_database(client, parent_page_id: str) -> str:
    """KeyRef DB를 parent_page_id 안에 생성. DB id 반환."""
    resp = client.create_database(
        parent_page_id=parent_page_id,
        title=KEYREF_DB_TITLE,
        properties=DB_SCHEMA_PROPERTIES,
    )
    return resp["id"]


def upsert_keyref(client, db_id: str, keyref: dict, existing_row_id: str | None) -> str:
    """KeyRef row를 DB에 create 또는 update.

    existing_row_id가 주어지면 update_page, 아니면 create_page (parent=database).
    URL은 unique key로 호출자가 state에서 추적.
    """
    props = keyref_to_row_properties(keyref)
    if existing_row_id:
        resp = client.update_page(page_id=existing_row_id, properties=props)
    else:
        resp = client.create_page(parent_database_id=db_id, properties=props)
    return resp["id"]
