"""export-wiki 후처리(F18) 회귀 테스트.

톤 정리·메타 제거·긴 문단 분리·slug 한국어화·문서 안내·enhance 통합.
[REF-xxx]·수치·고유명사 보존, 멱등성을 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import export_wiki
from scripts.wiki.postprocess import (
    build_guide_section,
    enhance_markdown,
    koreanize_slug,
    soften_tone,
    split_long_paragraphs,
    strip_meta_markers,
)


def test_soften_tone_replaces_academic_modifiers():
    assert soften_tone("학술 framework 기반") == "프레임워크 기반"
    assert soften_tone("학술 baseline 대비") == "기준선 대비"
    assert "학술 " not in soften_tone("학술 deep dive 수행")


def test_soften_tone_preserves_ref_and_numbers():
    src = "정확도 95.3% 달성 [REF-023]."
    assert soften_tone(src) == src  # 수치·REF 보존


def test_strip_meta_markers_removes_expansion_label():
    assert strip_meta_markers("## 핵심 개념 (확장)") == "## 핵심 개념"
    assert strip_meta_markers("## 배경 (보강)") == "## 배경"


def test_split_long_paragraphs_uses_paragraph_util():
    # 800자 ceiling 초과 입력 → 강제 분리 (paragraph.format_paragraphs 재사용)
    long = ("한 문장이다. " * 200).strip()
    out = split_long_paragraphs(long)
    assert "\n\n" in out  # 800자 ceiling 분리


def test_koreanize_slug_replaces_known_english():
    assert koreanize_slug("framework 설계") == "프레임워크 설계"
    # 고유명사·제품명은 보존
    assert koreanize_slug("Climate FieldView 연동") == "Climate FieldView 연동"


def test_build_guide_section_for_long_doc():
    body = "# 제목\n\n## 절1\n본문\n\n## 절2\n본문"
    guide = build_guide_section(body, min_chars=5)
    assert "안내" in guide and "절1" in guide  # H2 미리보기 포함


def test_enhance_markdown_idempotent():
    src = "## 개념 (확장)\n\n학술 framework 기반 [REF-1]."
    once = enhance_markdown(src)
    assert enhance_markdown(once) == once  # 멱등
    assert "학술 framework" not in once and "[REF-1]" in once


# --- Task 3: export_wiki --enhance hook 통합 ---


def _minimal_doc() -> dict:
    """학술 수식어·REF·수치를 담은 최소 document_final.json."""
    return {
        "title": "후처리 통합 테스트",
        "metadata": {"date": "2026-06-03", "domain": "tech"},
        "tech_cards": [
            {
                "id": "1.1.1",
                "name": "점적관개",
                "importance": "high",
                "section_id": "1.1",
                "overview": "학술 framework 기반 정확도 95.3% 달성 [REF-001].",
                "references": "[REF-001]",
                "ref_ids": ["REF-001"],
            }
        ],
        "project_cards": [],
        "product_cards": [],
        "tech_appendices": [],
        "project_appendices": [],
        "figures": [],
    }


def _write_doc(doc_dir: Path, doc: dict) -> None:
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "document_final.json").write_text(
        json.dumps(doc, ensure_ascii=False), encoding="utf-8"
    )


def test_export_wiki_enhance_softens_tone(tmp_path):
    doc_dir = tmp_path / "out"
    vault = tmp_path / "vault"
    _write_doc(doc_dir, _minimal_doc())

    rc = export_wiki.main(
        ["--doc", str(doc_dir), "--vault", str(vault), "--create-vault"]
    )
    assert rc == 0

    card = (vault / "Tech" / "점적관개.md").read_text(encoding="utf-8")
    assert "학술 framework" not in card  # 톤 정리 적용됨
    assert "프레임워크" in card
    assert "[REF-001]" in card  # REF 보존
    assert "95.3%" in card  # 수치 보존


def test_export_wiki_no_enhance_preserves_raw(tmp_path):
    doc_dir = tmp_path / "out"
    vault = tmp_path / "vault"
    _write_doc(doc_dir, _minimal_doc())

    rc = export_wiki.main(
        ["--doc", str(doc_dir), "--vault", str(vault), "--create-vault", "--no-enhance"]
    )
    assert rc == 0

    card = (vault / "Tech" / "점적관개.md").read_text(encoding="utf-8")
    assert "학술 framework" in card  # 후처리 비활성 → 원문 그대로
