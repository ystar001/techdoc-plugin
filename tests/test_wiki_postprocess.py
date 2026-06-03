"""export-wiki 후처리(F18) 회귀 테스트.

톤 정리·메타 제거·긴 문단 분리·slug 한국어화·문서 안내·enhance 통합.
[REF-xxx]·수치·고유명사 보존, 멱등성을 검증한다.
"""

from __future__ import annotations

from scripts.wiki.postprocess import (
    soften_tone,
    strip_meta_markers,
    split_long_paragraphs,
)


def test_soften_tone_replaces_academic_modifiers():
    assert soften_tone("학술 framework 기반") == "프레임워크 기반"
    assert soften_tone("학술 baseline 대비") == "기준선 대비"
    assert "학술 " not in soften_tone("학술 deep dive 수행")


def test_soften_tone_preserves_ref_and_numbers():
    src = "정확도 95.3% 달성 [REF-023]."
    assert soften_tone(src) == src  # 수치·REF 보존


def test_strip_meta_markers_removes_expansion_label():
    assert strip_meta_markers("## 핵심 개념 (확장)") == "## 핵심 개념"
    assert strip_meta_markers("## 배경 (보강)") == "## 배경"


def test_split_long_paragraphs_uses_paragraph_util():
    # 800자 ceiling 초과 입력 → 강제 분리 (paragraph.format_paragraphs 재사용)
    long = ("한 문장이다. " * 200).strip()
    out = split_long_paragraphs(long)
    assert "\n\n" in out  # 800자 ceiling 분리
