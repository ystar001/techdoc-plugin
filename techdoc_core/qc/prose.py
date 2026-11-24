"""산문 게이트 공용 헬퍼 — 시리즈 prose_gates의 상수·문단/절 분해를 옮김 (v1.11-b).

코드 펜스 · 표 행 · 인용구 · 표제 · 캡션 정의 줄은 산문이 아니다. md는 손으로 줄을 바꿔 두므로
문장 길이 같은 검사는 줄이 아니라 **문단** 단위로 본다(원본 주석 그대로의 이유).
표제 정규식만 번호 꼴(`numbering.head_re`)에 따른다. 아라비아일 때 원본과 같다.
"""
from __future__ import annotations

import re
from collections.abc import Iterator

from techdoc_core.qc.numbering import CAPTION_KINDS, CAPTION_TOKEN, head_re

FENCE = re.compile(r"^\s*```")
SKIP_LINE = re.compile(r"^\s*(?:\||#{1,6}\s|>|!!!|\$\$|[-*+]\s*\||<div\b)")
CAP_DEF = re.compile(
    r"^\s*(?:\*\*(?:그림|표|차트|사진|다이어그램)\s|(?:그림|표|차트|사진|다이어그램)\s"
    r"[\dA-Za-z][0-9A-Za-z.\-]*\.(?:\s|$))")
CAP_PLAIN = CAPTION_KINDS + r"\s" + CAPTION_TOKEN + r"\.(?=\s|$)"  # 번호 조각은 numbering(F82)
CAP_LINE_ANY = re.compile(
    r"^\s*(?:\*\*(?:그림|표|차트|사진|다이어그램)\s*[\dA-Za-z][\w.\-]*\.?\*\*|" + CAP_PLAIN + ")")
SENT = re.compile(r"(?<=[가-힣\)\]」』\*%\d℃`])\.[」』\)\*”`]*\s+")
BOLD = re.compile(r"\*\*[^*]+?\*\*")
RUNIN = re.compile(r"^\*\*(?![^*]{0,14}(?:다|까|요|죠|냐)\.?\*\*)[^*]{1,14}\.?\*\*")
MARKUP = re.compile(r"\*\*|\[REF-\d+\]|`|\]\([^)]*\)|[\[\]]")
# 약어 영문 원어 「(SOP, Standard Operating Procedure)」는 문장 길이에 세지 않는다
EN_GLOSS = re.compile(r"(?<=[A-Za-z0-9]), [A-Z][^()가-힣\n]*(?=\))"
                      r"|(?<=[A-Za-z0-9])\([A-Z][^()가-힣\n]*\)(?=:)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
CALC_BOX = re.compile(r"^\s*!!!\s+수식\b")
HEAD = head_re("arabic")


def is_cap_line(s: str) -> bool:
    """캡션 정의줄인가 — 굵은 옛 꼴과 굵게 없는 정본 꼴 모두."""
    return bool(CAP_LINE_ANY.match(s))


def strip_en_gloss(s: str) -> str:
    return EN_GLOSS.sub("", s)


def prose_lines(text: str) -> Iterator[tuple[int, str]]:
    """(줄번호, 줄) — 산문만. 펜스·표·표제·인용구·캡션 정의 제외."""
    infence = False
    for i, ln in enumerate(text.split("\n"), 1):
        if FENCE.match(ln):
            infence = not infence
            continue
        if infence or not ln.strip():
            continue
        if SKIP_LINE.match(ln) or CAP_DEF.match(ln):
            continue
        yield i, ln


def paragraphs(text: str, style: str | None = None) -> Iterator[tuple[int, str, str]]:
    """(시작줄, 한 줄로 이은 문단, 속한 표제 글) — 산문 문단만.

    목록 항목은 저마다 한 문단, `!!! 수식` 상자 안(들여 쓴 줄)은 산문이 아니다.
    """
    head_rx = head_re(style)
    infence = False
    buf: list[str] = []
    start = 0
    head = ""
    incalc = False
    for i, ln in enumerate(text.split("\n"), 1):
        if CALC_BOX.match(ln):
            incalc = True
        elif incalc and (not ln.strip() or ln.startswith("    ")):
            if buf:
                yield start, " ".join(buf), head
                buf = []
            continue
        else:
            incalc = False
        if FENCE.match(ln):
            infence = not infence
            if buf:
                yield start, " ".join(buf), head
                buf = []
            continue
        m = head_rx.match(ln)
        if m:
            if buf:
                yield start, " ".join(buf), head
                buf = []
            head = m.group(3)
            continue
        stripped = ln.strip()
        if infence or not stripped or SKIP_LINE.match(ln) or CAP_DEF.match(ln):
            if buf:
                yield start, " ".join(buf), head
                buf = []
            continue
        if LIST_ITEM.match(ln) and buf:
            yield start, " ".join(buf), head
            buf = []
        if not buf:
            start = i
        buf.append(stripped)
    if buf:
        yield start, " ".join(buf), head


def table_before(text: str, start_line: int) -> bool:
    """그 문단 바로 앞(표제를 넘지 않는 범위)에 표가 있는가."""
    lines = text.split("\n")
    j = start_line - 2
    while j >= 0 and not lines[j].startswith("|"):
        if lines[j].startswith("#") or lines[j].strip().startswith("```"):
            return False
        j -= 1
    return j >= 0


def sections(text: str, style: str | None = None) -> Iterator[tuple[int, str, str, int, str]]:
    """(레벨, 번호, 표제, 시작줄, 본문) — `##`/`###`/`####` 단위."""
    head_rx = head_re(style)
    lines = text.split("\n")
    marks = [(i, m) for i, ln in enumerate(lines) if (m := head_rx.match(ln))]
    for k, (i, m) in enumerate(marks):
        j = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        yield len(m.group(1)), m.group(2), m.group(3), i + 1, "\n".join(lines[i:j])
