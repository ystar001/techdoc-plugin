"""merge_research 계약 방어 테스트 (v1.9.0 워크스트림 G — F34·F44).

researcher round JSON의 refs_found는 스키마상 list[str](REF id)이나,
기존 dedupe_refs는 dict(url·title)를 가정해 str 원소에서 .get() 크래시했다.
"""
from scripts.merge_research import dedupe_refs


def test_dedupe_handles_str_id_list():
    """F34/F44 — str REF id 리스트에서 크래시하지 않고 정규화 처리."""
    kept, removed = dedupe_refs(["REF-001", "REF-002"])
    assert len(kept) == 2
    assert {r.get("id") for r in kept} == {"REF-001", "REF-002"}


def test_dedupe_str_ids_deduplicated_by_id():
    """F34/F44 — 동일 REF id는 id 기준으로 중복 제거."""
    kept, removed = dedupe_refs(["REF-001", "REF-001", "REF-002"])
    assert len(kept) == 2
    assert removed == 1


def test_dedupe_mixed_str_and_dict():
    """F34/F44 — str·dict 혼재 입력도 안전 처리."""
    kept, removed = dedupe_refs(["REF-001", {"id": "REF-002", "url": "http://x", "title": "t"}])
    assert len(kept) == 2


def test_dedupe_dict_url_still_works():
    """회귀 — 기존 dict(url) 기반 중복 제거 동작 유지."""
    kept, removed = dedupe_refs([
        {"url": "http://x/a", "title": "title one here long"},
        {"url": "http://x/a", "title": "title one here long"},
    ])
    assert len(kept) == 1
    assert removed == 1
