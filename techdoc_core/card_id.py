"""카드 ID 파서 — 구분자로 분해한 뒤 마디의 역할을 추론한다 (v1.10.2 — F58·F70·F73·F79·F81).

「알려진 패턴 열거」는 문서마다 별첨 문자·번호 꼴이 달라 다섯 번 재발했다(A~J 접두,
하이픈 유무, `2.A.7`). 여기서는 `.`으로 나눈 마디를 보고 앞붙이(front)·본문(body)·
별첨(appendix)·분할 표지(L/XL)를 가린다. `verify_cards`와 `check_quality`가 공유한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["front", "body", "appendix", "unknown"]

_SPLIT_RE = re.compile(r"^(?:L|XL)\d+$")
_APPENDIX_HEAD_RE = re.compile(r"^[A-Z]+-?\d*$")
_BODY_SEG_RE = re.compile(r"^(?:\d+|[A-Z])$")
_ROMAN_RE = re.compile(r"^[IVXLC]+$")


@dataclass(frozen=True)
class CardId:
    kind: Kind
    split: str | None
    segments: tuple[str, ...]


def parse_card_id_parts(stem: str, numbering: dict | None = None) -> CardId:
    """카드 파일 stem(`_card` 꼬리 허용) → CardId.

    `numbering.section == "roman"`이면 첫 마디가 로마 숫자인 ID(`I.1`·`II.6.L2`)를 본문으로 본다.
    기본값(None·arabic)에서는 지금처럼 접두 문자를 별첨으로 본다.
    """
    s = stem.removesuffix("_card").strip()
    segs = [x for x in s.split(".") if x]
    split: str | None = None
    if segs and _SPLIT_RE.match(segs[-1]):
        split = segs.pop()
    elif segs and segs[-1] == "S":
        segs.pop()
    if not segs:
        return CardId("unknown", split, ())
    head, rest = segs[0], segs[1:]
    seg_t = tuple(segs)
    if head == "0" and rest and all(x.isdigit() for x in rest):
        return CardId("front", split, seg_t)
    roman_body = (numbering or {}).get("section") == "roman" and _ROMAN_RE.match(head)
    if (head.isdigit() or roman_body) and all(_BODY_SEG_RE.match(x) for x in rest):
        return CardId("body", split, seg_t)
    if _APPENDIX_HEAD_RE.match(head) and all(x.isdigit() for x in rest):
        return CardId("appendix", split, seg_t)
    return CardId("unknown", split, seg_t)


def size_id(cid: CardId) -> str:
    """분량 등급: P0(앞붙이) · L<n>/XL<n>(분할) · S(본문·별첨) · ?(인식 실패)."""
    if cid.kind == "front":
        return "P0"
    if cid.kind == "unknown":
        return "?"
    if cid.split:
        return cid.split
    return "S"
