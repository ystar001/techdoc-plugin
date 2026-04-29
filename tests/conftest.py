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


@pytest.fixture
def fake_vault_dir(tmp_path: Path) -> Path:
    """비어있는 옵시디언 vault 디렉토리."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def fake_document_final() -> dict:
    """document_final.json의 in-memory 표현 — 카드·별첨·메타 포함."""
    return {
        "title": "노지 스마트농업 기술 분석",
        "subtitle": "보고서 부제",
        "metadata": {
            "date": "2026-04-29",
            "domain": "tech",
            "techdoc_version": "1.0.0",
        },
        "sections": [
            {
                "section_id": "1.1",
                "title": "관개 자동화",
                "html_content": "<h2>관개 자동화</h2><p>본문...</p>",
                "order": 0,
            },
        ],
        "tech_cards": [
            {
                "id": "1.1.1",
                "name": "점적관개",
                "name_en": "Drip Irrigation",
                "importance": "high",
                "section_id": "1.1",
                "overview": "<p>토양·작물 수분에 따른 정밀 급수.</p>",
                "principle": "<p>알고리즘...</p>",
                "components": "<table>...</table>",
                "performance": "<div>효율 85%</div>",
                "pros_cons": "<ul><li>장점</li></ul>",
                "differentiation": "<p>차별점</p>",
                "references": "<p>[REF-001]</p>",
                "ref_ids": ["REF-001", "REF-002"],
                "length_chars": 3120,
                "blocks_fulfilled": 7,
            },
        ],
        "project_cards": [
            {
                "id": "2.1.1",
                "name": "SMART-IRRI-2024",
                "importance": "high",
                "section_id": "2.1",
                "meta": {
                    "institution": "MIT CSAIL",
                    "pi": "Dr. Park",
                    "period": "2023-2025",
                    "budget": "$3.2M",
                    "sponsor": "NSF",
                },
                "background": "<p>배경</p>",
                "organization": "<p>조직</p>",
                "methodology": "<p>방법론</p>",
                "results": "<p>결과 효율 85%</p>",
                "implications": "<p>시사점</p>",
                "followup": "<p>후속</p>",
                "references": "<p>[REF-003]</p>",
                "ref_ids": ["REF-003"],
            },
        ],
        "product_cards": [
            {
                "id": "3.1.1",
                "name": "AgriLink X2",
                "importance": "medium",
                "section_id": "3.1",
                "meta": {"model": "X2", "maker": "AgroTech", "country": "USA"},
                "background": "<p>배경</p>",
                "features": "<p>기능</p>",
                "specifications": "<p>스펙</p>",
                "deployment": "<p>도입</p>",
                "market": "<p>시장</p>",
                "references": "<p>[REF-004]</p>",
                "ref_ids": ["REF-004"],
            },
        ],
        "tech_appendices": [
            {
                "id": "A.1",
                "source_card_id": "1.1.1",
                "type": "tech",
                "name": "점적관개 — 심층분석",
                "overview": "...",
                "theory": "...",
                "algorithms": "...",
                "architecture": "...",
                "benchmark": "...",
                "implementations": "...",
                "timeline": "...",
                "limitations": "...",
                "future": "...",
                "references": "...",
                "length_chars": 24512,
                "blocks_fulfilled": 10,
            },
        ],
        "project_appendices": [],
        "figures": [
            {"id": "fig_1_1", "path": "figures/fig_1_1.png", "caption": "관개 시스템"},
        ],
    }


@pytest.fixture
def fake_reference_list() -> dict:
    """reference_list.json in-memory."""
    return {
        "schema_version": "0.1.0",
        "references": [
            {
                "id": "REF-001",
                "title": "노지 원예농업의 스마트화",
                "source": "한국농촌경제연구원",
                "year": 2024,
                "url": "https://krei.re.kr/...",
                "category": "학술",
                "reliability": "확인됨",
                "file": "KeyRef/001_노지원예농업.md",
            },
        ],
    }


@pytest.fixture
def fake_keyref_dir(tmp_path: Path) -> Path:
    """KeyRef 디렉토리 + 1개 샘플."""
    kr = tmp_path / "KeyRef"
    kr.mkdir()
    (kr / "001_노지원예농업.md").write_text(
        "---\nid: REF-001\ntitle: 노지 원예농업의 스마트화\n---\n\n원문 요약...",
        encoding="utf-8",
    )
    return kr


@pytest.fixture
def fake_outline_glossary() -> dict[str, str]:
    """outline glossary in-memory."""
    return {
        "스마트농업": "ICT를 활용한 정밀 농업",
        "점적관개": "토양·작물 수분 상태에 따른 정밀 급수 방식",
    }
