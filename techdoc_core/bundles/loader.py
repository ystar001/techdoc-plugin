"""묶음 로더 — 층 순서대로 gates.yaml을 겹쳐 읽는다 (설계 D1).

아래 층(문서 종류·분야·시리즈·프로젝트)이 위 층과 같은 id를 다시 정의하면
`override: true`일 때만 바꾼다. 조용한 덮어쓰기는 오류다.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from techdoc_core.bundles.schema import GateSpec

LAYER_ORDER = ("core", "kind", "domain", "series", "project")


class BundleError(ValueError):
    """묶음 파일의 형식·겹침 오류."""


def core_bundle_dir() -> Path:
    """플러그인 본체 묶음 경로 — `techdoc-plugin/bundles/core`."""
    return Path(__file__).resolve().parents[2] / "bundles" / "core"


def _read_gates(layer: str, directory: Path) -> list[GateSpec]:
    path = directory / "gates.yaml"
    if not path.is_file():
        return []
    try:
        rows = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    except yaml.YAMLError as e:
        raise BundleError(f"{layer}/gates.yaml: YAML 오류 — {e}") from e
    if not isinstance(rows, list):
        raise BundleError(f"{layer}/gates.yaml: 최상위는 리스트여야 함")
    out: list[GateSpec] = []
    for i, row in enumerate(rows):
        try:
            out.append(GateSpec(**row))
        except (ValidationError, TypeError) as e:
            raise BundleError(f"{layer}/gates.yaml[{i}]: {e}") from e
    return out


def load_gate_specs(layers: list[tuple[str, Path | None]]) -> dict[str, GateSpec]:
    """[(층 이름, 디렉토리)] → {게이트 id: GateSpec}. 디렉토리가 None이거나 없으면 건너뜀."""
    specs: dict[str, GateSpec] = {}
    for layer, directory in layers:
        if directory is None or not Path(directory).is_dir():
            continue
        for spec in _read_gates(layer, Path(directory)):
            if spec.id in specs and not spec.override:
                raise BundleError(f"{layer}/{spec.id}: override 없이 덮어씀")
            specs[spec.id] = spec
    return specs
