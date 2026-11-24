"""게이트 등록 — 게이트 하나 = 함수 하나 (v1.11, 설계 D3.1).

함수 서명은 `(model: DocModel) -> GateOutput`. 읽은 대상 수와 지적 목록만 돌려주고,
판정(pass·fail·no-target·skip)과 집행 수준은 엔진이 정한다.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from techdoc_core.qc.model import DocModel, TreeFile


@dataclass(frozen=True)
class Finding:
    loc: str
    msg: str


@dataclass(frozen=True)
class GateOutput:
    targets_read: int
    findings: list[Finding] = field(default_factory=list)


@dataclass(frozen=True)
class Sample:
    model: DocModel
    expect: int


GateFunc = Callable[[DocModel], GateOutput]
REGISTRY: dict[str, GateFunc] = {}


def gate(gate_id: str, samples: list[Sample] | None = None):
    """게이트 함수 등록 데코레이터. 같은 id를 두 번 등록하면 ValueError."""

    def deco(fn: GateFunc) -> GateFunc:
        if gate_id in REGISTRY:
            raise ValueError(f"게이트 {gate_id} 중복 등록")
        fn.gate_id = gate_id  # type: ignore[attr-defined]
        fn.samples = list(samples or [])  # type: ignore[attr-defined]
        REGISTRY[gate_id] = fn
        return fn

    return deco


def sample_model(*, root: Path | None = None, kind: str = "tech_report",
                 cards: dict[str, dict] | None = None, tree: dict[str, str] | None = None,
                 references: list[dict] | None = None, reference_md: dict[str, str] | None = None,
                 exempt: dict[str, dict] | None = None, extra: dict | None = None,
                 draft: dict[str, str] | None = None, outline: dict | None = None,
                 numbering: dict | None = None, image_license: str | None = None) -> DocModel:
    """자기검사·테스트용 작은 모델."""
    return DocModel(
        root=root or Path("."),
        kind=kind,
        cards=dict(cards or {}),
        tree=[TreeFile(k, v) for k, v in (tree or {}).items()],
        draft=[TreeFile(k, v) for k, v in (draft or {}).items()],
        references=list(references or []),
        reference_md=[TreeFile(k, v) for k, v in (reference_md or {}).items()],
        outline=dict(outline or {}),
        numbering=dict(numbering or {}),
        exempt=dict(exempt or {}),
        extra=dict(extra or {}),
        image_license=image_license,
    )
