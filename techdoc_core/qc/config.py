"""프로젝트 설정 `techdoc.project.yaml` (v1.11 — 설계 D1·D3.2).

층 선택(kind·domain·series)·번호 꼴·경로·게이트 끄기/면제/수준 덮어쓰기·게이트별 추가 설정을
한 파일에서 받는다. 파일이 없으면 플러그인 출력 관례의 기본값으로 돈다(하위 호환).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

import yaml

from techdoc_core.bundles.loader import core_bundle_dir
from techdoc_core.bundles.schema import Level

CONFIG_NAME = "techdoc.project.yaml"
SECTION_STYLES = ("arabic", "roman", "letter_middle")
_LEVELS = get_args(Level)


@dataclass
class Paths:
    cards: Path
    render_tree: Path
    references: Path


@dataclass
class ProjectConfig:
    root: Path
    paths: Paths
    kind: str = "tech_report"
    domain: Path | None = None
    series: Path | None = None
    numbering: dict = field(default_factory=lambda: {"section": "arabic", "appendix": "letter"})
    gates_off: list[str] = field(default_factory=list)
    exempt: dict[str, list[str]] = field(default_factory=dict)
    level_overrides: dict[str, str] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _default_paths(root: Path) -> Paths:
    out = root / "output"
    return Paths(cards=out / "cards", render_tree=out / "render" / "tree",
                 references=out / "reference_list.json")


def default_config(root: Path) -> ProjectConfig:
    return ProjectConfig(root=Path(root), paths=_default_paths(Path(root)))


def _opt_path(root: Path, value) -> Path | None:
    if not value:
        return None
    p = Path(value)
    return p if p.is_absolute() else (root / p)


def load_config(root: Path, path: Path | None = None) -> ProjectConfig:
    """설정 읽기. path가 없으면 root/techdoc.project.yaml, 그것도 없으면 기본값."""
    root = Path(root)
    cfg_path = Path(path) if path else root / CONFIG_NAME
    if not cfg_path.is_file():
        return default_config(root)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    cfg = default_config(root)
    cfg.kind = data.get("kind", cfg.kind)
    cfg.domain = _opt_path(root, data.get("domain"))
    cfg.series = _opt_path(root, data.get("series"))

    numbering = {**cfg.numbering, **(data.get("numbering") or {})}
    if numbering["section"] not in SECTION_STYLES:
        raise ValueError(f"numbering.section은 {SECTION_STYLES} 중 하나: {numbering['section']!r}")
    cfg.numbering = numbering

    paths = data.get("paths") or {}
    for key in ("cards", "render_tree", "references"):
        if paths.get(key):
            setattr(cfg.paths, key, _opt_path(root, paths[key]))

    gates = data.get("gates") or {}
    # YAML 1.1(PyYAML)은 키 `off`를 불리언 False로 읽는다 — 두 꼴 모두 받는다
    off = gates.get("off", gates.get(False))
    cfg.gates_off = [str(g) for g in off or []]
    cfg.exempt = {str(k): [str(g) for g in v] for k, v in (gates.get("exempt") or {}).items()}
    levels = {str(k): str(v) for k, v in (gates.get("level") or {}).items()}
    bad = {k: v for k, v in levels.items() if v not in _LEVELS}
    if bad:
        raise ValueError(f"gates.level 값은 {_LEVELS} 중 하나: {bad}")
    cfg.level_overrides = levels
    cfg.extra = data.get("extra") or {}
    return cfg


def validate_gate_ids(cfg: ProjectConfig, known: set[str]) -> None:
    """설정이 부르는 게이트 id 중 모르는 것을 cfg.warnings에 더한다(조용한 무시 금지)."""
    seen: list[str] = []
    named = [*cfg.gates_off, *cfg.level_overrides]
    for ids in cfg.exempt.values():
        named.extend(ids)
    for gid in named:
        if gid not in known and gid not in seen:
            seen.append(gid)
            cfg.warnings.append(f"모르는 게이트 id: {gid}")


def layer_dirs(cfg: ProjectConfig) -> list[tuple[str, Path | None]]:
    """load_gate_specs 입력 — 본체 → 문서 종류 → 분야 → 시리즈 → 프로젝트."""
    core = core_bundle_dir()
    kind_dir = core.parent / "kinds" / cfg.kind
    project_dir = cfg.root / ".techdoc"
    return [
        ("core", core),
        ("kind", kind_dir if kind_dir.is_dir() else None),
        ("domain", cfg.domain),
        ("series", cfg.series),
        ("project", project_dir if project_dir.is_dir() else None),
    ]
