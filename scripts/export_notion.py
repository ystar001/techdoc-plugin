"""TechDoc → Notion publish 오케스트레이션 (v1.2.0).

mode 자동 판별 → preflight → state load → push pages/DB → state save.
LLM 호출 0회.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

from scripts.card_layout import detect_mode
from scripts.notion.blocks import markdown_to_blocks
from scripts.notion.client import NotionAPIError, NotionClient
from scripts.notion.keyref_db import create_keyref_database, upsert_keyref
from scripts.notion.preflight import check_notion_access
from scripts.notion.state import (
    compute_content_hash,
    detect_section_changes,
    load_state,
    save_state,
)


def _load_standard_sections(output_dir: Path) -> tuple[str, list[dict], list[dict]]:
    """document_final.json または document_draft.json 로드.

    Returns (report_title, sections_list, appendices_list).
    각 section/appendix는 {"id", "title", "html_content"}.
    """
    for fname in ("document_final.json", "document_draft.json"):
        p = output_dir / fname
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            title = data.get("title", "")
            sections = data.get("sections", [])
            appendices = (
                data.get("tech_appendices", []) + data.get("project_appendices", [])
            )
            return title, sections, appendices
    raise FileNotFoundError("document_final.json 또는 document_draft.json 없음")


def _load_keyrefs(output_dir: Path) -> list[dict]:
    """KeyRef/*.md를 YAML frontmatter dict 리스트로."""
    keyref_dir = output_dir / "KeyRef"
    if not keyref_dir.exists():
        return []
    import yaml

    refs: list[dict] = []
    for md in sorted(keyref_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        end = text.find("---", 3)
        if end < 0:
            continue
        try:
            front = yaml.safe_load(text[3:end])
            if isinstance(front, dict):
                refs.append(front)
        except Exception:
            continue
    return refs


def run_export(
    output_dir: Path,
    parent_page_id: str,
    token: str,
    transport: httpx.BaseTransport | None = None,
    dry_run: bool = False,
    force: bool = False,
    archive_stale: bool = True,
) -> dict:
    """전체 push 흐름. result dict 반환."""
    output_dir = Path(output_dir)
    mode = detect_mode(output_dir)
    if mode == "unknown":
        return {"status": "error", "reason": f"unknown mode in {output_dir}"}

    client = NotionClient(token=token, transport=transport)

    # 1. Preflight
    ok, reason = check_notion_access(client, parent_page_id)
    if not ok:
        return {"status": "error", "reason": f"preflight: {reason}"}

    # 2. Load state
    state = load_state(output_dir)

    # Task 15: parent_page_id 일관성 검사 — 실제 값이 있을 때만.
    # state에 기록된 parent와 인자가 다르면 즉시 abort (Notion 트리 이중화 방지).
    if state["parent_page_id"] and state["parent_page_id"] != parent_page_id:
        return {
            "status": "error",
            "reason": (
                f"parent_page_id 불일치 (state: {state['parent_page_id']}, "
                f"인자: {parent_page_id}). notion_state.json 삭제 후 새로 push 또는 Notion에서 수동 이동."
            ),
        }
    state["parent_page_id"] = parent_page_id

    pushed_count = 0

    # 3. mode별 push
    if mode == "standard":
        report_title, sections, appendices = _load_standard_sections(output_dir)

        # 3-1. 루트 페이지 생성 또는 update
        if not state["report_page_id"]:
            if not dry_run:
                resp = client.create_page(
                    parent_page_id=parent_page_id,
                    properties={"title": [{"type": "text", "text": {"content": report_title or "보고서"}}]},
                )
                state["report_page_id"] = resp["id"]
                state["report_last_edited_time"] = resp.get("last_edited_time")
            else:
                state["report_page_id"] = "dry-run-report-page"

        # title 변경 감지 — 변경 시 루트 페이지 title 갱신
        if (
            state.get("report_title")
            and state["report_title"] != report_title
            and state["report_page_id"]
            and not dry_run
        ):
            with contextlib.suppress(NotionAPIError):
                client.update_page(
                    page_id=state["report_page_id"],
                    properties={"title": [{"type": "text", "text": {"content": report_title}}]},
                )
        state["report_title"] = report_title

        # 3-2. KeyRef DB 생성 (없으면)
        if not state["keyref_db_id"]:
            if not dry_run:
                state["keyref_db_id"] = create_keyref_database(client, state["report_page_id"])
            else:
                state["keyref_db_id"] = "dry-run-db-id"

        # 3-3. KeyRef rows upsert
        for kr in _load_keyrefs(output_dir):
            url_key = kr.get("url", "")
            if not url_key:
                continue
            existing = state["keyrefs"].get(url_key, {})
            existing_row = existing.get("row_id")
            new_hash = compute_content_hash(kr)
            if not force and existing.get("content_hash") == new_hash:
                continue
            if not dry_run:
                row_id, last_edited = upsert_keyref(client, state["keyref_db_id"], kr, existing_row)
            else:
                row_id = existing_row or "dry-run-row"
                last_edited = None
            state["keyrefs"][url_key] = {
                "row_id": row_id,
                "content_hash": new_hash,
                "last_edited_time": last_edited,
            }
            pushed_count += 1

        # I1: KeyRef upsert 완료 후 REF-ID → row_id 맵 빌드
        keyref_id_map: dict[str, str] = {}
        for kr in _load_keyrefs(output_dir):
            url_key = kr.get("url", "")
            ref_id = kr.get("id", "")  # e.g. "REF-023"
            if url_key and ref_id:
                entry = state["keyrefs"].get(url_key, {})
                row_id = entry.get("row_id")
                if row_id:
                    keyref_id_map[ref_id] = row_id

        # 3-4. 섹션 페이지 push
        section_contents = {s["id"]: s.get("html_content", "") for s in sections}
        changes = detect_section_changes(state, section_contents)
        for sid in changes["new"] + changes["modified"]:
            sec = next((s for s in sections if s["id"] == sid), None)
            if not sec:
                continue
            blocks = markdown_to_blocks(sec.get("html_content", ""), keyref_id_map=keyref_id_map)
            if not dry_run:
                if sid in changes["new"]:
                    resp = client.create_page(
                        parent_page_id=state["report_page_id"],
                        properties={"title": [{"type": "text", "text": {"content": f"{sid} {sec.get('title', '')}"}}]},
                        children=blocks,
                    )
                    state["sections"][sid] = {
                        "page_id": resp["id"],
                        "content_hash": compute_content_hash(sec.get("html_content", "")),
                        "last_edited_time": resp.get("last_edited_time"),
                    }
                else:
                    page_id = state["sections"][sid]["page_id"]
                    client.update_block_children(page_id, blocks)
                    state["sections"][sid]["content_hash"] = compute_content_hash(sec.get("html_content", ""))
            pushed_count += 1

        # 3-5. stale 섹션 archive
        if archive_stale:
            for sid in changes["stale"]:
                page_id = state["sections"][sid]["page_id"]
                if not dry_run:
                    with contextlib.suppress(NotionAPIError):
                        client.archive_page(page_id)
                state["sections"].pop(sid, None)

        # C2: 별첨(tech_appendices + project_appendices) push
        appendix_contents = {a["id"]: a.get("html_content", "") for a in appendices}
        app_changes = detect_section_changes(state, appendix_contents, state_key="appendices")
        for aid in app_changes["new"] + app_changes["modified"]:
            ap = next((a for a in appendices if a["id"] == aid), None)
            if not ap:
                continue
            blocks = markdown_to_blocks(ap.get("html_content", ""), keyref_id_map=keyref_id_map)
            if not dry_run:
                if aid in app_changes["new"]:
                    resp = client.create_page(
                        parent_page_id=state["report_page_id"],
                        properties={"title": [{"type": "text", "text": {"content": f"별첨 {aid} {ap.get('title', '')}"}}]},
                        children=blocks,
                    )
                    state["appendices"][aid] = {
                        "page_id": resp["id"],
                        "content_hash": compute_content_hash(ap.get("html_content", "")),
                        "last_edited_time": resp.get("last_edited_time"),
                    }
                else:
                    page_id = state["appendices"][aid]["page_id"]
                    client.update_block_children(page_id, blocks)
                    state["appendices"][aid]["content_hash"] = compute_content_hash(ap.get("html_content", ""))
            pushed_count += 1

        # stale 별첨 archive
        if archive_stale:
            for aid in app_changes["stale"]:
                page_id = state["appendices"][aid]["page_id"]
                if not dry_run:
                    with contextlib.suppress(NotionAPIError):
                        client.archive_page(page_id)
                state["appendices"].pop(aid, None)

    elif mode == "self_model":
        # Task 14: cards/*_card.json 순회 — 각 카드를 Notion 페이지 1개로 push.
        # card.name 이 빈 경우 card_id로 fallback (§critical impl note 4).
        from scripts.card_layout import load_self_model_card

        report_title = output_dir.name  # 보고서 title은 디렉토리 이름으로 fallback
        card_files = sorted((output_dir / "cards").glob("*_card.json"))
        card_ids = [p.stem.replace("_card", "") for p in card_files]

        # 루트 페이지
        if not state["report_page_id"]:
            if not dry_run:
                resp = client.create_page(
                    parent_page_id=parent_page_id,
                    properties={"title": [{"type": "text", "text": {"content": report_title}}]},
                )
                state["report_page_id"] = resp["id"]
                state["report_last_edited_time"] = resp.get("last_edited_time")
            else:
                state["report_page_id"] = "dry-run-report-page"

        # title 변경 감지
        if (
            state.get("report_title")
            and state["report_title"] != report_title
            and state["report_page_id"]
            and not dry_run
        ):
            with contextlib.suppress(NotionAPIError):
                client.update_page(
                    page_id=state["report_page_id"],
                    properties={"title": [{"type": "text", "text": {"content": report_title}}]},
                )
        state["report_title"] = report_title

        # 각 카드 push
        card_contents: dict[str, dict] = {}
        for cid in card_ids:
            try:
                card_contents[cid] = load_self_model_card(output_dir, cid)
            except FileNotFoundError:
                continue

        changes = detect_section_changes(state, card_contents)
        for cid in changes["new"] + changes["modified"]:
            card = card_contents[cid]
            # 카드의 sections dict → 마크다운 단일 문자열로 평탄화
            md_parts: list[str] = []
            for sec_key, sec in card.get("sections", {}).items():
                body = sec.get("body", "") if isinstance(sec, dict) else str(sec)
                md_parts.append(f"## {sec_key}\n\n{body}")
            md = "\n\n".join(md_parts)
            blocks = markdown_to_blocks(md, keyref_id_map={})
            if not dry_run:
                if cid in changes["new"]:
                    card_name = card.get("name", "") or cid
                    resp = client.create_page(
                        parent_page_id=state["report_page_id"],
                        properties={"title": [{"type": "text", "text": {"content": f"{cid} {card_name}"}}]},
                        children=blocks,
                    )
                    state["sections"][cid] = {
                        "page_id": resp["id"],
                        "content_hash": compute_content_hash(card),
                        "last_edited_time": resp.get("last_edited_time"),
                    }
                else:
                    page_id = state["sections"][cid]["page_id"]
                    client.update_block_children(page_id, blocks)
                    state["sections"][cid]["content_hash"] = compute_content_hash(card)
            pushed_count += 1

        # stale archive
        if archive_stale:
            for cid in changes["stale"]:
                page_id = state["sections"][cid]["page_id"]
                if not dry_run:
                    with contextlib.suppress(NotionAPIError):
                        client.archive_page(page_id)
                state["sections"].pop(cid, None)

    # 4. State save
    state["last_pushed_at"] = datetime.now().isoformat()
    save_state(output_dir, state)
    client.close()

    return {
        "status": "success",
        "mode": mode,
        "pushed_count": pushed_count,
        "report_page_id": state["report_page_id"],
    }


def main() -> int:
    """Task 16: CLI entry point.

    NOTION_TOKEN 환경 변수 필수. 미설정 시 integration 안내 URL 출력 후 exit 1.
    --archive-stale / --no-archive-stale BooleanOptionalAction 지원.
    """
    import argparse

    ap = argparse.ArgumentParser(prog="export_notion", description="TechDoc → Notion publish")
    ap.add_argument("--doc", default="./output", help="보고서 output 디렉토리")
    ap.add_argument("--parent-page", required=True, help="Notion 부모 페이지 UUID")
    ap.add_argument("--dry-run", action="store_true", help="실제 API 호출 안 함")
    ap.add_argument("--force", action="store_true", help="hash 비교 skip, 강제 update")
    ap.add_argument(
        "--archive-stale",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="이전 state에 있던 stale 항목 archive (기본 on)",
    )
    args = ap.parse_args()

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("오류: NOTION_TOKEN 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        print(
            "Notion integration 생성: https://www.notion.so/my-integrations",
            file=sys.stderr,
        )
        return 1

    result = run_export(
        output_dir=Path(args.doc),
        parent_page_id=args.parent_page,
        token=token,
        dry_run=args.dry_run,
        force=args.force,
        archive_stale=args.archive_stale,
    )

    if result["status"] == "success":
        print(f"OK: {result.get('pushed_count', 0)}건 push, mode={result.get('mode')}")
        print(f"보고서 root page: {result.get('report_page_id')}")
        return 0
    print(f"오류: {result.get('reason', 'unknown')}", file=sys.stderr)
    return 1 if result["status"] == "error" else 2


if __name__ == "__main__":
    sys.exit(main())
