"""schema_version 기반 JSON 체크포인트 마이그레이션.

v0.1.0 → 미래 버전으로 갈 때, 구 스키마 JSON을 신 스키마로 자동 변환.
현재는 v0.1.0이 기준이므로 no-op (판단·보고만 수행), 향후 v0.2.0에서 실제 변환 로직 추가.

사용법:
    python -m scripts.migrate --input ./output/document_final.json  # 검사만
    python -m scripts.migrate --input ./output/ --write             # 발견 시 변환 저장
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from techdoc_core.constants import DEFAULT_SECTION_TITLES, SCHEMA_VERSION
from techdoc_core.schemas import format_error

# F14: title 운영 미주 패턴. 매칭 부분을 떼어 split_summary로 보낸다.
_TITLE_NOTE_PATTERNS = [
    r"\s*[—-]\s*분할\s*\d+\s*/\s*\d+\s*$",          # — 분할 1/3
    r"\s*\(\s*분할\s*\d+\s*/\s*\d+\s*\)\s*$",        # (분할 1/3)
    r"\s*[—-]\s*(§\d+[^—()]*?)\s*$",                  # — §1 정의·범위 + §2 ...
    r"\s*\(\s*§\d+\s*~\s*§\d+\s*\)\s*$",              # (§1~§3)
    r"\s*\(\s*X?L\d+\s*,\s*\d+p\s*\)\s*$",            # (L1, 10p) / (XL1, 10p)
    r"\s*[—-]\s*X?L\d+\s*$",                          # — L1 / — XL1
]


def split_title_notes(title: str) -> tuple[str, str]:
    """title에서 운영 미주를 떼어 (정제 title, split_summary) 반환. (F14)"""
    notes: list[str] = []
    cur = title
    changed = True
    while changed:
        changed = False
        for pat in _TITLE_NOTE_PATTERNS:
            m = re.search(pat, cur)
            if m:
                notes.insert(0, m.group(0).lstrip(" —-").strip())
                cur = cur[: m.start()].rstrip()
                changed = True
    return cur.strip(), " ".join(n for n in notes if n).strip()


_SEC_PREFIX_RE = re.compile(r"^(sec[1-6])")
_BODY_VARIANT_KEYS = ("body", "narrative", "content")


def _section_body(sec: dict) -> str:
    """body·narrative·content 중 첫 비어있지 않은 값 (F1)."""
    if not isinstance(sec, dict):
        return str(sec)
    for k in _BODY_VARIANT_KEYS:
        v = sec.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def normalize_sections(sections: dict) -> dict:
    """섹션 dict를 0.2.0 표준으로 변환 (F1 body + F3 키→secN + title)."""
    out: dict[str, dict] = {}
    for key, sec in sections.items():
        m = _SEC_PREFIX_RE.match(key)
        canonical = m.group(1) if m else key  # secN prefix면 위치 키로
        title = ""
        if isinstance(sec, dict):
            title = str(sec.get("title", "")).strip()
        if not title and canonical in DEFAULT_SECTION_TITLES:
            title = DEFAULT_SECTION_TITLES[canonical]
        out[canonical] = {"title": title, "body": _section_body(sec)}
    return out

# 향후 버전별 마이그레이션 핸들러 등록
# key = (from_version, to_version), value = callable(data: dict) -> dict
MIGRATIONS: dict[tuple[str, str], callable] = {}


def register_migration(from_v: str, to_v: str):
    """마이그레이션 핸들러 등록 데코레이터."""
    def decorator(fn):
        MIGRATIONS[(from_v, to_v)] = fn
        return fn
    return decorator


def detect_version(data: dict) -> str:
    """JSON data에서 schema_version 추출 (없으면 '0.0.0'으로 간주)."""
    return data.get("schema_version", "0.0.0")


def needs_migration(data: dict) -> bool:
    """마이그레이션 필요 여부."""
    return detect_version(data) != SCHEMA_VERSION


def apply_migration_path(data: dict, to_v: str = SCHEMA_VERSION) -> dict:
    """현재 버전 → to_v로 가는 체인 적용."""
    current = detect_version(data)
    if current == to_v:
        return data

    # 단순 체인 탐색 (직접 경로만, 복잡한 그래프 탐색 없음)
    while current != to_v:
        step_key = next(
            ((src, dst) for (src, dst) in MIGRATIONS if src == current), None
        )
        if step_key is None:
            raise ValueError(format_error(
                "TECHDOC-E081",
                f"No migration path from {current} to {to_v}",
                "plugin 버전 확인 후 재시도"
            ))
        handler = MIGRATIONS[step_key]
        data = handler(data)
        data["schema_version"] = step_key[1]
        current = step_key[1]

    return data


@register_migration("0.1.0", "0.2.0")
def _migrate_self_model_0_1_to_0_2(data: dict) -> dict:
    """self-model 카드 0.1.0 → 0.2.0 (F1·F3·F13·F14).

    self-model 카드만 변환한다(`sections` dict 보유 & `blocks` 미보유).
    standard 카드·기타 JSON은 그대로 반환.
    """
    if "sections" not in data or "blocks" in data:
        return data

    # F13: 단일 card_id(split marker 포함) + parent_id
    card_id = data.get("appendix_id") or data.get("card_id") or data.get("id", "")
    parent_id = data.get("section_id", "")
    if parent_id == card_id:
        parent_id = ""
    data["card_id"] = card_id
    data["parent_id"] = parent_id

    # F14: title 운영미주 분리
    title, note = split_title_notes(str(data.get("title", "")))
    data["title"] = title
    if note and not data.get("split_summary"):
        data["split_summary"] = note

    # F1·F3: 섹션 정규화
    data["sections"] = normalize_sections(data.get("sections", {}))
    return data


def scan_dir(output_dir: Path) -> list[Path]:
    """output_dir에서 schema_version 필드가 있을 법한 JSON 파일 스캔."""
    candidates = [
        "document_final.json",
        "document_draft.json",
        "draft_outline.json",
        "final_outline.json",
        "reference_list.json",
        "merged_research.json",
        "writer_state.json",
        "quality_report.json",
    ]
    found = []
    for name in candidates:
        p = output_dir / name
        if p.exists():
            found.append(p)
    # research_round_*.json
    found.extend(sorted(output_dir.glob("research_round_*.json")))
    return found


def report_file(path: Path) -> dict:
    """단일 파일 버전 상태 보고."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"path": str(path), "status": "invalid_json"}

    if not isinstance(data, dict):
        return {"path": str(path), "status": "not_dict"}

    current = detect_version(data)
    return {
        "path": str(path),
        "current_version": current,
        "target_version": SCHEMA_VERSION,
        "needs_migration": current != SCHEMA_VERSION,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate JSON checkpoints by schema_version")
    ap.add_argument("-i", "--input", required=True, help="단일 JSON 또는 디렉토리")
    ap.add_argument("--write", action="store_true", help="발견된 마이그레이션 대상 실제 변환·저장")
    args = ap.parse_args()

    input_path = Path(args.input)
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = scan_dir(input_path)
    else:
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 1

    if not files:
        print("마이그레이션 대상 파일 없음")
        return 0

    print(f"--- 스캔 결과 ({len(files)}개 파일) ---")
    migrate_targets = []
    for p in files:
        report = report_file(p)
        if report.get("needs_migration"):
            print(f"  MIGRATE: {p.name} ({report['current_version']} → {SCHEMA_VERSION})")
            migrate_targets.append(p)
        else:
            status = report.get("status", "ok")
            v = report.get("current_version", "?")
            print(f"  OK: {p.name} (v{v}, {status})")

    if not migrate_targets:
        print("모든 파일이 최신 스키마")
        return 0

    if not args.write:
        print(f"\n--write 옵션으로 실제 변환 가능 ({len(migrate_targets)}개 대상)")
        return 0

    # 실제 변환
    for p in migrate_targets:
        data = json.loads(p.read_text(encoding="utf-8"))
        try:
            migrated = apply_migration_path(data)
        except ValueError as e:
            print(f"  FAIL: {p.name} — {e}", file=sys.stderr)
            continue
        # 백업 후 덮어쓰기
        backup = p.with_suffix(p.suffix + f".v{detect_version(data)}.bak")
        backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        p.write_text(json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  OK: {p.name} (backup: {backup.name})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
