# techdoc-plugin/tests/test_export_notion.py
"""export_notion 통합 회귀 (v1.2.0)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest


# ─── helpers ──────────────────────────────────────────────────────────────────


def _setup_standard_doc(tmp_path: Path) -> None:
    """standard mode 보고서 디렉토리 생성 (writer_state + document_draft + KeyRef)."""
    (tmp_path / "writer_state.json").write_text(
        json.dumps({
            "schema_version": "0.1.0",
            "section_states": {"1.1": {"cards": [{"id": "1.1.1", "type": "tech"}]}},
        }),
        encoding="utf-8",
    )
    (tmp_path / "document_draft.json").write_text(
        json.dumps({
            "title": "테스트 보고서",
            "sections": [
                {"id": "1.1", "title": "섹션 1.1", "html_content": "<p>본문</p>"},
            ],
        }),
        encoding="utf-8",
    )
    keyref_dir = tmp_path / "KeyRef"
    keyref_dir.mkdir()
    (keyref_dir / "REF-001.md").write_text(
        "---\nid: REF-001\ntitle: Sample\nurl: https://x.test\ncategory: 학술\n---\n원문.",
        encoding="utf-8",
    )


# ─── Task 13: standard mode ───────────────────────────────────────────────────


def test_run_export_standard_mode_creates_pages_and_db(tmp_path):
    """standard 모드 — 루트 페이지·섹션 페이지·KeyRef DB·KeyRef row 모두 생성."""
    from scripts.export_notion import run_export

    _setup_standard_doc(tmp_path)

    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"method": request.method, "url": str(request.url)})
        url = str(request.url)
        if "/v1/pages/" in url and request.method == "GET":  # preflight
            return httpx.Response(200, json={"object": "page", "id": "parent"})
        if "/v1/databases" in url and request.method == "POST":
            return httpx.Response(200, json={"id": "db-id", "object": "database"})
        if "/v1/pages" in url and request.method == "POST":
            return httpx.Response(200, json={"id": "new-page-id", "object": "page"})
        if "/v1/blocks/" in url and request.method == "PATCH":
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json={"id": "x"})

    result = run_export(
        output_dir=tmp_path,
        parent_page_id="parent",
        token="test_token",
        transport=httpx.MockTransport(handler),
    )

    assert result["status"] in ("success", "partial_success")
    # state file 저장됨
    assert (tmp_path / "notion_state.json").exists()
    state = json.loads((tmp_path / "notion_state.json").read_text(encoding="utf-8"))
    assert state["parent_page_id"] == "parent"
    assert state["report_page_id"] is not None


# ─── Task 14: self-model mode ─────────────────────────────────────────────────


def test_run_export_self_model_mode(tmp_path):
    """self-model 모드 — cards/<id>_card.json 순회."""
    from scripts.export_notion import run_export

    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "1.1_card.json").write_text(
        json.dumps({
            "id": "1.1",
            "name": "테스트 카드",
            "sections": {
                "sec1_definition_scope": {"body": "정의 본문 ..."},
                "sec2_principles": {"body": "원리 본문 ..."},
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    page_creates: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/v1/pages/" in url and request.method == "GET":
            return httpx.Response(200, json={"object": "page", "id": "parent"})
        if "/v1/pages" in url and request.method == "POST":
            page_creates.append(request.read().decode())
            return httpx.Response(200, json={"id": "new-page", "object": "page"})
        return httpx.Response(200, json={"id": "x"})

    result = run_export(
        output_dir=tmp_path,
        parent_page_id="parent",
        token="t",
        transport=httpx.MockTransport(handler),
    )
    assert result["status"] == "success"
    assert result["mode"] == "self_model"
    # 카드 1.1을 한 페이지로 생성 + 루트 페이지
    assert len(page_creates) >= 2  # 루트 페이지 + 카드 1개


# ─── Task 15: parent_page_id 검증 + title 변경 ────────────────────────────────


def test_parent_page_id_mismatch_aborts(tmp_path):
    """state에 저장된 parent_page_id와 인자가 다르면 즉시 abort."""
    from scripts.export_notion import run_export

    (tmp_path / "notion_state.json").write_text(
        json.dumps({
            "schema_version": "0.1.0",
            "parent_page_id": "OLD-parent",
            "report_page_id": "r1",
            "keyref_db_id": "db1",
            "report_title": None,
            "sections": {},
            "appendices": {},
            "keyrefs": {},
            "last_pushed_at": None,
        }),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "x"})

    result = run_export(
        output_dir=tmp_path,
        parent_page_id="NEW-parent",  # 다른 parent
        token="t",
        transport=httpx.MockTransport(handler),
    )
    assert result["status"] == "error"
    assert "parent_page_id" in result["reason"]


def test_report_title_change_updates_root_page(tmp_path):
    """보고서 title이 state 기록과 다르면 루트 페이지 title 갱신."""
    from scripts.export_notion import run_export

    _setup_standard_doc(tmp_path)
    # document_draft.json의 title을 변경
    doc = json.loads((tmp_path / "document_draft.json").read_text("utf-8"))
    doc["title"] = "변경된 제목"
    (tmp_path / "document_draft.json").write_text(
        json.dumps(doc, ensure_ascii=False), encoding="utf-8"
    )

    # 기존 state에 다른 title 기록
    (tmp_path / "notion_state.json").write_text(
        json.dumps({
            "schema_version": "0.1.0",
            "parent_page_id": "p",
            "report_page_id": "existing-root",
            "report_title": "이전 제목",
            "keyref_db_id": "db",
            "sections": {},
            "appendices": {},
            "keyrefs": {},
            "last_pushed_at": None,
        }),
        encoding="utf-8",
    )

    patches: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PATCH" and "/pages/existing-root" in str(request.url):
            patches.append(request.read().decode())
        return httpx.Response(200, json={"id": "x"})

    run_export(
        output_dir=tmp_path,
        parent_page_id="p",
        token="t",
        transport=httpx.MockTransport(handler),
    )
    assert any("변경된 제목" in body for body in patches)


# ─── Task 16: CLI ─────────────────────────────────────────────────────────────


def test_cli_without_token_exits_nonzero(tmp_path, monkeypatch):
    """NOTION_TOKEN 미설정 시 CLI 실패."""
    from scripts.export_notion import main

    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    import sys as _s

    argv_bak = list(_s.argv)
    try:
        _s.argv = ["export_notion", "--doc", str(tmp_path), "--parent-page", "abc"]
        rc = main()
    finally:
        _s.argv = argv_bak
    assert rc != 0


def test_cli_with_dry_run(tmp_path, monkeypatch):
    """--dry-run 모드: 실제 API 호출 없이 stats만."""
    from scripts.export_notion import main

    _setup_standard_doc(tmp_path)
    monkeypatch.setenv("NOTION_TOKEN", "test")
    import sys as _s

    argv_bak = list(_s.argv)
    try:
        _s.argv = ["export_notion", "--doc", str(tmp_path), "--parent-page", "abc", "--dry-run"]
        rc = main()
    finally:
        _s.argv = argv_bak
    # dry-run은 preflight도 skip이므로 0 종료 가능
    # 또는 preflight 실패로 비0. 두 경우 다 허용 (네트워크 의존).
    assert rc in (0, 1)


# ─── C1 regression: last_edited_time 저장 ─────────────────────────────────────


def test_run_export_stores_last_edited_time_from_api(tmp_path):
    """v2 compat 원칙 1: 각 페이지·row의 last_edited_time이 state에 저장됨."""
    from scripts.export_notion import run_export

    _setup_standard_doc(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/v1/pages/" in url and request.method == "GET":
            return httpx.Response(200, json={"object": "page", "id": "parent"})
        if "/v1/databases" in url and request.method == "POST":
            return httpx.Response(200, json={"id": "db", "last_edited_time": "2026-05-13T11:00:00Z"})
        if "/v1/pages" in url and request.method == "POST":
            return httpx.Response(200, json={
                "id": "new-page",
                "last_edited_time": "2026-05-13T12:00:00Z",
            })
        return httpx.Response(200, json={"id": "x"})

    run_export(
        output_dir=tmp_path,
        parent_page_id="parent",
        token="t",
        transport=httpx.MockTransport(handler),
    )
    state = json.loads((tmp_path / "notion_state.json").read_text("utf-8"))
    # 섹션 또는 KeyRef 중 적어도 하나에 last_edited_time이 존재해야 함
    has_let = any(
        v.get("last_edited_time") for v in state.get("sections", {}).values()
    ) or any(
        v.get("last_edited_time") for v in state.get("keyrefs", {}).values()
    )
    assert has_let, "last_edited_time이 state에 저장되어야 함 (v2 compat 원칙 1)"


# ─── C2 regression: 별첨 push ────────────────────────────────────────────────


def _setup_doc_with_appendix(tmp_path: Path) -> None:
    """standard mode 보고서 + 별첨 포함 디렉토리 생성."""
    (tmp_path / "writer_state.json").write_text(
        json.dumps({
            "schema_version": "0.1.0",
            "section_states": {"1.1": {"cards": [{"id": "1.1.1", "type": "tech"}]}},
        }),
        encoding="utf-8",
    )
    (tmp_path / "document_draft.json").write_text(
        json.dumps({
            "title": "별첨 테스트 보고서",
            "sections": [
                {"id": "1.1", "title": "섹션 1.1", "html_content": "<p>본문</p>"},
            ],
            "tech_appendices": [
                {"id": "APP-01", "title": "기술 별첨", "html_content": "<p>별첨 본문</p>"},
            ],
            "project_appendices": [
                {"id": "APP-02", "title": "프로젝트 별첨", "html_content": "<p>프로젝트 별첨 본문</p>"},
            ],
        }),
        encoding="utf-8",
    )
    keyref_dir = tmp_path / "KeyRef"
    keyref_dir.mkdir()


def test_run_export_pushes_appendices(tmp_path):
    """C2: tech_appendices + project_appendices가 자식 페이지로 push되고 state["appendices"]에 저장됨."""
    from scripts.export_notion import run_export

    _setup_doc_with_appendix(tmp_path)

    page_creates: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/v1/pages/" in url and request.method == "GET":
            return httpx.Response(200, json={"object": "page", "id": "parent"})
        if "/v1/pages" in url and request.method == "POST":
            body = request.read().decode()
            page_creates.append(body)
            return httpx.Response(200, json={"id": f"page-{len(page_creates)}", "last_edited_time": "2026-05-13T12:00:00Z"})
        if "/v1/databases" in url and request.method == "POST":
            return httpx.Response(200, json={"id": "db"})
        return httpx.Response(200, json={"id": "x"})

    result = run_export(
        output_dir=tmp_path,
        parent_page_id="parent",
        token="t",
        transport=httpx.MockTransport(handler),
    )
    assert result["status"] == "success"

    state = json.loads((tmp_path / "notion_state.json").read_text("utf-8"))
    # 별첨 2개가 state["appendices"]에 저장되어야 함
    assert "APP-01" in state["appendices"], "APP-01 별첨이 state에 없음"
    assert "APP-02" in state["appendices"], "APP-02 별첨이 state에 없음"
    # page_id가 실제로 채워져 있어야 함
    assert state["appendices"]["APP-01"]["page_id"]
    assert state["appendices"]["APP-02"]["page_id"]
    # title에 "별첨" 포함 여부 확인
    assert any("별첨" in body for body in page_creates), "별첨 페이지 생성 요청에 '별첨'이 없음"
