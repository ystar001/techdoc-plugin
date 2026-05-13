# techdoc-plugin/tests/test_notion_state.py
"""notion_state.json 회귀 (v1.2.0)."""

from __future__ import annotations

import json
from pathlib import Path


def test_load_state_returns_empty_when_missing(tmp_path):
    from scripts.notion.state import load_state

    state = load_state(tmp_path)
    assert state["schema_version"] == "0.1.0"
    assert state["sections"] == {}
    assert state["keyrefs"] == {}
    assert state["report_page_id"] is None


def test_save_and_load_round_trip(tmp_path):
    from scripts.notion.state import load_state, save_state

    s = load_state(tmp_path)
    s["report_page_id"] = "abc"
    s["sections"]["1.1"] = {
        "page_id": "p1",
        "content_hash": "h1",
        "last_edited_time": "2026-05-13T10:00:00Z",  # v2 compat 원칙 1
    }
    save_state(tmp_path, s)

    s2 = load_state(tmp_path)
    assert s2["report_page_id"] == "abc"
    assert s2["sections"]["1.1"]["page_id"] == "p1"
    assert s2["sections"]["1.1"]["last_edited_time"] == "2026-05-13T10:00:00Z"


def test_state_includes_schema_version(tmp_path):
    """v2 compat 원칙 #4: schema_version 명시."""
    from scripts.notion.state import load_state, save_state

    s = load_state(tmp_path)
    save_state(tmp_path, s)

    raw = json.loads((tmp_path / "notion_state.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == "0.1.0"


def test_compute_content_hash_deterministic():
    from scripts.notion.state import compute_content_hash

    h1 = compute_content_hash("same content")
    h2 = compute_content_hash("same content")
    h3 = compute_content_hash("different content")
    assert h1 == h2
    assert h1 != h3


def test_compute_content_hash_handles_dict():
    """dict도 안정적으로 hash — sorted keys."""
    from scripts.notion.state import compute_content_hash

    h1 = compute_content_hash({"a": 1, "b": 2})
    h2 = compute_content_hash({"b": 2, "a": 1})
    assert h1 == h2


# Task 11 tests — detect_section_changes
def test_detect_changes_new_section(tmp_path):
    from scripts.notion.state import detect_section_changes

    old_state = {"sections": {}}
    new_sections = {"1.1": "new body"}
    changes = detect_section_changes(old_state, new_sections)
    assert "1.1" in changes["new"]
    assert changes["modified"] == []
    assert changes["unchanged"] == []
    assert changes["stale"] == []


def test_detect_changes_modified_section(tmp_path):
    from scripts.notion.state import compute_content_hash, detect_section_changes

    old_hash = compute_content_hash("old body")
    old_state = {"sections": {"1.1": {"page_id": "p1", "content_hash": old_hash}}}
    new_sections = {"1.1": "new body"}
    changes = detect_section_changes(old_state, new_sections)
    assert changes["new"] == []
    assert "1.1" in changes["modified"]


def test_detect_changes_unchanged_section():
    from scripts.notion.state import compute_content_hash, detect_section_changes

    body = "same body"
    h = compute_content_hash(body)
    old_state = {"sections": {"1.1": {"page_id": "p1", "content_hash": h}}}
    changes = detect_section_changes(old_state, {"1.1": body})
    assert "1.1" in changes["unchanged"]


def test_detect_changes_stale_section():
    from scripts.notion.state import detect_section_changes

    old_state = {"sections": {"1.1": {"page_id": "p1", "content_hash": "h"}}}
    changes = detect_section_changes(old_state, {})  # 1.1 사라짐
    assert "1.1" in changes["stale"]
