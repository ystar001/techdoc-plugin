"""TOC (목차) 파일 파싱 → draft_outline.json 생성.

사용법:
    python -m scripts.parse_toc --toc ./toc.txt --title "보고서 제목" -o ./output/

목차 파일 형식:
    1장. 인프라 기술
    ● 정의
    ● 역할

    1.1 관개 자동화
    ● 점적관수 시스템
    ● AI 물수요 예측
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from techdoc_core.constants import ANALYSIS_TAGS, DEFAULT_ANALYSIS_TAG
from techdoc_core.models import Outline, Section
from techdoc_core.schemas import format_error

ITEM_MARKERS = ("●", "-", "*", "•")
META_BLOCK_PATTERNS = (
    r"^\s*\[.*\]\s*$",  # [작성 지침] 같은 대괄호 메타
)

# 섹션 ID: 영숫자 prefix(R·G1·AP·A-1·1.1) 허용. ID 뒤 구분자(장/절·마침표·공백)를
# 요구해 "5G/LTE" 같은 제목이 ID로 오인되는 것을 막는다.
SECTION_ID_RE = re.compile(
    r"^([A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*)\s*(?:장|절)?\.?\s+(.+)$"
)

# TOC 표의 Sizing/등급 칼럼 값을 estimated_length(short|medium|long)로 매핑.
# estimated_length는 3단계뿐이므로 XL은 long으로 흡수한다.
SIZING_TO_LENGTH = {
    "S": "short", "M": "medium", "L": "long", "XL": "long",
    "소": "short", "중": "medium", "대": "long",
}


def map_sizing(value: str) -> str | None:
    """Sizing 칼럼 값 → estimated_length. 미인식 시 None."""
    return SIZING_TO_LENGTH.get(value.strip().upper())


TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?\s*$")
PURE_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*$")


def split_table_row(line: str) -> list[str]:
    """'| a | b | c |' → ['a', 'b', 'c']."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator_row(line: str) -> bool:
    """'|---|:--:|' 같은 표 구분행인지."""
    return bool(TABLE_SEP_RE.match(line))


def is_pure_id(cell: str) -> bool:
    """셀 전체가 ID 토큰(영숫자 prefix, 공백 없음)인지."""
    return bool(PURE_ID_RE.match(cell.strip()))


def parse_toc_file(file_path: Path | str) -> list[dict]:
    """TOC 텍스트 파일 → 섹션 리스트 반환.

    Returns:
        [{"id": "1.1", "title": "...", "subtopics": [...]}, ...]
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(format_error("TECHDOC-E010", f"TOC file not found: {file_path}"))

    text = path.read_text(encoding="utf-8")
    sections: list[dict] = []
    current: dict | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        # 메타 블록 스킵
        if any(re.match(pat, line) for pat in META_BLOCK_PATTERNS):
            continue

        stripped = line.lstrip()

        # 하위 항목 (●, -, *, •로 시작)
        if stripped[:1] in ITEM_MARKERS:
            if current is None:
                continue
            subtopic = stripped[1:].strip().lstrip(".")
            if subtopic:
                current["subtopics"].append(subtopic)
            continue

        # 섹션 라인 - "1장. ..." / "1.1 ..." / "G1 ..." / "A-1 ..."
        m = SECTION_ID_RE.match(stripped)
        if m:
            if current is not None:
                sections.append(current)
            section_id = m.group(1).rstrip(".")
            title = m.group(2).strip()
            current = {"id": section_id, "title": title, "subtopics": []}
        else:
            # ID 없는 최상위 제목 — 일련번호 자동 부여
            if current is not None:
                sections.append(current)
            section_id = str(len(sections) + 1)
            current = {"id": section_id, "title": stripped, "subtopics": []}

    if current is not None:
        sections.append(current)

    if not sections:
        raise ValueError(format_error("TECHDOC-E010", "TOC file produced zero sections", "파일 내용 확인"))

    return sections


def assign_analysis_tag(title: str, subtopics: list[str]) -> list[str]:
    """제목·하위항목 키워드에서 분석 태그 자동 매칭 (우선순위순 첫 일치)."""
    haystack = title + " " + " ".join(subtopics)
    for tag_def in ANALYSIS_TAGS:
        for kw in tag_def["keywords"]:
            if kw in haystack:
                return [tag_def["tag"]]
    return [DEFAULT_ANALYSIS_TAG]


def estimate_length(subtopic_count: int) -> str:
    """하위 항목 수 기반 예상 길이 추정."""
    if subtopic_count >= 5:
        return "long"
    if subtopic_count >= 3:
        return "medium"
    return "short"


def build_outline(title: str, parsed_sections: list[dict]) -> Outline:
    """파싱된 섹션 리스트 → Outline 객체."""
    sections = []
    for p in parsed_sections:
        sections.append(
            Section(
                id=p["id"],
                title=p["title"],
                subtopics=p["subtopics"],
                analysis_tags=assign_analysis_tag(p["title"], p["subtopics"]),
                estimated_length=estimate_length(len(p["subtopics"])),
            )
        )
    return Outline(title=title, sections=sections)


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse TOC file into draft_outline.json")
    ap.add_argument("--toc", required=True, help="TOC 파일 경로")
    ap.add_argument("--title", required=True, help="문서 제목")
    ap.add_argument("-o", "--output", default="./output", help="출력 디렉토리")
    args = ap.parse_args()

    try:
        sections = parse_toc_file(args.toc)
        outline = build_outline(args.title, sections)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "draft_outline.json"
    outline.save(out_path)
    print(f"OK: {out_path} ({len(outline.sections)} sections)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
