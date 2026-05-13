"""Plan C — preflight permission check (F6) tests."""

from __future__ import annotations

import os

import pytest


def test_check_write_permission_passes_on_writable_dir(tmp_path):
    from scripts.preflight import check_write_permission

    ok, reason = check_write_permission(tmp_path)
    assert ok is True
    assert "OK" in reason or reason == ""


def test_check_write_permission_creates_no_residue(tmp_path):
    from scripts.preflight import check_write_permission

    check_write_permission(tmp_path)
    # preflight는 임시 파일을 정리해야 함
    assert list(tmp_path.iterdir()) == []


def test_check_write_permission_creates_parent_if_missing(tmp_path):
    from scripts.preflight import check_write_permission

    nested = tmp_path / "deep" / "nested" / "out"
    ok, _ = check_write_permission(nested)
    assert ok is True
    assert nested.exists()
    # 정리 확인
    assert list(nested.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX chmod semantics only")
def test_check_write_permission_fails_on_readonly(tmp_path):
    from scripts.preflight import check_write_permission

    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(0o555)  # read+execute, no write
    try:
        ok, reason = check_write_permission(readonly)
        assert ok is False
        assert reason  # 비어있지 않은 사유
    finally:
        readonly.chmod(0o755)  # cleanup
