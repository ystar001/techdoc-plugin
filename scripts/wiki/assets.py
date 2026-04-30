"""차트·다이어그램 자산 복사 (figures → vault/Assets/figures/<report>/)."""

from __future__ import annotations

import shutil
from pathlib import Path


def copy_figures(source_dir: Path, vault_dir: Path, report_slug: str) -> list[Path]:
    """source_dir의 모든 파일을 vault/Assets/figures/<report_slug>/로 복사.

    source_dir이 없거나 비어있으면 빈 리스트 반환.
    """
    if not source_dir.exists() or not source_dir.is_dir():
        return []
    target = vault_dir / "Assets" / "figures" / report_slug
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in source_dir.iterdir():
        if src.is_file():
            dst = target / src.name
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied
