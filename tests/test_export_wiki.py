"""export_wiki.py 단위·통합 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.wiki.markers import (
    AUTO_START, AUTO_END,
    extract_ai_region, replace_ai_region, has_markers,
)
from scripts.wiki.frontmatter import (
    serialize_frontmatter, parse_frontmatter, split_page,
)
from scripts.wiki.filename import sanitize_name
from scripts.wiki.conflict import (
    extract_facts, detect_conflicts, format_conflict_callout,
)
from scripts.wiki.assets import copy_figures
from scripts.wiki.builders.source import build_source_page, source_filename
from scripts.wiki.builders.entity import (
    build_tech_page, build_project_page, build_product_page, entity_filename,
)


def test_pytest_infra(fake_vault_dir: Path, fake_document_final: dict):
    """fixtures 정상 로드 확인."""
    assert fake_vault_dir.exists()
    assert fake_document_final["title"] == "노지 스마트농업 기술 분석"
    assert len(fake_document_final["tech_cards"]) == 1


def test_markers_constants():
    assert AUTO_START == "<!-- techdoc:auto-start -->"
    assert AUTO_END == "<!-- techdoc:auto-end -->"


def test_has_markers_true():
    page = f"intro\n{AUTO_START}\nai\n{AUTO_END}\nouter"
    assert has_markers(page) is True


def test_has_markers_false():
    assert has_markers("just plain text without markers") is False


def test_extract_ai_region():
    page = f"user note\n{AUTO_START}\nAI managed area\n{AUTO_END}\nmore user note"
    assert extract_ai_region(page) == "AI managed area"


def test_extract_ai_region_no_markers():
    """마커가 없으면 None."""
    assert extract_ai_region("plain page") is None


def test_replace_ai_region_existing():
    """기존 AI 영역 치환, 외부 메모 보존."""
    page = f"USER MEMO TOP\n\n{AUTO_START}\nold ai\n{AUTO_END}\n\nUSER MEMO BOTTOM"
    new = replace_ai_region(page, "new ai content")
    assert "USER MEMO TOP" in new
    assert "USER MEMO BOTTOM" in new
    assert "old ai" not in new
    assert "new ai content" in new
    assert AUTO_START in new
    assert AUTO_END in new


def test_replace_ai_region_no_markers():
    """마커가 없는 페이지면 마커 + AI 영역을 끝에 추가, 기존 내용 100% 보존."""
    page = "USER MEMO\n\nmore notes"
    new = replace_ai_region(page, "ai content")
    assert "USER MEMO" in new
    assert "more notes" in new
    assert AUTO_START in new
    assert AUTO_END in new
    assert "ai content" in new


def test_replace_ai_region_empty_page():
    """빈 페이지 처리."""
    new = replace_ai_region("", "ai content")
    assert AUTO_START in new
    assert "ai content" in new
    assert AUTO_END in new


def test_serialize_frontmatter():
    data = {"type": "tech", "name": "점적관개", "tags": ["smart-farming"]}
    out = serialize_frontmatter(data)
    assert out.startswith("---\n")
    assert out.endswith("---\n")
    assert "type: tech" in out
    assert "점적관개" in out


def test_parse_frontmatter_with_data():
    page = "---\ntype: tech\nname: 점적관개\n---\n\nbody content"
    fm, body = parse_frontmatter(page)
    assert fm == {"type": "tech", "name": "점적관개"}
    assert body.strip() == "body content"


def test_parse_frontmatter_no_frontmatter():
    page = "just body, no frontmatter"
    fm, body = parse_frontmatter(page)
    assert fm == {}
    assert body == "just body, no frontmatter"


def test_split_page_combines():
    """split_page는 frontmatter dict와 body 문자열을 받아 완전한 페이지 생성."""
    fm = {"type": "tech", "name": "점적관개"}
    body = "## 본문\n내용"
    page = split_page(fm, body)
    parsed_fm, parsed_body = parse_frontmatter(page)
    assert parsed_fm == fm
    assert parsed_body.strip() == body


def test_sanitize_name_korean_preserved():
    assert sanitize_name("점적관개") == "점적관개"


def test_sanitize_name_english_preserved():
    assert sanitize_name("Drip Irrigation") == "Drip Irrigation"


def test_sanitize_name_invalid_chars_replaced():
    """Windows 금지 문자: / \\ : * ? " < > |"""
    assert sanitize_name("a/b\\c:d*e?f\"g<h>i|j") == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_name_strips_whitespace():
    assert sanitize_name("  점적관개  ") == "점적관개"


def test_sanitize_name_empty_fallback():
    assert sanitize_name("") == "unnamed"


def test_sanitize_name_only_invalid_fallback():
    assert sanitize_name("////") == "____"


def test_extract_facts_years():
    text = "2024년 시범지구 9개 시군에서 점적관개 도입"
    facts = extract_facts(text)
    assert "2024" in facts["years"]
    assert any("9" in n for n in facts["numbers"])


def test_extract_facts_organizations():
    text = "MIT CSAIL과 한국농촌경제연구원의 협력으로 진행"
    facts = extract_facts(text)
    assert any("MIT CSAIL" in o or "한국농촌경제연구원" in o for o in facts["organizations"])


