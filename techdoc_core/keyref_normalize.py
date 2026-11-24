"""KeyRef frontmatter 정규화 — 근거를 조용히 버리지 않는다 (v1.10.2 — F61·F78).

researcher가 자연스럽게 쓰는 변형(`key_numbers`의 dict 원소, 「교차확인필요」 같은
reliability 표현, 숫자 문자열 연도)을 스키마가 받는 꼴로 바꾼다. 바꾼 사실은 note로
돌려주어 호출부가 보고한다. 원본 dict는 바꾸지 않는다. LLM 호출 0회.
"""
from __future__ import annotations

import copy
from typing import get_args

from techdoc_core.schemas import Category, Reliability

ALLOWED_RELIABILITY: tuple[str, ...] = get_args(Reliability)
ALLOWED_CATEGORY: tuple[str, ...] = get_args(Category)

# 자연어 표현 → 허용값. 허용값도 별칭도 아니면 「미확인」으로 강등 (버리지 않음).
RELIABILITY_ALIASES: dict[str, str] = {
    "교차확인필요": "단일출처",
    "교차 확인 필요": "단일출처",
    "확인필요": "미확인",
    "검증됨": "확인됨",
}
_DEMOTED = "미확인"

# category 자연어 표현 → 허용값. 모르는 값은 「기타」로 (버리지 않음). 실데이터 회귀 37건.
CATEGORY_ALIASES: dict[str, str] = {
    "정부보고서": "정부공공",
    "정부": "정부공공",
    "공공기관": "정부공공",
    "법령·고시": "정부공공",
    "법령": "정부공공",
    "고시": "정부공공",
    "논문": "학술",
    "학술논문": "학술",
    "기업": "기업R&D",
    "연구기관": "전문연구기관",
    "시장보고서": "산업시장",
    "언론": "뉴스",
}
_CATEGORY_FALLBACK = "기타"


def _stringify(item: object) -> str:
    if isinstance(item, dict):
        return "; ".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def normalize_keyref(data: dict) -> tuple[dict, list[str]]:
    """KeyRef frontmatter → (정규화된 사본, note 목록)."""
    out = copy.deepcopy(data)
    notes: list[str] = []

    kn = out.get("key_numbers")
    if isinstance(kn, list) and any(not isinstance(x, str) for x in kn):
        out["key_numbers"] = [x if isinstance(x, str) else _stringify(x) for x in kn]
        n = sum(1 for x in kn if not isinstance(x, str))
        notes.append(f"key_numbers 비문자열 {n}건을 문자열로 바꿈")

    if "key_numbers" in out and out["key_numbers"] is None:
        out["key_numbers"] = []
        notes.append("key_numbers가 비어 있음(None) → 빈 리스트")

    cat = out.get("category")
    if isinstance(cat, str) and cat not in ALLOWED_CATEGORY:
        if cat in CATEGORY_ALIASES:
            out["category"] = CATEGORY_ALIASES[cat]
            notes.append(f"category '{cat}' → '{out['category']}' (별칭)")
        else:
            out["category"] = _CATEGORY_FALLBACK
            notes.append(f"category '{cat}'는 허용값이 아님 → '{_CATEGORY_FALLBACK}'")

    rel = out.get("reliability")
    if isinstance(rel, str) and rel not in ALLOWED_RELIABILITY:
        if rel in RELIABILITY_ALIASES:
            out["reliability"] = RELIABILITY_ALIASES[rel]
            notes.append(f"reliability '{rel}' → '{out['reliability']}' (별칭)")
        else:
            out["reliability"] = _DEMOTED
            notes.append(f"reliability '{rel}'는 허용값이 아님 → '{_DEMOTED}'로 강등")

    year = out.get("year")
    if isinstance(year, str) and year.strip().isdigit():
        out["year"] = int(year.strip())
        notes.append(f"year '{year}' → {out['year']}")

    return out, notes
