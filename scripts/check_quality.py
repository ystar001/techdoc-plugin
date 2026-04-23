"""Phase A 품질 검증 (결정론적 측정 23개 항목).

항목 분류:
  기본 12개: 섹션 길이·컴포넌트·인용 수·AI추정 비율·서술 형식·용어 일치 등
  기술연구 5개: 대학·기업·연구기관 패턴 (REQ-012~014)
  카드 시스템 6개: 섹션당 카드 수·블록 충족률·최소 길이·종합분석 블록

사용법:
    python -m scripts.check_quality --input ./output/document_final.json \
        --refs ./output/reference_list.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from techdoc_core.constants import (
    CARD_LENGTH_RULES,
    CARDS_PER_SECTION,
    MAX_AI_ESTIMATE_RATIO,
    MIN_REF_PER_SECTION,
    MIN_SECTION_LENGTH,
)
from techdoc_core.models import Document
from techdoc_core.schemas import QualityIssueSchema

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html: str) -> str:
    return TAG_RE.sub("", html or "").strip()


def count_citations(html: str) -> int:
    return len(re.findall(r"\[REF-\d{3}\]", html or ""))


def count_ai_estimates(html: str) -> int:
    """AI 추정 표현 패턴 검출."""
    patterns = (
        r"~로 알려져 있다",
        r"~할 것으로 보인다",
        r"~로 추정된다",
        r"~라고 한다",
        r"것으로 알려졌다",
    )
    count = 0
    for pat in patterns:
        count += len(re.findall(pat.replace("~", "[가-힣]+"), html or ""))
    return count


def check_institution_number_pattern(html: str) -> int:
    """대학·기업·연구기관 + 수치 패턴 (REQ-012~014)."""
    text = strip_html(html)
    # "XX대학" 또는 "XX Univ" + 숫자%/수치
    uni_pat = re.compile(r"(?:[가-힣A-Za-z]{2,}\s*(?:대학|Univ|University))[^.!?]{0,200}\d+\.?\d*\s*(?:%|%p|배|건)")
    corp_pat = re.compile(r"(?:[가-힣A-Z][가-힣A-Za-z]{1,}\s*(?:연구소|Research|R&D|Labs|AI))[^.!?]{0,200}\d+")
    return len(uni_pat.findall(text)) + len(corp_pat.findall(text))


def check_product_pattern(html: str) -> int:
    """기업명 + 제품·모델명 + 스펙 패턴."""
    text = strip_html(html)
    # 영문 제품명 + 숫자 스펙
    pat = re.compile(r"[A-Z][a-zA-Z]+[-\s]?[\w\d]+[^.!?]{0,200}\d+\.?\d*\s*(?:GHz|MHz|nm|W|kW|dB|kbps|Mbps|Gbps)")
    return len(pat.findall(text))


def check_project_pattern(html: str) -> int:
    """연구기관 + 프로젝트명 + 기간·예산 패턴."""
    text = strip_html(html)
    # 연도 범위 (2020-2025 등) + 기관
    pat = re.compile(r"20\d{2}\s*[-~]\s*20\d{2}[^.!?]{0,100}(?:프로젝트|Project|연구|Research)")
    return len(pat.findall(text))


def measure_document(document: Document, reference_list: dict | None = None) -> dict:
    """Phase A 23개 지표 측정."""
    metrics: dict = {}
    issues: list[QualityIssueSchema] = []

    # ── 기본 12개 ──
    all_content = " ".join(s.html_content or "" for s in document.sections)
    total_citations = count_citations(all_content)
    total_ai_estimates = count_ai_estimates(all_content)
    total_text = strip_html(all_content)
    word_count = len(total_text)

    metrics["total_sections"] = len(document.sections)
    metrics["total_word_count"] = word_count
    metrics["total_citations"] = total_citations
    metrics["ai_estimate_count"] = total_ai_estimates
    metrics["ai_estimate_ratio"] = round(total_ai_estimates / max(1, total_citations), 3)

    # 섹션별 검증
    short_sections = 0
    low_citation_sections = 0
    for sec in document.sections:
        text = strip_html(sec.html_content or "")
        if len(text) < MIN_SECTION_LENGTH:
            short_sections += 1
            issues.append(QualityIssueSchema(
                metric="section_length",
                severity="FAIL",
                section_id=sec.section_id,
                expected=f">={MIN_SECTION_LENGTH}",
                actual=str(len(text)),
                action=f"섹션 {sec.section_id} 재작성",
            ))
        sec_cites = count_citations(sec.html_content or "")
        if sec_cites < MIN_REF_PER_SECTION:
            low_citation_sections += 1
            issues.append(QualityIssueSchema(
                metric="section_citations",
                severity="WARNING",
                section_id=sec.section_id,
                expected=f">={MIN_REF_PER_SECTION}",
                actual=str(sec_cites),
            ))

    metrics["short_sections"] = short_sections
    metrics["low_citation_sections"] = low_citation_sections
    metrics["has_h2_all"] = all("<h2" in (s.html_content or "") for s in document.sections)

    if metrics["ai_estimate_ratio"] > MAX_AI_ESTIMATE_RATIO:
        issues.append(QualityIssueSchema(
            metric="ai_estimate_ratio",
            severity="FAIL",
            expected=f"<={MAX_AI_ESTIMATE_RATIO}",
            actual=str(metrics["ai_estimate_ratio"]),
            action="근거 미확인 문장 제거",
        ))

    # ── 기술연구 5개 ──
    tech_patterns = sum(check_institution_number_pattern(s.html_content or "") for s in document.sections)
    product_patterns = sum(check_product_pattern(s.html_content or "") for s in document.sections)
    project_patterns = sum(check_project_pattern(s.html_content or "") for s in document.sections)

    metrics["tech_institution_number_patterns"] = tech_patterns
    metrics["product_spec_patterns"] = product_patterns
    metrics["project_period_patterns"] = project_patterns

    if reference_list:
        cat_counts = {c["category"]: c["count"] for c in reference_list.get("category_coverage", [])}
        total = reference_list.get("total_refs", 1)
        academic_ratio = cat_counts.get("학술", 0) / total
        rd_ratio = cat_counts.get("기업R&D", 0) / total
        metrics["academic_ratio"] = round(academic_ratio, 3)
        metrics["rd_ratio"] = round(rd_ratio, 3)

        if academic_ratio < 0.35:
            issues.append(QualityIssueSchema(
                metric="academic_ratio",
                severity="FAIL",
                expected=">=0.35",
                actual=str(metrics["academic_ratio"]),
                action="학술 레퍼런스 추가 (arxiv·IEEE·ACM·RISS)",
            ))
        if rd_ratio < 0.24:
            issues.append(QualityIssueSchema(
                metric="rd_ratio",
                severity="FAIL",
                expected=">=0.24",
                actual=str(metrics["rd_ratio"]),
                action="기업 R&D 레퍼런스 추가",
            ))

    # ── 카드 시스템 6개 ──
    tech_min, tech_max = CARDS_PER_SECTION["tech"]
    proj_min, proj_max = CARDS_PER_SECTION["project"]

    section_ids = [s.section_id for s in document.sections]
    sections_with_tech_cards: dict[str, int] = {sid: 0 for sid in section_ids}
    sections_with_project_cards: dict[str, int] = {sid: 0 for sid in section_ids}

    for c in document.tech_cards:
        sid = ".".join(c.id.split(".")[:2])
        if sid in sections_with_tech_cards:
            sections_with_tech_cards[sid] += 1
    for c in document.project_cards:
        sid = ".".join(c.id.split(".")[:2])
        if sid in sections_with_project_cards:
            sections_with_project_cards[sid] += 1

    under_tech = [sid for sid, cnt in sections_with_tech_cards.items() if cnt < tech_min]
    under_proj = [sid for sid, cnt in sections_with_project_cards.items() if cnt < proj_min]
    metrics["tech_card_total"] = len(document.tech_cards)
    metrics["project_card_total"] = len(document.project_cards)
    metrics["product_card_total"] = len(document.product_cards)
    metrics["sections_under_tech_min"] = len(under_tech)
    metrics["sections_under_project_min"] = len(under_proj)

    for sid in under_tech:
        issues.append(QualityIssueSchema(
            metric="tech_cards_per_section",
            severity="WARNING",
            section_id=sid,
            expected=f">={tech_min}",
            actual=str(sections_with_tech_cards[sid]),
        ))

    # 카드 7블록 충족률
    def tech_card_blocks_score(card) -> float:
        fields = ("overview", "principle", "components", "performance",
                  "pros_cons", "differentiation", "references")
        filled = sum(1 for f in fields if getattr(card, f, "").strip())
        return filled / len(fields)

    def project_card_blocks_score(card) -> float:
        fields = ("background", "organization", "methodology", "results",
                  "implications", "followup", "references")
        filled = sum(1 for f in fields if getattr(card, f, "").strip())
        return filled / len(fields)

    tech_fill = [tech_card_blocks_score(c) for c in document.tech_cards]
    proj_fill = [project_card_blocks_score(c) for c in document.project_cards]
    metrics["tech_card_block_fill_avg"] = round(sum(tech_fill) / max(1, len(tech_fill)), 3)
    metrics["project_card_block_fill_avg"] = round(sum(proj_fill) / max(1, len(proj_fill)), 3)

    if metrics["tech_card_block_fill_avg"] < 0.85 and document.tech_cards:
        issues.append(QualityIssueSchema(
            metric="tech_card_block_fill",
            severity="FAIL",
            expected=">=0.85",
            actual=str(metrics["tech_card_block_fill_avg"]),
            action="기술 카드 7블록 보완",
        ))

    # 카드 최소 길이
    def tech_card_len(c) -> int:
        return sum(len(strip_html(getattr(c, f, ""))) for f in
                   ("overview", "principle", "components", "performance", "pros_cons", "differentiation"))

    def project_card_len(c) -> int:
        return sum(len(strip_html(getattr(c, f, ""))) for f in
                   ("background", "organization", "methodology", "results", "implications", "followup"))

    undersized_tech = sum(1 for c in document.tech_cards if tech_card_len(c) < CARD_LENGTH_RULES["tech"]["min"])
    undersized_project = sum(1 for c in document.project_cards if project_card_len(c) < CARD_LENGTH_RULES["project"]["min"])
    metrics["undersized_tech_cards"] = undersized_tech
    metrics["undersized_project_cards"] = undersized_project

    if undersized_tech > 0:
        issues.append(QualityIssueSchema(
            metric="undersized_tech_cards",
            severity="FAIL",
            expected="0",
            actual=str(undersized_tech),
            action=f"기술 카드 {undersized_tech}개 분량 확대 (최소 {CARD_LENGTH_RULES['tech']['min']}자)",
        ))

    # 종합 분석 블록 존재 여부
    sections_without_analysis = sum(
        1 for s in document.sections
        if s.html_content and "section-summary" not in s.html_content
        and "종합 분석" not in s.html_content and "종합분석" not in s.html_content
    )
    metrics["sections_without_analysis_block"] = sections_without_analysis

    # 종합
    total_fail = sum(1 for i in issues if i.severity == "FAIL")
    total_warning = sum(1 for i in issues if i.severity == "WARNING")
    overall = 5.0 - min(5.0, total_fail * 0.5 + total_warning * 0.1)

    return {
        "schema_version": "0.1.0",
        "phase_a": metrics,
        "issues": [i.model_dump() for i in issues],
        "total_fail": total_fail,
        "total_warning": total_warning,
        "overall": round(overall, 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase A quality check (23 metrics)")
    ap.add_argument("-i", "--input", required=True, help="document_final.json")
    ap.add_argument("--refs", help="reference_list.json (학술·R&D 비율 체크)")
    ap.add_argument("-o", "--output", default="./output/quality_report.json", help="리포트 저장 경로")
    args = ap.parse_args()

    doc = Document.load(Path(args.input))
    refs = None
    if args.refs and Path(args.refs).exists():
        refs = json.loads(Path(args.refs).read_text(encoding="utf-8"))

    result = measure_document(doc, refs)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {out_path}")
    print(f"  overall: {result['overall']} / 5.0")
    print(f"  FAIL: {result['total_fail']}, WARNING: {result['total_warning']}")
    print(f"  tech_cards: {result['phase_a']['tech_card_total']}, project: {result['phase_a']['project_card_total']}, product: {result['phase_a']['product_card_total']}")

    if result["total_fail"] > 0:
        return 2  # FAIL 가드
    return 0


if __name__ == "__main__":
    sys.exit(main())
