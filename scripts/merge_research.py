"""3 researcher 병렬 출력 합병·dedup.

researcher subagent A/B/C가 각각 생성한 research_round_A.json, research_round_B.json,
research_round_C.json을 하나로 병합하고 URL/제목 유사도 dedup.

사용법:
    python -m scripts.merge_research --input ./output/ -o ./output/merged_research.json
"""

from __future__ import annotations

import argparse
import json
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
    kept: list[dict] = []
    removed = 0

    for ref in all_refs:
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
        kept.append(ref)

    return kept, removed


def load_round_files(input_dir: Path) -> list[tuple[str, list[dict]]]:
    """input_dir에서 research_round_*.json 파일들 로드."""
    patterns = ("research_round_A.json", "research_round_B.json", "research_round_C.json",
                "research_round_*.json")
    found: list[tuple[str, list[dict]]] = []
    seen: set[Path] = set()

    for pat in patterns:
        for p in input_dir.glob(pat):
            if p in seen:
                continue
            seen.add(p)
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"  [WARN] {p.name}: JSON decode failed — {e}", file=sys.stderr)
                continue
            refs = data.get("refs_found") or data.get("refs") or []
            found.append((p.name, refs))

    return found


def merge_research(input_dir: Path) -> dict:
    """모든 research_round_*.json 병합."""
    rounds = load_round_files(input_dir)
    if not rounds:
        raise FileNotFoundError(format_error(
            "TECHDOC-E021",
            f"No research_round_*.json found in {input_dir}",
            "researcher subagent 출력 확인"
        ))

    all_refs: list[dict] = []
    per_round: dict[str, int] = {}
    for name, refs in rounds:
        per_round[name] = len(refs)
        all_refs.extend(refs)

    deduped, removed = dedupe_refs(all_refs)

    return {
        "schema_version": "0.1.0",
        "source_files": list(per_round.keys()),
        "per_file_count": per_round,
        "total_before_dedup": len(all_refs),
        "total_after_dedup": len(deduped),
        "removed_duplicates": removed,
        "refs": deduped,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge 3 researcher parallel outputs")
    ap.add_argument("-i", "--input", default="./output", help="research_round_*.json 디렉토리")
    ap.add_argument("-o", "--output", default="./output/merged_research.json", help="병합 결과 파일")
    args = ap.parse_args()

    try:
        result = merge_research(Path(args.input))
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {out_path}")
    print(f"  source: {result['source_files']}")
    print(f"  before: {result['total_before_dedup']}, after: {result['total_after_dedup']}, removed: {result['removed_duplicates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
