"""update_plugin.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from scripts.update_plugin import (
    fetch_latest_release,
    is_newer,
    read_current_version,
    download_zip,
    apply_zip,
    PluginError,
    Release,
    print_release_summary,
    print_up_to_date,
    print_reload_hint,
    confirm_with_user,
    main,
)


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


# ── download_zip 테스트 ──────────────────────────────────────────────────────


def test_download_zip(tmp_path: Path, fake_release_zip: Path):
    """다운로드 함수가 mocked URL에서 zip을 받아 저장."""
    payload = fake_release_zip.read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, headers={"Content-Type": "application/zip"})
    transport = httpx.MockTransport(handler)

    dest = download_zip(
        url="https://github.com/.../techdoc-plugin-v1.1.0.zip",
        dest_dir=tmp_path,
        transport=transport,
    )
    assert dest.exists()
    assert dest.suffix == ".zip"
    assert dest.read_bytes() == payload


# ── apply_zip 테스트 ─────────────────────────────────────────────────────────


def test_apply_zip_overwrites_files(fake_plugin_dir: Path, fake_release_zip: Path):
    """zip이 plugin 디렉토리에 적용되면 신규 파일이 추가되어야 한다."""
    apply_zip(fake_release_zip, fake_plugin_dir)
    assert (fake_plugin_dir / "commands" / "new_command.md").exists()
    assert (fake_plugin_dir / "scripts" / "existing.py").exists()
    import json
    data = json.loads((fake_plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "1.1.0"


def test_apply_zip_invalid_structure(fake_plugin_dir: Path, tmp_path: Path):
    """zip에 .claude-plugin/plugin.json이 없으면 PluginError."""
    import zipfile
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("README.md", "# nope")

    with pytest.raises(PluginError, match="zip 형식"):
        apply_zip(bad_zip, fake_plugin_dir)


# ── 사용자 출력·프롬프트 테스트 ────────────────────────────────────────────────


def test_print_release_summary(capsys: pytest.CaptureFixture):
    rel = Release(
        version="1.1.0",
        tag_name="v1.1.0",
        name="v1.1.0",
        body="## CHANGELOG\n- Wiki 통합\n- 테스트 강화",
        published_at="2026-05-15T00:00:00Z",
        zip_url="https://example.com/x.zip",
    )
    print_release_summary(current="1.0.0", latest=rel)
    out = capsys.readouterr().out
    assert "1.0.0" in out
    assert "1.1.0" in out
    assert "Wiki 통합" in out


def test_print_up_to_date(capsys: pytest.CaptureFixture):
    print_up_to_date(current="1.0.0")
    out = capsys.readouterr().out
    assert "1.0.0" in out
    assert "최신" in out


def test_print_reload_hint(capsys: pytest.CaptureFixture):
    print_reload_hint()
    out = capsys.readouterr().out
    assert "/reload-plugins" in out or "reload" in out.lower()


def test_print_force_reinstall(capsys: pytest.CaptureFixture):
    """--force 동일 버전 안내 메시지."""
    from scripts.update_plugin import print_force_reinstall
    print_force_reinstall(current="1.0.0")
    out = capsys.readouterr().out
    assert "1.0.0" in out
    assert "강제 재설치" in out


def test_confirm_with_user_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert confirm_with_user() is True


def test_confirm_with_user_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert confirm_with_user() is False


def test_confirm_with_user_empty_default_no(monkeypatch):
    """[y/N]에서 Enter만 입력하면 N(취소)."""
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert confirm_with_user() is False


# ── main() 통합 테스트 ────────────────────────────────────────────────────────


def _make_release(version: str, body: str = "") -> dict:
    return {
        "tag_name": f"v{version}",
        "name": f"v{version}",
        "body": body,
        "published_at": "2026-05-15T00:00:00Z",
        "assets": [
            {
                "name": f"techdoc-plugin-v{version}.zip",
                "browser_download_url": f"https://example.com/techdoc-plugin-v{version}.zip",
            }
        ],
    }


def test_main_check_only_up_to_date(fake_plugin_dir: Path, capsys, monkeypatch):
    """--check, 동일 버전: 'up to date' 출력 후 0 리턴."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_make_release("1.0.0"))
    monkeypatch.setattr(
        "scripts.update_plugin._http_transport",
        lambda: httpx.MockTransport(handler),
    )
    code = main(["--check"], plugin_root=fake_plugin_dir)
    assert code == 0
    assert "최신" in capsys.readouterr().out


