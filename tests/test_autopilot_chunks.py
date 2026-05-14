"""Chunk 결정 + dependency graph 회귀."""

from __future__ import annotations


def test_pick_next_chunk_outline_first():
    """초기 상태 — outline이 첫 chunk."""
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "pending",
            "research_A": "pending",
            "research_B": "pending",
            "merge_research": "pending",
            "write_A": "pending",
            "write_B": "pending",
            "review": "pending",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "outline"


def test_pick_next_chunk_research_after_outline():
    """outline 완료 후 research_A."""
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "pending",
            "research_B": "pending",
            "merge_research": "pending",
            "write_A": "pending",
            "review": "pending",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "research_A"


def test_pick_next_chunk_merge_after_all_research():
    """모든 research_* 완료 후 merge_research."""
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "completed",
            "research_B": "completed",
            "research_C": "completed",
            "merge_research": "pending",
            "write_A": "pending",
            "review": "pending",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "merge_research"


def test_pick_next_chunk_write_after_merge():
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "completed",
            "merge_research": "completed",
            "write_A": "pending",
            "write_B": "pending",
            "review": "pending",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "write_A"


def test_pick_next_chunk_review_after_all_writes():
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "completed",
            "merge_research": "completed",
            "write_A": "completed",
            "write_B": "completed",
            "review": "pending",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "review"


def test_pick_next_chunk_render_after_review():
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "completed",
            "merge_research": "completed",
            "write_A": "completed",
            "review": "completed",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "render"


def test_pick_next_chunk_none_when_all_done():
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "completed",
            "merge_research": "completed",
            "write_A": "completed",
            "review": "completed",
            "render": "completed",
        }
    }
    assert pick_next_chunk(state) is None


def test_pick_next_chunk_skips_completed_and_skipped():
    """completed + skipped는 dependency 충족으로 처리."""
    from scripts.autopilot.chunks import pick_next_chunk

    state = {
        "stages": {
            "outline": "completed",
            "research_A": "completed",
            "research_B": "skipped",  # 섹션 없어서 skip된 케이스
            "merge_research": "pending",
            "write_A": "pending",
            "review": "pending",
            "render": "pending",
        }
    }
    assert pick_next_chunk(state) == "merge_research"
