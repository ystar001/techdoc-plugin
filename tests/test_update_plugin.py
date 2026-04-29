"""update_plugin.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.update_plugin import is_newer


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


@pytest.mark.parametrize(
    "latest, current, expected",
    [
        ("1.1.0", "1.0.0", True),
        ("1.0.1", "1.0.0", True),
        ("2.0.0", "1.9.9", True),
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "1.0.1", False),
        ("0.9.0", "1.0.0", False),
        ("1.10.0", "1.9.0", True),
    ],
)
def test_is_newer(latest: str, current: str, expected: bool):
    assert is_newer(latest, current) is expected


def test_is_newer_strips_v_prefix():
    assert is_newer("v1.1.0", "1.0.0") is True
    assert is_newer("v1.0.0", "v1.0.0") is False
