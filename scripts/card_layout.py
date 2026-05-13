"""Plan D (F8) — 카드 레이아웃 모드 자동 판별.

plugin은 두 가지 카드 레이아웃을 지원한다:

1. **Standard 모드** (plugin 기본):
   - `output/writer_state.json`이 모든 카드의 상태를 관리
   - `output/document_draft.json` 또는 `output/sections/section_<id>.json`에 카드 내용
   - 한 섹션 = 다수 카드 (tech/project/product 분리)
   - 각 카드 = blocks dict (7/7/6 fields)

2. **Self-model 모드** (자식 프로젝트가 채택 가능):
   - `output/cards/<call_id>_card.json` 파일 1개 = 카드 1개
   - 카드 = sections dict (사용자 정의 키, 각 키 아래 `body`)
   - writer_state.json·document_draft.json 부재
   - openfieldtech 프로젝트가 채택한 패턴

`/techdoc-rewrite`·`/techdoc-write`는 mode를 자동 판별해 적절한 경로로 분기.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

Mode = Literal["standard", "self_model", "unknown"]


def detect_mode(output_dir: Path) -> Mode:
    """output_dir의 파일 구조로 카드 레이아웃 모드 판별.

    Priority:
    1. `writer_state.json` 존재 → "standard"
    2. `cards/*_card.json` 존재 → "self_model"
    3. 그 외 → "unknown"
    """
    output_dir = Path(output_dir)
    if (output_dir / "writer_state.json").exists():
        return "standard"
    cards_dir = output_dir / "cards"
    if cards_dir.exists() and cards_dir.is_dir():
        if any(cards_dir.glob("*_card.json")):
            return "self_model"
    return "unknown"


def load_self_model_card(output_dir: Path, card_id: str) -> dict:
    """self-model 모드에서 단일 카드 JSON 로드."""
    path = Path(output_dir) / "cards" / f"{card_id}_card.json"
    if not path.exists():
        raise FileNotFoundError(f"self-model 카드 파일이 없습니다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_standard_card_state(output_dir: Path, card_id: str) -> dict:
    """standard 모드에서 writer_state.json에서 카드 상태 로드.

    카드 ID로 section/cards 트리를 탐색해 매칭 항목 반환.
    """
    state_path = Path(output_dir) / "writer_state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"writer_state.json이 없습니다: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    section_states = state.get("section_states", {})
    for sec in section_states.values():
        for card in sec.get("cards", []):
            if card.get("id") == card_id:
                return card
    raise KeyError(f"card_id {card_id}가 writer_state.json에 없습니다")
