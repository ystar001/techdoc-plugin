"""카드 시각 필드 캡션 번호 게이트 — V89 (v1.11-c 신규, F82 ③).

원리: 카드 `diagrams[]`·`figures[]`(F22)의 그림 번호는 렌더 산출물에 **캡션으로만** 실린다. 작성기가
번호를 `id`에만 넣고 캡션에 적지 않으면(F82 — 52개 중 48개) 렌더에서 번호가 사라져 본문의
「그림 1-2」 호출이 갈 곳을 잃는다.

- 대상: 카드의 `diagrams`·`figures` 항목 중 `id`가 비지 않은 것(번호를 매기려 한 항목).
- 지적: 그 항목의 `caption`에 도표 종류 + 번호(「그림 1-2」·「표 II.8-1」·「그림 A.1-3」 — 종류 뒤 토큰에
  숫자가 하나 이상)가 없으면 경고 하나. 번호 꼴은 묻지 않는다(번호 정합은 V12·PLG-CQ 캡션 게이트 몫).
- 위치: `<카드>:<필드>[<순번>]` — 카드 면제(`gates.exempt`)가 그대로 먹는다.
"""
from __future__ import annotations

import re

from techdoc_core.qc.model import DocModel
from techdoc_core.qc.numbering import CAPTION_KINDS
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

FIELDS = ("diagrams", "figures")
_NUMBERED = re.compile(rf"{CAPTION_KINDS}\s*[\dA-Za-z][0-9A-Za-z.\-]*")


def caption_has_number(caption) -> bool:
    """캡션에 「종류 + 숫자가 든 번호」가 있나 — 굵게 표시는 걷고 본다."""
    if not isinstance(caption, str):
        return False
    text = caption.replace("**", "")
    return any(re.search(r"\d", m.group(0)) for m in _NUMBERED.finditer(text))


def _items(card: dict):
    for field in FIELDS:
        items = card.get(field)
        for i, it in enumerate(items if isinstance(items, list) else [], 1):
            if isinstance(it, dict):
                yield field, i, it


def _card(field: str, **item) -> dict:
    return {"sections": {"s1": {"body": "본문"}}, field: [item]}


@gate("V89", samples=[
    Sample(sample_model(cards={"1.1": _card("diagrams", id="그림 1-2", caption="흐름")}), 1),
    Sample(sample_model(cards={"1.1": _card("figures", id="f1", caption="그림 1-2 흐름")}), 0),
])
def v89(model: DocModel) -> GateOutput:
    n = 0
    items: list[Finding] = []
    for cid, card in model.cards.items():
        for field, i, it in _items(card):
            ident = it.get("id")
            if not (isinstance(ident, str) and ident.strip()):
                continue
            n += 1
            cap = it.get("caption")
            if not caption_has_number(cap):
                items.append(Finding(f"{cid}:{field}[{i}]",
                                     f"id 「{ident.strip()}」에만 번호가 있고 캡션 「{cap or ''}」에 "
                                     "그림·표 번호가 없음 — 렌더에서 번호가 사라짐, 캡션 앞에 번호를"))
    return GateOutput(n, items)
