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


# ── Task 2: 카드/병합 MD 렌더 ──────────────────────────────────


def test_render_card_md_uses_korean_heading():
    from techdoc_core.renderers.markdown_tree import render_card_md

    card = {"card_id": "1.1", "title": "관개", "sections": {"sec1": {"body": "본문 텍스트."}}}
    md = render_card_md(card, card_id="1.1")
    assert "# 1.1" in md or "관개" in md
    assert "정의·범위" in md  # sec1 → 한글 헤딩(section_heading)


def test_render_merged_md_sequential_sections():
    from techdoc_core.renderers.markdown_tree import render_merged_md

    cards = [
        {"card_id": "1.4.L1", "title": "컴퓨팅 — 분할 1/2", "sections": {"sec1": {"body": "a."}}},
        {"card_id": "1.4.L2", "title": "컴퓨팅 — 분할 2/2", "sections": {"sec2": {"body": "b."}}},
    ]
    md = render_merged_md("1.4", cards)
    assert "컴퓨팅" in md and "분할" not in md.split("\n")[0]  # 부모 제목 정리(clean_parent_title)
    assert "a." in md and "b." in md
