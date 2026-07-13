"""용어 한글화 토큰맵 — render 시 영문 sec제목·jargon을 프로젝트 용어로 치환 (F29).

writer가 남긴 영문 용어를 render 단계에서 프로젝트별 토큰맵(english→korean)으로
한글화한다(F12 섹션 키 한글 매핑·F16 표기 표준의 연장). 결정론적·LLM 0회.
"""
from __future__ import annotations

import re


def localize_terms(text: str, term_map: dict[str, str]) -> str:
    """text의 영문 용어를 term_map(원문→치환) 으로 치환.

    - 긴 용어 우선(부분 문자열 오치환 방지: 'State Vector Schema' → 'State Vector'보다 먼저).
    - ascii 경계에서만 매칭('cat'이 'category'를 건드리지 않음).
    """
    if not text or not term_map:
        return text
    for term in sorted(term_map, key=len, reverse=True):
        if not term:
            continue
        repl = term_map[term]
        pat = re.escape(term)
        if term[:1].isalnum():
            pat = r"\b" + pat
        if term[-1:].isalnum():
            pat = pat + r"\b"
        text = re.sub(pat, lambda _m, r=repl: r, text)
    return text
