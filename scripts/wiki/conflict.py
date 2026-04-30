"""핵심 사실(연도·수치·기관) 추출 + 충돌 감지.

LLM 호출 없이 정규식·휴리스틱 기반.
"""

from __future__ import annotations

import re

_YEAR_PATTERN = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?[%개건명년월]?")
_ORG_KO = re.compile(r"[가-힣]+(?:연구원|연구소|진흥청|대학교|대학|기업|공사|청|부|원)")
_ORG_EN = re.compile(r"[A-Z]{2,}(?:[A-Z][a-z]+)*")


def extract_facts(text: str) -> dict[str, set[str]]:
    """텍스트에서 연도·수치·기관 후보를 추출. 모두 set으로 반환."""
    return {
        "years": {m.group(0) for m in _YEAR_PATTERN.finditer(text)},
        "numbers": {m for m in _NUMBER_PATTERN.findall(text) if any(c.isdigit() for c in m)},
        "organizations": set(_ORG_KO.findall(text)) | set(_ORG_EN.findall(text)),
    }


def detect_conflicts(facts_a: dict[str, set], facts_b: dict[str, set]) -> list[dict]:
    """두 fact set 사이 카테고리별 차이 추출.

    같은 카테고리에서 양쪽 모두 비어있지 않은데 교집합이 비면 충돌로 본다.
    """
    conflicts: list[dict] = []
    category_labels = {"years": "연도", "numbers": "수치", "organizations": "기관"}
    for key, label in category_labels.items():
        a, b = facts_a.get(key, set()), facts_b.get(key, set())
        if a and b and not (a & b):
            conflicts.append(
                {
                    "category": label,
                    "values": [
                        *({"value": v, "source": "기존"} for v in sorted(a)),
                        *({"value": v, "source": "신규"} for v in sorted(b)),
                    ],
                }
            )
    return conflicts


def format_conflict_callout(conflicts: list[dict]) -> str:
    """충돌 목록 → 옵시디언 callout 마크다운."""
    if not conflicts:
        return ""
    lines = ["> [!warning] 정보 충돌 감지"]
    for c in conflicts:
        lines.append(f"> **{c['category']}**:")
        for v in c["values"]:
            lines.append(f"> - {v['source']}: {v['value']}")
    return "\n".join(lines) + "\n"
