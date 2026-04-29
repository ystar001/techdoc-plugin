"""update_plugin.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path


def test_pytest_infra_works():
    """pytest 인프라가 정상 동작하는지 확인 (TDD 출발 sanity check)."""
    assert 1 + 1 == 2


def test_fake_plugin_dir_fixture(fake_plugin_dir: Path):
    """fake_plugin_dir fixture가 plugin.json을 v1.0.0으로 만드는지 확인."""
    plugin_json = fake_plugin_dir / ".claude-plugin" / "plugin.json"
    assert plugin_json.exists()
    import json
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"