def test_detect_conflicts_year_mismatch():
    a = {"years": {"2024"}, "numbers": set(), "organizations": set()}
    b = {"years": {"2025"}, "numbers": set(), "organizations": set()}
    conflicts = detect_conflicts(a, b)
    assert len(conflicts) > 0
    assert "year" in conflicts[0]["category"].lower() or "연도" in conflicts[0]["category"]


def test_detect_conflicts_no_conflict():
    a = {"years": {"2024"}, "numbers": {"85%"}, "organizations": {"MIT"}}
    b = {"years": {"2024"}, "numbers": {"85%"}, "organizations": {"MIT"}}
    assert detect_conflicts(a, b) == []


def test_format_conflict_callout():
    conflicts = [
        {
            "category": "연도",
            "values": [
                {"value": "2024", "source": "보고서 A"},
                {"value": "2025", "source": "보고서 B"},
            ],
        }
    ]
    callout = format_conflict_callout(conflicts)
    assert "[!warning]" in callout
    assert "2024" in callout
    assert "2025" in callout


def test_copy_figures(tmp_path: Path, fake_vault_dir: Path):
    """source figures → vault/Assets/figures/<report_slug>/."""
    src = tmp_path / "src_figures"
    src.mkdir()
    (src / "fig_1_1.png").write_bytes(b"fake png")
    (src / "fig_1_2.svg").write_bytes(b"<svg/>")

    copied = copy_figures(src, fake_vault_dir, report_slug="노지스마트농업")
    target = fake_vault_dir / "Assets" / "figures" / "노지스마트농업"
    assert target.exists()
    assert (target / "fig_1_1.png").read_bytes() == b"fake png"
    assert (target / "fig_1_2.svg").read_bytes() == b"<svg/>"
    assert len(copied) == 2


def test_copy_figures_missing_source(fake_vault_dir: Path, tmp_path: Path):
    """source 디렉토리가 없으면 빈 리스트 반환 (에러 아님)."""
    nonexistent = tmp_path / "nope"
    copied = copy_figures(nonexistent, fake_vault_dir, report_slug="x")
    assert copied == []


def test_source_filename():
    ref = {"id": "REF-001", "title": "노지 원예농업의 스마트화 실태와 과제"}
    name = source_filename(ref)
    assert name.startswith("REF-001_")
    assert name.endswith(".md")


def test_build_source_page_new(fake_keyref_dir: Path, fake_reference_list: dict):
    ref = fake_reference_list["references"][0]
    page = build_source_page(ref, keyref_dir=fake_keyref_dir, existing_page=None)
    # frontmatter
    assert "type: source" in page
    assert "REF-001" in page
    assert "확인됨" in page or "confirmed" in page
    # 본문에 KeyRef 원문 요약이 들어옴
    assert "원문 요약" in page or "KeyRef" in page
    # AI 영역 마커 존재
    from scripts.wiki.markers import AUTO_START
    assert AUTO_START in page


def test_build_source_page_idempotent(fake_keyref_dir: Path, fake_reference_list: dict):
    """같은 ref로 두 번 호출하면 결과가 같아야 한다 (멱등)."""
    ref = fake_reference_list["references"][0]
    p1 = build_source_page(ref, keyref_dir=fake_keyref_dir, existing_page=None)
    p2 = build_source_page(ref, keyref_dir=fake_keyref_dir, existing_page=p1)
    # frontmatter·AI 영역은 동일 (멱등)
    from scripts.wiki.frontmatter import parse_frontmatter
    fm1, _ = parse_frontmatter(p1)
    fm2, _ = parse_frontmatter(p2)
    assert fm1 == fm2


def test_entity_filename():
    card = {"name": "점적관개"}
    assert entity_filename(card) == "점적관개.md"


def test_build_tech_page(fake_document_final: dict):
    card = fake_document_final["tech_cards"][0]
    page = build_tech_page(card, report_title="노지 스마트농업", existing_page=None)
    assert "type: tech" in page
    assert "점적관개" in page
    assert "Drip Irrigation" in page  # name_en
    assert "high" in page  # importance


def test_build_project_page_meta(fake_document_final: dict):
    card = fake_document_final["project_cards"][0]
    page = build_project_page(card, report_title="노지 스마트농업", existing_page=None)
    assert "type: project" in page
    assert "MIT CSAIL" in page  # institution
    assert "$3.2M" in page  # budget


def test_build_product_page_meta(fake_document_final: dict):
    card = fake_document_final["product_cards"][0]
    page = build_product_page(card, report_title="노지 스마트농업", existing_page=None)
    assert "type: product" in page
    assert "AgroTech" in page  # maker
    assert "USA" in page  # country


def test_build_tech_page_with_appendix_link(fake_document_final: dict):
    """별첨이 있는 카드는 frontmatter appendix 필드 + 본문 표준 마크다운 링크."""
    card = fake_document_final["tech_cards"][0]  # id=1.1.1, appendix A.1 존재
    page = build_tech_page(
        card,
        report_title="노지 스마트농업",
        existing_page=None,
        has_appendix=True,
    )
    assert "appendix:" in page or "_appendix" in page
    assert "심층분석 별첨" in page  # 콜아웃 헤더
    assert "_appendix.md)" in page  # 표준 마크다운 링크
