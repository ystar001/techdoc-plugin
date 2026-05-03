"""TechDoc Plugin Obsidian Wiki Exporter.

document_final.json + KeyRef + figures + outline glossary → 옵시디언 vault 변환·누적.

사용법:
    python -m scripts.export_wiki --doc ./output --vault ~/Obsidian/주제 [--create-vault] [--lint]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.wiki.assets import copy_figures
from scripts.wiki.builders.appendix import (
    build_tech_appendix_page,
    build_project_appendix_page,
    appendix_filename,
)
from scripts.wiki.builders.concept import build_concept_page
from scripts.wiki.builders.entity import (
    build_tech_page,
    build_project_page,
    build_product_page,
    entity_filename,
)
from scripts.wiki.builders.index import build_index
from scripts.wiki.builders.log import append_log
from scripts.wiki.builders.report import build_report_moc
from scripts.wiki.builders.source import build_source_page, source_filename
from scripts.wiki.conflict import detect_conflicts, extract_facts, format_conflict_callout
from scripts.wiki.filename import sanitize_name
from scripts.wiki.markers import extract_ai_region, replace_ai_region


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_existing(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_card_page_with_conflict(
    builder_fn,
    card: dict,
    report_title: str,
    existing_page: str | None,
    has_appendix: bool = False,
    stats: dict | None = None,
) -> str:
    """카드 빌드 + 기존 페이지 AI 영역과 충돌 감지.

    existing_page가 있으면 새 AI 콘텐츠 vs 기존 AI 콘텐츠를 비교해 충돌 callout을 추가한다.
    """
    import inspect
    sig = inspect.signature(builder_fn)
    if "has_appendix" in sig.parameters:
        new_page = builder_fn(card, report_title=report_title, existing_page=None, has_appendix=has_appendix)
    else:
        new_page = builder_fn(card, report_title=report_title, existing_page=None)

    if existing_page is None:
        return new_page

    # 충돌 감지: 기존 AI 영역 vs 새 AI 영역
    old_ai = extract_ai_region(existing_page) or ""
    new_ai = extract_ai_region(new_page) or ""

    if old_ai and new_ai:
        facts_old = extract_facts(old_ai)
        facts_new = extract_facts(new_ai)
        conflicts = detect_conflicts(facts_old, facts_new)
        if conflicts:
            if stats is not None:
                stats["conflicts"] = stats.get("conflicts", 0) + len(conflicts)
            callout = format_conflict_callout(conflicts)
            # 충돌 callout을 새 AI 영역 앞에 추가
            new_ai_with_callout = callout + "\n" + new_ai
            if "has_appendix" in sig.parameters:
                merged_page = builder_fn(card, report_title=report_title, existing_page=existing_page, has_appendix=has_appendix)
            else:
                merged_page = builder_fn(card, report_title=report_title, existing_page=existing_page)
            # callout을 AI 영역 앞에 삽입
            return replace_ai_region(merged_page, new_ai_with_callout)

    # 충돌 없음: 기존 방식대로 갱신 (사용자 메모 보존)
    if "has_appendix" in sig.parameters:
        return builder_fn(card, report_title=report_title, existing_page=existing_page, has_appendix=has_appendix)
    return builder_fn(card, report_title=report_title, existing_page=existing_page)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="export_wiki")
    parser.add_argument("--doc", required=False, default=".", help="document_final.json 디렉토리")
    parser.add_argument("--vault", required=True, help="옵시디언 vault 경로")
    parser.add_argument("--create-vault", action="store_true", help="vault 없으면 신규 생성")
    parser.add_argument("--lint", action="store_true", help="lint만 수행, export 안 함")
    args = parser.parse_args(argv)

    doc_dir = Path(args.doc)
    vault = Path(args.vault)

    if not vault.exists():
        if not args.create_vault:
            print(
                f"오류: vault 디렉토리가 없습니다: {vault}\n  --create-vault 옵션으로 신규 생성 가능",
                file=sys.stderr,
            )
            return 1
        vault.mkdir(parents=True)

    if args.lint:
        from scripts.wiki.lint import lint_vault
        lint_vault(vault)
        return 0

    doc_path = doc_dir / "document_final.json"
    refs_path = doc_dir / "reference_list.json"
    outline_path = doc_dir / "final_outline.json"
    keyref_dir = doc_dir / "KeyRef"
    figures_dir = doc_dir / "figures"

    if not doc_path.exists():
        print(f"오류: document_final.json을 찾을 수 없습니다: {doc_path}", file=sys.stderr)
        return 1

    document = _read_json(doc_path)
    refs = _read_json(refs_path) if refs_path.exists() else {"references": []}
    outline = _read_json(outline_path) if outline_path.exists() else {}
    glossary = outline.get("glossary", {})

    title = document.get("title", "untitled")
    report_slug = sanitize_name(title)

    stats: dict = {"new_pages": 0, "updated_pages": 0, "conflicts": 0}

    def _bump(p: Path) -> None:
        if p.exists():
            stats["updated_pages"] += 1
        else:
            stats["new_pages"] += 1

    # 1. Sources
    for ref in refs.get("references", []):
        fname = source_filename(ref)
        target = vault / "Sources" / fname
        _bump(target)
        page = build_source_page(ref, keyref_dir=keyref_dir, existing_page=_read_existing(target))
        _write(target, page)

    # 2. 별첨이 있는 카드 ID 집합 (entity 빌드 시 has_appendix 결정용)
    tech_appendix_parents = {a["source_card_id"] for a in document.get("tech_appendices", [])}
    project_appendix_parents = {a["source_card_id"] for a in document.get("project_appendices", [])}

    # 3. Tech / Projects / Products 본문 카드 (충돌 감지 포함)
    for c in document.get("tech_cards", []):
        target = vault / "Tech" / entity_filename(c)
        _bump(target)
        page = _build_card_page_with_conflict(
            build_tech_page,
            c,
            report_title=title,
            existing_page=_read_existing(target),
            has_appendix=c.get("id") in tech_appendix_parents,
            stats=stats,
        )
        _write(target, page)

    for c in document.get("project_cards", []):
        target = vault / "Projects" / entity_filename(c)
        _bump(target)
        page = _build_card_page_with_conflict(
            build_project_page,
            c,
            report_title=title,
            existing_page=_read_existing(target),
            has_appendix=c.get("id") in project_appendix_parents,
            stats=stats,
        )
        _write(target, page)

    for c in document.get("product_cards", []):
        target = vault / "Products" / entity_filename(c)
        _bump(target)
        page = _build_card_page_with_conflict(
            build_product_page,
            c,
            report_title=title,
            existing_page=_read_existing(target),
            stats=stats,
        )
        _write(target, page)

    # 4. 별첨 — source_card_id → parent name 매핑
    name_by_id = {c["id"]: c.get("name", "") for c in document.get("tech_cards", [])}
    name_by_id.update({c["id"]: c.get("name", "") for c in document.get("project_cards", [])})

    for a in document.get("tech_appendices", []):
        parent_name = name_by_id.get(a.get("source_card_id"), a.get("name", "unknown"))
        target = vault / "Tech" / appendix_filename(a, parent_name)
        _bump(target)
        page = build_tech_appendix_page(
            a, parent_name=parent_name, report_title=title, existing_page=_read_existing(target)
        )
        _write(target, page)

    for a in document.get("project_appendices", []):
        parent_name = name_by_id.get(a.get("source_card_id"), a.get("name", "unknown"))
        target = vault / "Projects" / appendix_filename(a, parent_name)
        _bump(target)
        page = build_project_appendix_page(
            a, parent_name=parent_name, report_title=title, existing_page=_read_existing(target)
        )
        _write(target, page)

    # 5. Concepts (glossary)
    for term, definition in glossary.items():
        target = vault / "Concepts" / f"{sanitize_name(term)}.md"
        _bump(target)
        page = build_concept_page(term=term, definition=definition, existing_page=_read_existing(target))
        _write(target, page)

    # 6. Report MOC
    report_target = vault / "Reports" / f"{report_slug}.md"
    _bump(report_target)
    moc = build_report_moc(document, existing_page=_read_existing(report_target))
    _write(report_target, moc)

    # 7. 자산 복사
    if figures_dir.exists():
        copy_figures(figures_dir, vault, report_slug)

    # 8. Index 재생성
    index_target = vault / "index.md"
    index = build_index(vault, existing_index=_read_existing(index_target))
    _write(index_target, index)

    # 9. Log append
    log_target = vault / "log.md"
    from datetime import date as _date
    today = document.get("metadata", {}).get("date") or _date.today().isoformat()
    log = append_log(
        existing_log=_read_existing(log_target),
        date=today,
        report_title=title,
        stats=stats,
    )
    _write(log_target, log)

    # 10. 보고서 출력
    report_json = doc_dir / "wiki_export_report.json"
    report_json.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"vault 갱신 완료: {vault}")
    print(f"  신규: {stats['new_pages']} / 갱신: {stats['updated_pages']} / 충돌: {stats['conflicts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
