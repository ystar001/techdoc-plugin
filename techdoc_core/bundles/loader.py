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


KIND_SCHEMA = "techdoc-kind/1"
KIND_FILE = "kind.yaml"
_KIND_KEYS = {"schema", "description", "gates", "extra", "expects"}


def kinds_bundle_dir() -> Path:
    """플러그인이 싣는 문서 종류 묶음 경로 — `techdoc-plugin/bundles/kinds`."""
    return core_bundle_dir().parent / "kinds"


def read_kind_bundle(directory: Path) -> dict | None:
    """`<kind 디렉토리>/kind.yaml` → {"level", "off", "extra", "expects"}. 파일이 없으면 None.

    꼴(`schema: techdoc-kind/1`): `gates: {level: {id: 수준}, off: [id]}` · `extra: {...}` ·
    `expects: {id: ">=1"}`. 모르는 키·틀린 형은 BundleError — 조용히 무시하지 않는다.
    """
    path = Path(directory) / KIND_FILE
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise BundleError(f"{path}: YAML 오류 — {e}") from e
    if not isinstance(data, dict):
        raise BundleError(f"{path}: 최상위는 표(dict)여야 함")
    if data.get("schema") != KIND_SCHEMA:
        raise BundleError(f"{path}: schema는 {KIND_SCHEMA!r}여야 함 — {data.get('schema')!r}")
    unknown = sorted(set(map(str, data)) - _KIND_KEYS)
    if unknown:
        raise BundleError(f"{path}: 모르는 키 {unknown} (받는 키: {sorted(_KIND_KEYS)})")
    gates = data.get("gates") or {}
    if not isinstance(gates, dict):
        raise BundleError(f"{path}: gates는 표(dict)여야 함")
    # YAML 1.1(PyYAML)은 키 `off`를 불리언 False로 읽는다 — 두 꼴 모두 받는다
    gates = {("off" if k is False else str(k)): v for k, v in gates.items()}
    bad_g = sorted(set(gates) - {"level", "off"})
    if bad_g:
        raise BundleError(f"{path}: gates의 모르는 키 {bad_g} (받는 키: level·off)")
    level, off = gates.get("level") or {}, gates.get("off") or []
    extra, expects = data.get("extra") or {}, data.get("expects") or {}
    for name, val, typ in (("gates.level", level, dict), ("gates.off", off, list),
                           ("extra", extra, dict), ("expects", expects, dict)):
        if not isinstance(val, typ):
            raise BundleError(f"{path}: {name}의 형이 틀림 — {typ.__name__} 필요")
    return {"level": {str(k): str(v) for k, v in level.items()}, "off": [str(g) for g in off],
            "extra": extra, "expects": {str(k): str(v) for k, v in expects.items()}}


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
