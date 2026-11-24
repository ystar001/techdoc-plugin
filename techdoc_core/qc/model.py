"""qc 문서 모델 — 어댑터가 채우고 게이트가 읽는다 (v1.11)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TreeFile:
    rel: str  # 렌더 트리 기준 POSIX 상대 경로
    text: str


@dataclass
class DocModel:
    root: Path
    kind: str = "tech_report"
    cards: dict[str, dict] = field(default_factory=dict)
    tree: list[TreeFile] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    reference_md: list[TreeFile] = field(default_factory=list)
    numbering: dict = field(default_factory=dict)
    exempt: dict[str, list[str]] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    load_errors: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.cards and not self.tree
