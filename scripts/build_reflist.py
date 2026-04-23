"""KeyRef/*.md → reference_list.json (카테고리 분류·비율 계산).

researcher subagent가 KeyRef/001_출처.md 형태로 저장한 YAML frontmatter를
수집하여 reference_list.json 생성. schema 검증은 pydantic KeyRefSchema 사용.

사용법:
    python -m scripts.build_reflist --keyref ./output/KeyRef/ -o ./output/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from pydantic import ValidationError

from techdoc_core.constants import get_ref_targets
from techdoc_core.schemas import KeyRefSchema, format_error


def extract_frontmatter(md_path: Path) -> dict | None:
    """마크다운 파일에서 YAML frontmatter 추출."""
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None


def validate_ref(data: dict, md_path: Path) -> KeyRefSchema | None:
    """KeyRef 스키마 검증. 실패 시 None 반환 + 경고."""
    try:
        return KeyRefSchema(**data)
    except ValidationError as e:
        print(f"  [WARN] {md_path.name}: schema validation failed — {e.error_count()} errors",
              file=sys.stderr)
        return None


def detect_english(ref: KeyRefSchema) -> bool:
    """영문 레퍼런스 판별 (제목·저자·URL 기반)."""
    sample = f"{ref.title} {' '.join(ref.authors)}"
    ascii_ratio = sum(1 for c in sample if c.isascii()) / max(1, len(sample))
    return ascii_ratio > 0.7


def is_international_org(ref: KeyRefSchema) -> bool:
    """국제기구 자료 여부."""
    intl_orgs = ("FAO", "OECD", "World Bank", "WHO", "UNESCO", "IMF", "EU Commission",
                 "UN ", "IPCC", "ILO", "ITU")
    haystack = f"{ref.source} {ref.institution} {ref.venue}".upper()
    return any(org.upper() in haystack for org in intl_orgs)


def is_academic(ref: KeyRefSchema) -> bool:
    """학술 자료 여부 (카테고리 + venue)."""
    if ref.category == "학술":
        return True
    academic_venues = ("IEEE", "ACM", "Springer", "Elsevier", "Nature", "Science",
                       "arXiv", "RISS", "DBpia", "KISS")
    return any(v in ref.venue for v in academic_venues)


def build_reflist(keyref_dir: Path, document_type: str = "기술보고서") -> dict:
    """KeyRef 디렉토리 전체 파싱 → reference_list dict."""
    if not keyref_dir.exists():
        raise FileNotFoundError(format_error("TECHDOC-E022", f"KeyRef dir not found: {keyref_dir}"))

    md_files = sorted(keyref_dir.glob("*.md"))
    if not md_files:
        raise ValueError(format_error("TECHDOC-E020", "No KeyRef files found"))

    refs: list[KeyRefSchema] = []
    skipped = 0
    for mp in md_files:
        fm = extract_frontmatter(mp)
        if fm is None:
            skipped += 1
            continue
        ref = validate_ref(fm, mp)
        if ref is None:
            skipped += 1
            continue
        refs.append(ref)

    if not refs:
        raise ValueError(format_error("TECHDOC-E022", "No valid KeyRef entries after validation"))

    # 카테고리 분포
    cat_count: dict[str, int] = defaultdict(int)
    for r in refs:
        cat_count[r.category] += 1

    targets = get_ref_targets(document_type)
    cat_targets = targets.get("category_targets", {})

    # 비율 계산
    total = len(refs)
    usable = sum(1 for r in refs if r.reliability in ("확인됨", "단일출처"))
    en_count = sum(1 for r in refs if detect_english(r))
    intl_count = sum(1 for r in refs if is_international_org(r))
    academic_count = sum(1 for r in refs if is_academic(r))

    # 섹션별 커버리지
    section_coverage: dict[str, int] = defaultdict(int)
    for r in refs:
        for sid in r.related_sections:
            section_coverage[sid] += 1

    # 카테고리별 coverage
    category_coverage = []
    for cat, count in sorted(cat_count.items()):
        category_coverage.append({
            "category": cat,
            "count": count,
            "target": cat_targets.get(cat, 0),
            "ratio": round(count / total, 3),
        })

    return {
        "schema_version": "0.1.0",
        "document_type": document_type,
        "total_refs": total,
        "usable_refs": usable,
        "en_ratio": round(en_count / total, 3),
        "intl_org_count": intl_count,
        "academic_count": academic_count,
        "category_coverage": category_coverage,
        "section_coverage": dict(section_coverage),
        "refs": [r.model_dump(mode="json") for r in refs],
        "_meta": {
            "source_files": len(md_files),
            "skipped": skipped,
            "targets": {
                "min_total": targets.get("min_total"),
                "per_section": targets.get("per_section"),
                "min_en_ratio": targets.get("min_en_ratio"),
                "min_intl_org": targets.get("min_intl_org"),
                "min_academic": targets.get("min_academic"),
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build reference_list.json from KeyRef/")
    ap.add_argument("--keyref", default="./output/KeyRef", help="KeyRef 디렉토리")
    ap.add_argument("--type", dest="document_type", default="기술보고서", help="문서 유형")
    ap.add_argument("-o", "--output", default="./output", help="출력 디렉토리")
    args = ap.parse_args()

    try:
        result = build_reflist(Path(args.keyref), args.document_type)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "reference_list.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {out_path}")
    print(f"  refs: {result['total_refs']} (usable={result['usable_refs']}, skipped={result['_meta']['skipped']})")
    print(f"  en_ratio: {result['en_ratio']}, intl={result['intl_org_count']}, academic={result['academic_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
