"""게이트 사전 묶음 — 띄어쓰기 목록·한계값 등 (v1.11-b).

본체 사전은 `bundles/core/dicts/`, 아래 층(문서 종류·분야·시리즈·프로젝트)은 `<층 디렉토리>/dicts/`.
아래 층 파일이 있으면 **통째로 교체**하고, 파일에 `"extend": true`가 있으면 `items`를 이어 붙인다.
"""
from __future__ import annotations

import json
from pathlib import Path

from techdoc_core.bundles.loader import core_bundle_dir


def _read(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_dict(name: str, layers: list[tuple[str, Path | None]]) -> dict | list:
    """층 순서대로 `dicts/<name>`을 겹쳐 읽는다. 어디에도 없으면 빈 dict."""
    result: dict | list | None = _read(core_bundle_dir() / "dicts" / name)
    for layer, directory in layers:
        if layer == "core" or directory is None:
            continue
        data = _read(Path(directory) / "dicts" / name)
        if data is None:
            continue
        if isinstance(data, dict) and data.get("extend") and isinstance(result, dict):
            merged = dict(result)
            merged["items"] = list(result.get("items") or []) + list(data.get("items") or [])
            result = merged
        else:
            result = data
    return result if result is not None else {}
