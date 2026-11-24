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
    draft: list[TreeFile] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    reference_md: list[TreeFile] = field(default_factory=list)
    outline: dict = field(default_factory=dict)  # final_outline.json — 별첨 선언(V2)
    numbering: dict = field(default_factory=dict)
    exempt: dict[str, dict] = field(default_factory=dict)  # "<cid>|<sec>" → {gates, why}
    image_license: str | None = None  # 이미지 라이선스 대장 글(V7) — 파일이 없으면 None
    extra: dict = field(default_factory=dict)
    load_errors: list[str] = field(default_factory=list)
    # 묶음 층 [(층 이름, 디렉토리)] — 게이트 사전(`dicts/`)을 이 순서로 겹쳐 읽는다(config.layer_dirs)
    layers: list[tuple[str, Path | None]] = field(default_factory=list)
    # standard 모드 원본 {doc, reference_list, glossary} — PLG-CQ 게이트(check_quality 지표)가 읽는다.
    # None이면 self-model 카드(또는 카드 없음) — PLG-FG·PLG-CQ self-model·VC 게이트가 카드를 본다
    standard: dict | None = None

    def is_empty(self) -> bool:
        return not self.cards and not self.tree and not self.draft

    def card_items(self):
        """(카드id, 섹션키, 표제, 본문) — 원본 check_v2.texts 순서(카드 수준 필드 → 섹션)."""
        from techdoc_core.qc.card_text import card_texts

        for cid, card in self.cards.items():
            for key, title, body in card_texts(card):
                yield cid, key, title, body

    def prose(self) -> list[TreeFile]:
        """산문 게이트 입력 — draft가 있으면 draft(`_`로 시작하는 파일 제외), 없으면 렌더 트리."""
        if self.draft:
            return [t for t in self.draft if not t.rel.rsplit("/", 1)[-1].startswith("_")]
        return list(self.tree)
