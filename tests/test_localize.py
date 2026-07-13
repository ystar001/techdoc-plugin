"""용어 한글화 토큰맵 테스트 (v1.9.0 워크스트림 — F29).

writer가 남긴 영문 sec제목·jargon을 render 시 프로젝트 토큰맵으로 한글화.
"""
from techdoc_core.localize import localize_terms


def test_localize_replaces_terms():
    m = {"State Vector": "상태벡터", "GDD": "생육도일(GDD)"}
    out = localize_terms("The State Vector uses GDD daily.", m)
    assert "상태벡터" in out
    assert "생육도일(GDD)" in out
    assert "State Vector" not in out


def test_localize_word_boundary_no_partial():
    """부분 문자열 오치환 방지 — 'cat'이 'category'를 건드리지 않음."""
    assert localize_terms("category theory", {"cat": "고양이"}) == "category theory"


def test_localize_longest_first():
    """긴 용어 우선 — 'State Vector Schema'가 'State Vector'보다 먼저 치환."""
    m = {"State Vector": "상태벡터", "State Vector Schema": "상태벡터 스키마"}
    out = localize_terms("the State Vector Schema here", m)
    assert "상태벡터 스키마" in out


def test_localize_empty_map_noop():
    assert localize_terms("hello world", {}) == "hello world"
