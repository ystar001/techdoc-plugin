"""다음 chunk 결정 + stage dependency graph (v1.3.0).

stages = {chunk_id: status}.
status ∈ {pending, in_progress, completed, skipped, failed}.

dependency graph (chunk → 의존하는 prerequisite chunks):
  outline           ← (없음)
  research_A·B·C    ← outline
  merge_research    ← 모든 research_*
  write_A·B·C       ← merge_research
  review            ← 모든 write_*
  render            ← review
"""

from __future__ import annotations

# stage 정의 순서 (의존 만족 시 우선순위)
STAGE_ORDER = (
    "outline",
    "research_A", "research_B", "research_C",
    "merge_research",
    "write_A", "write_B", "write_C",
    "review",
    "render",
)


def _is_satisfied(status: str) -> bool:
    return status in ("completed", "skipped")


def _prerequisites(chunk_id: str, all_stages: list[str]) -> list[str]:
    """chunk_id의 prerequisite 목록 (현재 보고서의 stages 중에서)."""
    if chunk_id == "outline":
        return []
    if chunk_id.startswith("research_"):
        return ["outline"]
    if chunk_id == "merge_research":
        return [s for s in all_stages if s.startswith("research_")]
    if chunk_id.startswith("write_"):
        return ["merge_research"]
    if chunk_id == "review":
        return [s for s in all_stages if s.startswith("write_")]
    if chunk_id == "render":
        return ["review"]
    return []


def pick_next_chunk(state: dict) -> str | None:
    """다음 실행할 chunk를 stage_order 순서로 탐색.

    Returns chunk_id 또는 None (모든 stage 완료/스킵)."""
    stages = state.get("stages", {})
    all_stage_ids = list(stages.keys())
    for chunk_id in STAGE_ORDER:
        if chunk_id not in stages:
            continue
        status = stages[chunk_id]
        if status in ("completed", "skipped"):
            continue
        # pending or in_progress or failed → prerequisites 점검
        prereqs = _prerequisites(chunk_id, all_stage_ids)
        if all(_is_satisfied(stages.get(p, "pending")) for p in prereqs):
            return chunk_id
    return None


def estimate_remaining_chunks(state: dict) -> int:
    """미완료 chunk 수 (status가 completed·skipped가 아닌 것)."""
    return sum(
        1 for s in state.get("stages", {}).values()
        if s not in ("completed", "skipped")
    )
