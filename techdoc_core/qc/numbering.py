"""번호 꼴 — 절·표제·캡션·별첨 번호를 설정(`numbering.section`)에 따라 (v1.11-b, 설계 D3.2·F82).

시리즈 게이트는 아라비아 번호(`3.2`)를 가정했다. 로마 숫자로 부를 나눈 문서(`II.6.3`)나 문자가
가운데 오는 번호(`2.A.7`)는 표제를 못 알아보거나 절 참조를 끊어진 참조로 잘못 잡는다.

이식한 게이트는 **아라비아일 때 원본 정규식을 그대로 쓰고**, 다른 꼴일 때만 이 모듈의 조각을 쓴다
(차분 회귀에서 원본과 같은 건수를 지키기 위해).
"""
from __future__ import annotations

import re

SECTION_NUM = {
    "arabic": r"\d+(?:\.\d+)+",
    "roman": r"[IVX]+(?:\.\d+)+",
    "letter_middle": r"\d+\.[A-Z]\.\d+(?:\.\d+)*",
}
_HEAD_NUM = {
    "arabic": r"[0-9][0-9A-Za-z.\-]*",  # 원본 prose_gates.HEAD
    "roman": r"(?:[IVX]+|[0-9])[0-9A-Za-z.\-]*",
    "letter_middle": r"[0-9][0-9A-Za-z.\-]*",
}
_CAPTION_NUM = {
    "arabic": r"\d+(?:\.\d+)*-\d+",
    "roman": r"(?:[IVX]+|\d+)(?:\.\d+)*-\d+",
    "letter_middle": r"\d+(?:\.[A-Z0-9]+)*-\d+",
}


def _style(style: str | None) -> str:
    return style if style in SECTION_NUM else "arabic"


def section_num(style: str | None) -> str:
    """절 번호 정규식 조각(묶음 없음)."""
    return SECTION_NUM[_style(style)]


def section_ref_re(style: str | None) -> re.Pattern:
    """본문 속 절 참조 「3.2절」·「II.6.3절」 — 1번 묶음이 번호."""
    return re.compile(rf"(?<![\w.])({section_num(style)})\s*절")


def head_re(style: str | None) -> re.Pattern:
    """`##`~`####` 표제 — 묶음 (레벨 #들, 번호, 표제 글)."""
    return re.compile(rf"^(#{{2,4}})\s+({_HEAD_NUM[_style(style)]})\s+(.+?)\s*$")


def caption_num_re(style: str | None) -> re.Pattern:
    """캡션 번호 「3-2」·「II.8-1」 (F82)."""
    return re.compile(_CAPTION_NUM[_style(style)])


_LEAD = {"arabic": r"[0-9]+", "roman": r"[IVX]+", "letter_middle": r"[0-9]+"}
_SECTION_FILE = {
    "arabic": r"^(\d+)\.(\d+)([^.\s]*)\.\s",  # 원본 prose_gates._SEC_FILE
    "roman": r"^([IVX]+)\.(\d+)([^.\s]*)\.\s",
    "letter_middle": r"^(\d+)\.([A-Z0-9]+(?:\.\d+)*)([^.\s]*)\.\s",
}


def lead_num(style: str | None) -> str:
    """번호의 첫 마디(부·장) 조각 — arabic `[0-9]+` · roman `[IVX]+`."""
    return _LEAD[_style(style)]


def head_num(style: str | None) -> str:
    """표제 번호 조각(묶음 없음) — arabic은 원본 prose_gates.HEAD의 번호 꼴."""
    return _HEAD_NUM[_style(style)]


def section_file_re(style: str | None) -> re.Pattern:
    """렌더 트리의 절 파일 이름 「3.1. 제목.md」·「II.6. 제목.md」."""
    return re.compile(_SECTION_FILE[_style(style)])


def appendix_letters(extra: dict | None) -> str:
    """별첨 문자 범위(정규식 문자 집합 안쪽) — 기본 A-Z, `extra.structure.appendix_letters`로."""
    return ((extra or {}).get("structure") or {}).get("appendix_letters") or "A-Z"
