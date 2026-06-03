"""markdown_tree (F15 + F17) 회귀 테스트.

config 기반 트리 디렉토리 빌더 — 카드 버킷팅·parent 병합·카드/병합 MD 렌더·
트리 emit·조건부 시리즈 INDEX(F17)·render.py --tree 통합.
"""
import json

from techdoc_core.renderers.markdown_tree import bucket_cards, group_by_parent


def _card(tmp, cid, title="제목"):
    p = tmp / f"{cid}_card.json"
    p.write_text(json.dumps({"card_id": cid, "title": title,
                             "sections": {"sec1": {"title": "정의", "body": "본문."}}},
                            ensure_ascii=False), encoding="utf-8")
    return p


def test_bucket_cards_by_part(tmp_path):
    files = [_card(tmp_path, "1.1"), _card(tmp_path, "1.2"), _card(tmp_path, "A-1")]
    buckets = bucket_cards(files)
    assert set(buckets) >= {"body", "appendix"}
    assert len(buckets["body"]) == 2 and len(buckets["appendix"]) == 1


def test_group_by_parent_merges_splits(tmp_path):
    files = [_card(tmp_path, "1.4.L1"), _card(tmp_path, "1.4.L2"), _card(tmp_path, "1.5")]
    groups = group_by_parent(files)
    # 1.4.L1·L2는 parent 1.4로 묶이고, 1.5는 단독
    assert sorted(groups) == ["1.4", "1.5"]
    assert len(groups["1.4"]) == 2 and len(groups["1.5"]) == 1
