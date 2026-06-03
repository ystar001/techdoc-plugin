"""autopilot_state.json read/write (v1.3.0)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_SCHEMA_VERSION = "0.1.0"
STATE_FILENAME = "autopilot_state.json"

# Stage 정의 (chunk granularity B 결정)
ALL_STAGE_IDS = (
    "outline",
    "research_A", "research_B", "research_C",
    "merge_research",
    "write_A", "write_B", "write_C",
    "review",
    "deepdive",
    "render",
)


def _empty_state() -> dict:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "started_at": None,
        "title": None,
        "config": {},
        "stages": {},
        "wake_ups": [],
        "consecutive_card_failures": 0,
        "halt_reason": None,
        "completed_at": None,
    }


# 디스크 산출물 → 완료 stage 매핑 (F9-ii). (파일/디렉토리, stage)
_ARTIFACT_STAGES = [
    ("draft_outline.json", "outline"),
    ("reference_list.json", "merge_research"),
    ("document_final.json", "render"),  # 최종 문서까지 있으면 render도
]


def scan_completed_stages(output_dir: Path) -> set[str]:
    """output_dir의 산출물을 스캔해 완료된 stage 집합 반환 (F9-ii)."""
    out = Path(output_dir)
    done: set[str] = set()
    for fname, stage in _ARTIFACT_STAGES:
        if (out / fname).exists():
            done.add(stage)
    # cards/*_card.json 있으면 write 완료로 간주
    cards = out / "cards"
    if cards.is_dir() and any(cards.glob("*_card.json")):
        done.update({"write_A", "write_B", "write_C"})
    # reviews/ 비어있지 않으면 review 완료
    reviews = out / "reviews"
    if reviews.is_dir() and any(reviews.glob("*.md")):
        done.add("review")
    # research_*.json 있으면 해당 research 완료
    for rp in out.glob("research_*.json"):
        done.add(rp.stem)  # e.g. research_A
    return done


def init_state(
    output_dir: Path,
    title: str,
    config: dict,
    num_section_groups: int = 3,
    resume_from_disk: bool = False,
) -> dict:
    """신규 autopilot_state 생성. 섹션 그룹 수에 따라 research_*·write_*만 포함.

    resume_from_disk=True면 디스크 산출물을 스캔해 완료 stage를 completed로 마킹(F9-ii).
    """
    state = _empty_state()
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["title"] = title
    state["config"] = dict(config)
    groups = ["A", "B", "C"][:num_section_groups]
    stages: dict[str, str] = {"outline": "pending"}
    for g in groups:
        stages[f"research_{g}"] = "pending"
    stages["merge_research"] = "pending"
    for g in groups:
        stages[f"write_{g}"] = "pending"
    stages["review"] = "pending"
    # deepdive(별첨)는 config 요청 시 pending, 아니면 skipped (F9-i)
    wants_deepdive = bool(config.get("deep_dive_auto") or config.get("deep_dive"))
    stages["deepdive"] = "pending" if wants_deepdive else "skipped"
    stages["render"] = "pending"
    if resume_from_disk:
        done = scan_completed_stages(output_dir)
        for s in done:
            if s in stages:
                stages[s] = "completed"
    state["stages"] = stages
    return state


def load_state(output_dir: Path) -> dict:
    """state.json 로드. 파일 없으면 빈 state 반환."""
    path = Path(output_dir) / STATE_FILENAME
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # schema_version 누락 보정
        if "schema_version" not in data:
            data["schema_version"] = STATE_SCHEMA_VERSION
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_state()


def save_state(output_dir: Path, state: dict) -> None:
    path = Path(output_dir) / STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_stage(state: dict, chunk_id: str, status: str) -> None:
    """stages[chunk_id] = status. 정의되지 않은 chunk는 무시."""
    if chunk_id in state.get("stages", {}):
        state["stages"][chunk_id] = status


def append_wake_up(state: dict, entry: dict) -> None:
    """wake_ups 배열에 1개 추가."""
    state.setdefault("wake_ups", []).append(entry)


def mark_completed(state: dict) -> None:
    state["completed_at"] = datetime.now(timezone.utc).isoformat()


def mark_halted(state: dict, reason: str) -> None:
    state["halt_reason"] = reason
