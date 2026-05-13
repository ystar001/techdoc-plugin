"""Plan A — self_check 필드 정합화 회귀 테스트.

F2: validation·structure_check 필드가 카드 사이즈에 따라 비대칭이던 문제
F4: 자체 검증 메모가 본문 텍스트에 인라인으로 부착되던 문제
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "cards"

# F4가 본문에 남기던 메모의 시그너처. 본문에 이 패턴이 있으면 F4 잔존.
# 콜론은 ASCII(`:`)·전각(`：`) 모두 매치.
INLINE_SELF_DIAGNOSIS_PATTERNS = [
    r"AI 추정 표현 \d+%",
    r"자가진단[:：]",
    r"\[REF-xxx\] \d+건 이상 확인",
    r"7블록 모두 작성",
    r"KeyRef 직접 인용\.",
]


def _iter_card_body_texts(card: dict) -> list[str]:
    """카드의 모든 body 텍스트를 평탄화. F1(키 변형 4종)을 잠정 처리."""
    out: list[str] = []
    sections = card.get("sections", {})
    for sec in sections.values():
        for key in ("body", "narrative", "content"):
            if isinstance(sec.get(key), str):
                out.append(sec[key])
        for block in sec.get("blocks", []) or []:
            if isinstance(block, dict) and isinstance(block.get("body"), str):
                out.append(block["body"])
    blocks = card.get("blocks", {})
    if isinstance(blocks, dict):
        for v in blocks.values():
            if isinstance(v, str):
                out.append(v)
    return out


def test_f4_fixture_has_inline_self_diagnosis():
    """F4 fixture는 본문 인라인 자체 검증 메모를 가지고 있어야 한다 (회귀의 출발점)."""
    card = json.loads((FIXTURES / "F4_inline_self_diagnosis.json").read_text("utf-8"))
    bodies = _iter_card_body_texts(card)
    assert bodies, "fixture에 본문 텍스트가 있어야 함"
    matches = [
        p for p in INLINE_SELF_DIAGNOSIS_PATTERNS
        for body in bodies if re.search(p, body)
    ]
    assert matches, "F4 fixture가 인라인 자체 검증 패턴을 포함해야 함"


from techdoc_core.schemas import SelfCheckResult


def test_self_check_result_defaults_to_optional():
    """SelfCheckResult는 모든 카드 사이즈에 동일하게 적용 — 모든 필드 optional."""
    result = SelfCheckResult()
    assert result.blocks_filled is None
    assert result.refs_count is None
    assert result.min_length_ok is None
    assert result.ai_inference_below_threshold is None
    assert result.no_unverified_markers is None
    assert result.notes == []


def test_self_check_result_full_population():
    """모든 검증 항목을 명시한 정상 케이스."""
    result = SelfCheckResult(
        blocks_filled=True,
        refs_count=6,
        min_length_ok=True,
        ai_inference_below_threshold=True,
        no_unverified_markers=True,
        notes=["기준 충족"],
    )
    assert result.refs_count == 6
    assert "기준 충족" in result.notes


def test_self_check_result_rejects_unknown_field():
    """schema 외 필드는 거부 (pydantic strict)."""
    with pytest.raises(Exception):
        SelfCheckResult(unexpected_key="value")
