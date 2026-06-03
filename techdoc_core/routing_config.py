"""카드 ID → Part 라우팅 config (F21).

자식 프로젝트의 하드코딩 Part 체계를 데이터(config)로 분리한다. config는
순서 있는 규칙 목록: 각 규칙은 {key, pattern(정규식 prefix), dir, label}.
parse_card_id가 card_id를 규칙에 순차 매칭해 (part_key, sort_key)를 반환한다.
F15 트리 생성(후속)이 이 결과로 디렉토리를 구성한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# 범용 기본 config — 숫자 ID=본문, 영문 prefix=별첨. 프로젝트별 config로 교체 가능.
DEFAULT_ROUTING = {
    "parts": [
        {"key": "body", "pattern": r"^\d+(?:\.\d+)*$", "dir": "Part-본문", "label": "본문"},
        {"key": "appendix", "pattern": r"^[A-Za-z]", "dir": "Part-별첨", "label": "별첨"},
    ]
}

_NUM_RE = re.compile(r"\d+")


def load_routing_config(path: str | Path | None = None) -> dict:
    """routing config 로드. path 없으면 DEFAULT_ROUTING.

    각 규칙은 `pattern`·`key` 필수 — 누락 시 load 시점에 ValueError로 거부해
    parse_card_id 런타임 KeyError를 방지한다.
    """
    if path is None:
        return DEFAULT_ROUTING
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for rule in cfg.get("parts", []):
        if "pattern" not in rule or "key" not in rule:
            raise ValueError(f"routing config 규칙에 pattern·key 필수: {rule}")
    return cfg


def _sort_key(card_id: str) -> tuple:
    """card_id의 숫자 부분으로 자연 정렬 키 생성."""
    return tuple(int(n) for n in _NUM_RE.findall(card_id)) or (0,)


def parse_card_id(card_id: str, config: dict = DEFAULT_ROUTING) -> tuple[str, tuple]:
    """card_id → (part_key, sort_key). 매칭 규칙 없으면 ('misc', ...)."""
    cid = card_id.strip()
    for rule in config.get("parts", []):
        if re.match(rule["pattern"], cid):
            return rule["key"], _sort_key(cid)
    return "misc", _sort_key(cid)
