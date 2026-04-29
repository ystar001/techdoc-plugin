"""export_wiki.py 단위·통합 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_pytest_infra(fake_vault_dir: Path, fake_document_final: dict):
    """fixtures 정상 로드 확인."""
    assert fake_vault_dir.exists()
    assert fake_document_final["title"] == "노지 스마트농업 기술 분석"
    assert len(fake_document_final["tech_cards"]) == 1
