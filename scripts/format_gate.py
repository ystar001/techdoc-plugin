"""서식 게이트 — self_model 카드 본문 markdown 형식 품질 측정 (LLM 0회·결정론적).

verify_rewrite.py(openfieldtech) 게이트 로직 이식. 스키마 무지: 추출된 텍스트만 받는다.
전부 WARNING 기본, ``strict`` 시 "렌더가 깨지는 구조 결함 + REF 회귀"만 FAIL로 승격.
``markdown`` 모듈은 optional(미설치 시 render_nesting만 생략).
"""

from __future__ import annotations

import re

REF_RE = re.compile(r"REF-\d{3,4}")
NUM_RE = re.compile(r"\d[\d,.]*")
INLINE_ROMAN = re.compile(r"\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)")
INLINE_ALPHA = re.compile(r"\([a-z]-\d\)")
TOP_PLAIN = re.compile(r"(?:^|[\s.])\([a-h]\)\s")
LIST_LINE = re.compile(r"^( *)([-*]|\d+\.)\s")
NONBULLET_INDENT = re.compile(r"^ {2,3}(?![-*] |\d+\. )\S", re.M)
REDUNDANT_SUMMARY = re.compile(r"종합하면|정리하면|종합적으로")

# --strict 에서 FAIL로 승격되는 "렌더가 깨지는 구조 결함 + REF 회귀"
STRICT_FAIL_METRICS = {
    "inline_hierarchy",
    "top_plain_label",
    "nonbullet_indent",
    "flatten_risk_indent",
    "ref_loss",
}


def analyze_lists(text: str) -> tuple[int, int]:
    """리스트 줄 들여쓰기 분석 → (4배수 중첩 수, 4배수 아님=평탄화 위험 수)."""
    indent4 = bad = 0
    for line in text.split("\n"):
        m = LIST_LINE.match(line)
        if not m:
            continue
        n = len(m.group(1))
        if n == 0:
            continue
        if n % 4 == 0:
            indent4 += 1
        else:
            bad += 1
    return indent4, bad


def count_nonbullet_indent(text: str) -> int:
    """불릿 아닌 2·3칸 들여쓰기 텍스트 줄 수 (설명을 리스트에 욱여넣은 흔적)."""
    return len(NONBULLET_INDENT.findall(text))
