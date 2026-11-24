"""3 researcher 병렬 출력 합병·dedup.

researcher subagent A/B/C가 각각 생성한 research_round_A.json, research_round_B.json,
research_round_C.json을 하나로 병합하고 URL/제목 유사도 dedup.

사용법:
    python -m scripts.merge_research --input ./output/ -o ./output/merged_research.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

from techdoc_core.schemas import format_error

TITLE_SIMILARITY_THRESHOLD = 85  # 제목 유사도 ≥85면 중복 처리


def url_canonical(url: str) -> str:
    """URL 정규화 (프로토콜·트레일링슬래시·쿼리스트링 제거)."""
    if not url:
        return ""
    u = url.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if u.startswith(prefix):
            u = u[len(prefix):]
    u = u.split("?")[0].split("#")[0].rstrip("/")
    return u


def dedupe_refs(all_refs: list[dict]) -> tuple[list[dict], int]:
    """URL 완전 일치 + 제목 rapidfuzz 유사도 기반 중복 제거.

    Returns:
        (deduplicated_refs, removed_count)
    """
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    kept: list[dict] = []
    removed = 0

    for raw in all_refs:
        # researcher round refs_found는 스키마상 list[str](REF id)이나 dict 변형도 방어.
        if isinstance(raw, str):
            ref: dict = {"id": raw}
        elif isinstance(raw, dict):
            ref = raw
        else:
            removed += 1
            continue

        # REF id 기준 중복 제거 (str 계약의 1차 dedup 키)
        ref_id = (ref.get("id") or "").strip()
        if ref_id and ref_id in seen_ids:
            removed += 1
            continue

        url_key = url_canonical(ref.get("url", ""))
        if url_key and url_key in seen_urls:
            removed += 1
            continue

        # 제목 유사도 체크 (URL 없거나 미본 경우)
        title = (ref.get("title") or "").strip()
        dup_by_title = False
        if title and len(title) > 15:
            for kref in kept:
                ktitle = (kref.get("title") or "").strip()
                if len(ktitle) > 15 and fuzz.ratio(title, ktitle) >= TITLE_SIMILARITY_THRESHOLD:
                    dup_by_title = True
                    break

        if dup_by_title:
            removed += 1
            continue

        if url_key:
            seen_urls.add(url_key)
        if ref_id:
            seen_ids.add(ref_id)
        kept.append(ref)

    return kept, removed


_REF_LIST_KEYS = ("refs", "refs_found", "ref_ids_used", "new_refs")
_KEYREF_ID_RE = re.compile(r"^id:\s*(REF-\d+)", re.M)


def extract_round_refs(data: dict, name: str) -> tuple[list[str | dict], list[str]]:
    """라운드 JSON 한 개에서 refs를 꺼낸다 (F54·F57·F60·F77).

    researcher 병렬 산출은 꼴이 갈린다: `refs`·`refs_found`(list)·`ref_ids_used`·
    `new_refs`(list일 때)·중첩 `rounds`. 처음 맞는 list 키를 쓴다. `refs_found`가
    정수면 건수로 보고 무시한다. 아무 꼴도 없으면 빈 list와 note를 돌려준다.
    """
    notes: list[str] = []
    for key in _REF_LIST_KEYS:
        val = data.get(key)
        if isinstance(val, list):
            return list(val), notes
        if key == "refs_found" and isinstance(val, int):
            notes.append(f"{name}: refs_found가 정수({val}) — 건수로 보고 무시")
    rounds = data.get("rounds")
    if isinstance(rounds, list):
        merged: list[str | dict] = []
        for i, sub in enumerate(rounds):
            if isinstance(sub, dict):
                sub_refs, sub_notes = extract_round_refs(sub, f"{name}#rounds[{i}]")
                merged.extend(sub_refs)
                notes.extend(sub_notes)
        if merged:
            return merged, notes
    notes.append(f"{name}: refs 꼴을 찾지 못함 (keys={sorted(data)})")
    return [], notes


def load_round_files(input_dir: Path) -> tuple[list[tuple[str, list]], list[str]]:
    """input_dir에서 research_round_*.json 로드 → ([(파일명, refs)], notes)."""
    found: list[tuple[str, list]] = []
    notes: list[str] = []
    for p in sorted(input_dir.glob("research_round_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            notes.append(f"{p.name}: JSON decode failed — {e}")
            found.append((p.name, []))
            continue
        if not isinstance(data, dict):
            notes.append(f"{p.name}: 최상위가 객체가 아님")
            found.append((p.name, []))
            continue
        refs, file_notes = extract_round_refs(data, p.name)
        found.append((p.name, refs))
        notes.extend(file_notes)
    return found, notes


def _ref_id(ref: str | dict) -> str:
    if isinstance(ref, str):
        return ref.strip()
    if isinstance(ref, dict):
        return str(ref.get("id") or "").strip()
    return ""


def keyref_crosscheck(keyref_dir: Path, merged: list) -> dict:
    """KeyRef/*.md의 id와 병합 결과 id를 대조 (F60 ③)."""
    kr_ids: set[str] = set()
    for md in keyref_dir.glob("*.md"):
        m = _KEYREF_ID_RE.search(md.read_text(encoding="utf-8"))
        if m:
            kr_ids.add(m.group(1))
    merged_ids = {_ref_id(r) for r in merged} - {""}
    return {
        "keyref_ids": len(kr_ids),
        "merged_ids": len(merged_ids),
        "missing_in_merge": sorted(kr_ids - merged_ids),
    }


def merge_research(input_dir: Path, keyref_dir: Path | None = None) -> dict:
    """모든 research_round_*.json 병합. 경고는 결과의 warnings에 모은다."""
    rounds, warnings = load_round_files(input_dir)
    if not rounds:
        raise FileNotFoundError(format_error(
            "TECHDOC-E021",
            f"No research_round_*.json found in {input_dir}",
            "researcher subagent 출력 확인"
        ))

    all_refs: list = []
    per_round: dict[str, int] = {}
    empty_files: list[str] = []
    for name, refs in rounds:
        per_round[name] = len(refs)
        if not refs:
            empty_files.append(name)
        all_refs.extend(refs)

    deduped, removed = dedupe_refs(all_refs)

    result = {
        "schema_version": "0.1.0",
        "source_files": list(per_round.keys()),
        "per_file_count": per_round,
        "total_before_dedup": len(all_refs),
        "total_after_dedup": len(deduped),
        "removed_duplicates": removed,
        "empty_files": empty_files,
        "warnings": warnings,
        "refs": deduped,
    }
    if keyref_dir is not None:
        cc = keyref_crosscheck(keyref_dir, deduped)
        result["keyref_crosscheck"] = cc
        if cc["missing_in_merge"]:
            warnings.append(
                f"KeyRef {len(cc['missing_in_merge'])}건이 병합 결과에 없음: "
                + ", ".join(cc["missing_in_merge"][:10])
            )
    return result


def main() -> int:
    """종료 코드: 0 정상 · 1 라운드 파일 없음 · 3 경고(빈 파일·꼴 불명·KeyRef 대조 누락)."""
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Merge 3 researcher parallel outputs")
    ap.add_argument("-i", "--input", default="./output", help="research_round_*.json 디렉토리")
    ap.add_argument("-o", "--output", default="./output/merged_research.json", help="병합 결과 파일")
    ap.add_argument("--keyref", default=None, help="KeyRef 디렉토리 (id 대조, 선택)")
    args = ap.parse_args()

    try:
        result = merge_research(
            Path(args.input), Path(args.keyref) if args.keyref else None
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {out_path}")
    print(f"  source: {result['source_files']}")
    print(f"  before: {result['total_before_dedup']}, after: {result['total_after_dedup']}, "
          f"removed: {result['removed_duplicates']}")
    for w in result["warnings"]:
        print(f"  [WARN] {w}", file=sys.stderr)
    if result["empty_files"] or result["warnings"]:
        print(f"  경고 {len(result['warnings'])}건 · 빈 라운드 {result['empty_files']} → 종료 코드 3",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
