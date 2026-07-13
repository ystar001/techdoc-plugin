"""parse_toc analysis_tags 폴백 편향 제거 테스트 (v1.9.0 워크스트림 G — F31).

미매칭 섹션을 모두 동일 DEFAULT_ANALYSIS_TAG로 강제하던 폴백이 코퍼스를
한 분석 렌즈로 과편향시켰다. 미매칭은 빈 리스트(무편향)로 둔다.
"""
from scripts.parse_toc import assign_analysis_tag
from techdoc_core.constants import ANALYSIS_TAGS


def test_no_keyword_match_returns_empty():
    """F31 — 어떤 태그 키워드도 없는 제목은 강제 기본 태그 없이 빈 리스트."""
    tags = assign_analysis_tag("zzxq nomatch 98765 lorem", [])
    assert tags == []


def test_keyword_match_still_assigns_tag():
    """회귀 — 실제 키워드가 든 제목은 해당 태그를 계속 부여."""
    first = ANALYSIS_TAGS[0]
    kw = first["keywords"][0]
    tags = assign_analysis_tag(f"섹션 {kw} 관련", [])
    assert tags == [first["tag"]]
