"""export-wiki 후처리 — 톤·메타·문단 정리 (F18). LLM 0회·결정론·멱등.

[REF-xxx]·수치·고유명사는 보존한다(치환 사전은 일반 수식어 한정).
"""
from __future__ import annotations

import re

from techdoc_core.renderers.paragraph import format_paragraphs

# "학술 X" 과잉 수식어 → 일반어 (F18-2)
_TONE_REPLACEMENTS = {
    "학술 framework": "프레임워크",
    "학술 baseline": "기준선",
    "학술 deep dive": "심층 분석",
    "학술 정초 논문": "정초 논문",
    "학술 시리즈": "시리즈",
    "학술 정의": "정의",
    "학술 분담": "분담",
}
# 남은 단독 "학술 " 수식어(고유명사 앞 제외)는 보수적으로 제거
_BARE_ACADEMIC_RE = re.compile(r"학술\s+(?=[A-Za-z가-힣])")
_META_LABEL_RE = re.compile(r"\s*\((?:확장|보강|정리|편집)\)\s*$")


def soften_tone(text: str) -> str:
    """'학술' 과잉 수식어를 일반어로. REF·수치는 사전에 없으므로 보존."""
    for k, v in _TONE_REPLACEMENTS.items():
        text = text.replace(k, v)
    return _BARE_ACADEMIC_RE.sub("", text)


def strip_meta_markers(line: str) -> str:
    """헤더 끝의 메타 표시 '(확장)'·'(보강)' 제거(헤더 자체 보존)."""
    return _META_LABEL_RE.sub("", line)


def split_long_paragraphs(text: str) -> str:
    """긴 문단 분리 — Plan I paragraph.format_paragraphs 재사용(800자 ceiling)."""
    return format_paragraphs(text)
