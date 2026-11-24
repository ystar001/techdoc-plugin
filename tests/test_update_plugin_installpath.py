"""update_plugin — installed_plugins.json의 installPath 갱신 (findings F108).

실행된 폴더(캐시의 다른 판)만 바뀌고 Claude Code가 실제로 읽는 installPath는 그대로
남던 결함의 재현 테스트. 실제 홈 폴더는 건드리지 않도록 json 경로를 주입한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts import update_plugin
from scripts.update_plugin import find_install_entry, main


def _make_plugin(root: Path, version: str) -> Path:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "techdoc-plugin", "version": version}), encoding="utf-8"
    )
    return root


@pytest.fixture
def fake_home(tmp_path: Path) -> dict:
    """임시 홈 — 캐시에 1.10.0·1.8.0 두 폴더, installPath는 1.8.0 (F108 재현 경로)."""
    cache = tmp_path / "home" / ".claude" / "plugins" / "cache" / "mk" / "techdoc-plugin"
    run_dir = _make_plugin(cache / "1.10.0", "1.0.0")
    active = _make_plugin(cache / "1.8.0", "1.0.0")
    json_path = tmp_path / "home" / ".claude" / "plugins" / "installed_plugins.json"
    json_path.write_text(json.dumps({
        "version": 2,
        "plugins": {
            "other@mk": [{"scope": "user", "installPath": str(tmp_path / "x"), "version": "9"}],
            "techdoc-plugin@techdoc-marketplace": [{
                "scope": "user",
                "installPath": str(active),
                "version": "1.0.0",
                "installedAt": "2026-05-13T08:20:44.890Z",
                "lastUpdated": "2026-07-13T04:37:00.000Z",
            }],
        },
    }, indent=2), encoding="utf-8")
    return {"run_dir": run_dir, "active": active, "json": json_path}


def _mock_release(monkeypatch, zip_bytes: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/releases/latest" in str(request.url):
            return httpx.Response(200, json={
                "tag_name": "v1.1.0", "name": "v1.1.0", "body": "",
                "published_at": "2026-11-24T00:00:00Z",
                "assets": [{"name": "techdoc-plugin-v1.1.0.zip",
                            "browser_download_url": "https://example.invalid/x.zip"}],
            })
        return httpx.Response(200, content=zip_bytes)

    monkeypatch.setattr(
        "scripts.update_plugin._http_transport", lambda: httpx.MockTransport(handler)
    )


def test_find_install_entry_f108(fake_home):
    """F108 — json에서 techdoc 항목의 installPath를 찾는다(다른 플러그인 항목은 무시)."""
    entry = find_install_entry(fake_home["json"])
    assert entry is not None
    assert entry.install_path == fake_home["active"]
    assert entry.key.startswith("techdoc-plugin@")


def test_find_install_entry_missing_json(tmp_path):
    assert find_install_entry(tmp_path / "none.json") is None


def test_update_targets_installpath_not_run_dir_f108(
    fake_home, fake_release_zip, monkeypatch, capsys
):
    """F108 — 캐시의 다른 판 폴더에서 돌려도 installPath 폴더가 갱신되고, json 백업이 남는다."""
    _mock_release(monkeypatch, fake_release_zip.read_bytes())
    monkeypatch.setattr("builtins.input", lambda _: "y")

    rc = main([], plugin_root=fake_home["run_dir"], installed_json=fake_home["json"])
    assert rc == 0

    def ver(p: Path) -> str:
        return json.loads((p / ".claude-plugin" / "plugin.json").read_text("utf-8"))["version"]

    assert ver(fake_home["active"]) == "1.1.0"      # 실제로 읽히는 폴더가 갱신
    assert ver(fake_home["run_dir"]) == "1.0.0"     # 실행 폴더는 그대로

    data = json.loads(fake_home["json"].read_text("utf-8"))
    ent = data["plugins"]["techdoc-plugin@techdoc-marketplace"][0]
    assert ent["version"] == "1.1.0"
    assert ent["installPath"] == str(fake_home["active"])
    assert ent["lastUpdated"] != "2026-07-13T04:37:00.000Z"
    assert data["plugins"]["other@mk"][0]["version"] == "9"   # 다른 항목 보존

    backups = list(fake_home["json"].parent.glob("installed_plugins.json.bak-*"))
    assert len(backups) == 1
    old = json.loads(backups[0].read_text("utf-8"))
    assert old["plugins"]["techdoc-plugin@techdoc-marketplace"][0]["version"] == "1.0.0"

    out = capsys.readouterr().out
    assert "installPath" in out and "1.1.0" in out


def test_yes_flag_is_non_interactive_f108(fake_home, fake_release_zip, monkeypatch):
    """F108 — --yes면 input()을 부르지 않고 적용한다."""
    _mock_release(monkeypatch, fake_release_zip.read_bytes())

    def boom(_):
        raise AssertionError("input() 호출됨")

    monkeypatch.setattr("builtins.input", boom)
    rc = main(["--yes"], plugin_root=fake_home["run_dir"], installed_json=fake_home["json"])
    assert rc == 0
    pj = json.loads((fake_home["active"] / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    assert pj["version"] == "1.1.0"


def test_missing_installpath_folder_stops(fake_home, monkeypatch, capsys):
    """installPath 폴더가 없으면 엉뚱한 폴더를 고치지 않고 멈춘다."""
    import shutil

    shutil.rmtree(fake_home["active"])
    _mock_release(monkeypatch, b"")
    rc = main(["--yes"], plugin_root=fake_home["run_dir"], installed_json=fake_home["json"])
    assert rc == 1
    assert "installPath" in capsys.readouterr().err


def test_no_entry_falls_back_to_run_dir(fake_plugin_dir, tmp_path, monkeypatch, capsys):
    """json에 techdoc 항목이 없으면 실행 폴더를 갱신하되 경고한다."""
    empty = tmp_path / "installed_plugins.json"
    empty.write_text(json.dumps({"version": 2, "plugins": {}}), encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "tag_name": "v1.0.0", "name": "", "body": "", "published_at": "",
            "assets": [{"name": "a.zip", "browser_download_url": "https://e.invalid/a.zip"}],
        })

    monkeypatch.setattr(
        "scripts.update_plugin._http_transport", lambda: httpx.MockTransport(handler)
    )
    rc = main(["--check"], plugin_root=fake_plugin_dir, installed_json=empty)
    assert rc == 0
    assert "installed_plugins.json" in capsys.readouterr().err


def test_default_json_path_uses_home(monkeypatch, tmp_path):
    """기본 json 경로는 호출 시점의 홈 아래(테스트에서 홈을 바꿀 수 있게)."""
    monkeypatch.delenv("TECHDOC_INSTALLED_PLUGINS", raising=False)
    monkeypatch.setattr(update_plugin.Path, "home", classmethod(lambda cls: tmp_path))
    assert update_plugin.installed_plugins_path() == (
        tmp_path / ".claude" / "plugins" / "installed_plugins.json"
    )
