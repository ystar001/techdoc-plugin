"""update_plugin.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from scripts.update_plugin import fetch_latest_release, is_newer, read_current_version, PluginError, Release


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


def test_read_current_version_ok(fake_plugin_dir: Path):
    """fake plugin dir에서 v1.0.0을 읽어와야 한다."""
    assert read_current_version(fake_plugin_dir) == "1.0.0"


def test_read_current_version_missing_plugin_json(tmp_path: Path):
    """plugin.json이 없으면 PluginError."""
    with pytest.raises(PluginError, match="plugin.json"):
        read_current_version(tmp_path)


def test_read_current_version_malformed_json(fake_plugin_dir: Path):
    """plugin.json이 깨진 JSON이면 PluginError."""
    (fake_plugin_dir / ".claude-plugin" / "plugin.json").write_text("not json", encoding="utf-8")
    with pytest.raises(PluginError, match="plugin.json"):
        read_current_version(fake_plugin_dir)


def test_read_current_version_missing_version_field(fake_plugin_dir: Path):
    """version 필드가 없으면 PluginError."""
    import json
    (fake_plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "techdoc-plugin"}), encoding="utf-8"
    )
    with pytest.raises(PluginError, match="version"):
        read_current_version(fake_plugin_dir)


# ── fetch_latest_release 테스트 ──────────────────────────────────────────────


def _mock_github_response(payload: dict) -> httpx.MockTransport:
    """GET /repos/.../releases/latest 호출에 대한 가짜 응답."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/releases/latest" in str(request.url)
        return httpx.Response(200, json=payload)
    return httpx.MockTransport(handler)


def test_fetch_latest_release_ok():
    payload = {
        "tag_name": "v1.1.0",
        "name": "v1.1.0",
        "body": "## CHANGELOG\n- Wiki 통합",
        "published_at": "2026-05-15T00:00:00Z",
        "assets": [
            {
                "name": "techdoc-plugin-v1.1.0.zip",
                "browser_download_url": "https://github.com/.../techdoc-plugin-v1.1.0.zip",
            }
        ],
    }
    transport = _mock_github_response(payload)
    rel = fetch_latest_release(transport=transport)
    assert isinstance(rel, Release)
    assert rel.version == "1.1.0"
    assert rel.zip_url.endswith("techdoc-plugin-v1.1.0.zip")
    assert "Wiki 통합" in rel.body


def test_fetch_latest_release_no_zip_asset():
    payload = {
        "tag_name": "v1.1.0",
        "name": "v1.1.0",
        "body": "",
        "published_at": "2026-05-15T00:00:00Z",
        "assets": [],
    }
    transport = _mock_github_response(payload)
    with pytest.raises(PluginError, match="zip 자산"):
        fetch_latest_release(transport=transport)


def test_fetch_latest_release_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})
    transport = httpx.MockTransport(handler)
    with pytest.raises(PluginError, match="GitHub API"):
        fetch_latest_release(transport=transport)