def test_main_check_only_new_version_no_apply(fake_plugin_dir: Path, fake_release_zip, capsys, monkeypatch):
    """--check, 새 버전: 요약만 출력하고 적용 안 함."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_make_release("1.1.0", body="- new feature"))
    monkeypatch.setattr(
        "scripts.update_plugin._http_transport",
        lambda: httpx.MockTransport(handler),
    )
    code = main(["--check"], plugin_root=fake_plugin_dir)
    assert code == 0
    out = capsys.readouterr().out
    assert "1.1.0" in out
    import json
    data = json.loads((fake_plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"


def test_main_apply_with_user_confirm(fake_plugin_dir: Path, fake_release_zip: Path, monkeypatch):
    """--check 없이, 사용자 'y': 다운로드·적용 후 plugin.json이 v1.1.0으로 갱신."""
    payload = fake_release_zip.read_bytes()

    def api_handler(request: httpx.Request) -> httpx.Response:
        if "/releases/latest" in str(request.url):
            return httpx.Response(200, json=_make_release("1.1.0"))
        return httpx.Response(200, content=payload, headers={"Content-Type": "application/zip"})

    monkeypatch.setattr(
        "scripts.update_plugin._http_transport",
        lambda: httpx.MockTransport(api_handler),
    )
    monkeypatch.setattr("builtins.input", lambda _: "y")
    code = main([], plugin_root=fake_plugin_dir)
    assert code == 0
    import json
    data = json.loads((fake_plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "1.1.0"


def test_main_apply_user_declines(fake_plugin_dir: Path, monkeypatch):
    """사용자 'n': plugin.json 그대로."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_make_release("1.1.0"))
    monkeypatch.setattr(
        "scripts.update_plugin._http_transport",
        lambda: httpx.MockTransport(handler),
    )
    monkeypatch.setattr("builtins.input", lambda _: "n")
    code = main([], plugin_root=fake_plugin_dir)
    assert code == 0
    import json
    data = json.loads((fake_plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"


def test_main_force_same_version_message(fake_plugin_dir: Path, capsys, monkeypatch):
    """--force + 동일 버전: '강제 재설치' 메시지 + '신규 버전 발견' 미출력."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_make_release("1.0.0"))

    monkeypatch.setattr(
        "scripts.update_plugin._http_transport",
        lambda: httpx.MockTransport(handler),
    )
    monkeypatch.setattr("builtins.input", lambda _: "n")
    code = main(["--force"], plugin_root=fake_plugin_dir)
    assert code == 0
    out = capsys.readouterr().out
    assert "강제 재설치" in out
    assert "신규 버전 발견" not in out


# ── Plan B Task 1: SHA-256 검증 (F7) ──────────────────────────────────────────


def test_compute_sha256_matches_known_value(tmp_path):
    """compute_sha256은 표준 hashlib.sha256과 동일한 결과를 낸다."""
    from scripts.update_plugin import compute_sha256
    import hashlib as _hashlib

    f = tmp_path / "sample.bin"
    f.write_bytes(b"hello techdoc")
    expected = _hashlib.sha256(b"hello techdoc").hexdigest()
    assert compute_sha256(f) == expected


def test_verify_sha256_accepts_correct_hash(tmp_path):
    from scripts.update_plugin import verify_sha256
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    correct = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert verify_sha256(f, correct) is True


def test_verify_sha256_rejects_wrong_hash(tmp_path):
    from scripts.update_plugin import verify_sha256
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    assert verify_sha256(f, "0" * 64) is False


def test_verify_sha256_accepts_checksum_file_format(tmp_path):
    """`<hash>  <filename>` 형식의 .sha256 파일 내용도 받는다."""
    from scripts.update_plugin import verify_sha256
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    correct = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    checksum_file_content = f"{correct}  x.bin\n"
    assert verify_sha256(f, checksum_file_content) is True
