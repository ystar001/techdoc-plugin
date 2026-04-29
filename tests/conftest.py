"""pytest fixtures for update_plugin tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fake_plugin_dir(tmp_path: Path) -> Path:
    """가짜 plugin 디렉토리 (현재 v1.0.0 설치 상태 모사)."""
    plugin_root = tmp_path / "techdoc-plugin"
    (plugin_root / ".claude-plugin").mkdir(parents=True)
    (plugin_root / "commands").mkdir()
    (plugin_root / "scripts").mkdir()

    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    plugin_json.write_text(
        json.dumps({"name": "techdoc-plugin", "version": "1.0.0"}),
        encoding="utf-8",
    )

    (plugin_root / "commands" / "existing.md").write_text("# existing", encoding="utf-8")
    (plugin_root / "scripts" / "existing.py").write_text("# existing", encoding="utf-8")

    return plugin_root


@pytest.fixture
def fake_release_zip(tmp_path: Path) -> Path:
    """v1.1.0 릴리스를 모사하는 zip 파일."""
    import zipfile

    src = tmp_path / "release_src" / "techdoc-plugin"
    (src / ".claude-plugin").mkdir(parents=True)
    (src / "commands").mkdir()
    (src / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "techdoc-plugin", "version": "1.1.0"}),
        encoding="utf-8",
    )
    (src / "commands" / "new_command.md").write_text("# new", encoding="utf-8")

    zip_path = tmp_path / "techdoc-plugin-v1.1.0.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for path in src.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(src))
    return zip_path
