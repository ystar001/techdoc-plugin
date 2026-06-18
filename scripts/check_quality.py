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

from scripts.extract_glossary import (
    _looks_like_abbr,
    find_abbreviations,
    find_explanation_pairs,
)
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


# ── 표기 일관성 지표 (F16, Plan H) ──────────────────────────────────────────
#
# extract_glossary 의 약어 정규식·페어 추출을 재사용(상단 import).
# LLM 호출 0회·결정론적. glossary 미제공 시 두 지표 모두 0.

# 외래어 표준안 ↔ 흔한 변형 사전 (국립국어원 외래어 표기법 기준 일부).
# key = 표준어, value = 본문에서 발견 시 비표준으로 카운트할 변형 목록.
_KNOWN_VARIANTS: dict[str, tuple[str, ...]] = {
    "데이터": ("데이타",),
    "센서": ("센써",),
    "메시지": ("메세지",),
    "로봇": ("로보트",),
    "디지털": ("디지탈",),
    "콘텐츠": ("컨텐츠", "컨텐트"),
    "알고리즘": ("알고리듬",),
    "네트워크": ("네트웍",),
}


def check_abbreviation_consistency(html: str, defined: set | None = None) -> int:
    """풀이 없이 처음 등장한 미정의 약어 수.

    `정식명(ABBR)` 풀이 페어로 본문에서 정의됐거나 `defined`(대문자 집합)에 있으면 정의됨.
    그 외 약어는 미정의로 카운트(약어 종류 기준, 등장 횟수 아님).
    """
    text = strip_html(html)
    defined_upper = {d.upper() for d in (defined or set())}
    # 본문 내 풀이 페어로 정의된 약어
    for pair in find_explanation_pairs(text):
        defined_upper.add(pair["abbr"].upper())

    undefined: set[str] = set()
    for abbr in find_abbreviations(text):
        if not _looks_like_abbr(abbr):
            continue
        if abbr.upper() in defined_upper:
            continue
        undefined.add(abbr.upper())
    return len(undefined)


def check_terminology_consistency(text: str, glossary: dict | None = None) -> int:
    """glossary 표준어의 알려진 변형이 본문에 등장한 횟수.

    내장 변형 사전(_KNOWN_VARIANTS) + glossary 키를 표준어로 간주.
    표준어에 변형이 등록돼 있고 그 변형이 본문에 나타나면 카운트.

    참고: _KNOWN_VARIANTS(예: 데이타→데이터)는 국립국어원 표기 기준이라
    glossary와 무관하게 검사한다. 따라서 이 지표는 abbreviation 지표와 달리
    glossary 미제공 시에도 발화할 수 있다(의도된 비대칭). 단 WARNING이라
    FAIL/exit code에는 영향 없음.
    """
    plain = strip_html(text)
    glossary = glossary or {}
    count = 0
    # glossary 키 + 내장 사전의 표준어를 검사 대상으로
    standards = set(_KNOWN_VARIANTS) | set(glossary.keys())
    for std in standards:
        variants = _KNOWN_VARIANTS.get(std, ())
        for variant in variants:
            count += plain.count(variant)
    return count


def measure_document(
    document: Document,
    reference_list: dict | None = None,
    glossary: dict | None = None,
) -> dict:
    """Phase A 23개 지표 + 표기 일관성 2개 측정.

    glossary 미제공 시 표기 일관성 지표는 0(기존 흐름 무변경).
    """
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

    # ── 표기 일관성 2개 (F16) ──
    # glossary 미제공 시 두 지표 모두 0 (기존 흐름 무변경).
    glossary = glossary or {}
    defined_abbrs = {str(k).upper() for k in glossary}
    undefined_abbreviations = check_abbreviation_consistency(all_content, defined=defined_abbrs)
    terminology_inconsistencies = check_terminology_consistency(all_content, glossary=glossary)
    metrics["undefined_abbreviations"] = undefined_abbreviations
    metrics["terminology_inconsistencies"] = terminology_inconsistencies

    # 임계: 미정의 약어 3종 초과 / 표기 변형 1회 이상 → medium WARN
    if glossary and undefined_abbreviations > 3:
        issues.append(QualityIssueSchema(
            metric="undefined_abbreviations",
            severity="WARNING",
            expected="<=3",
            actual=str(undefined_abbreviations),
            action="첫 등장 약어 풀이(정식명(ABBR)) 추가 또는 glossary 보강",
        ))
    if terminology_inconsistencies > 0:
        issues.append(QualityIssueSchema(
            metric="terminology_inconsistencies",
            severity="WARNING",
            expected="0",
            actual=str(terminology_inconsistencies),
            action="외래어 표준 표기로 통일 (terminology_rules 참조)",
        ))

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
    tech_min, _tech_max = CARDS_PER_SECTION["tech"]
    proj_min, _proj_max = CARDS_PER_SECTION["project"]

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


# ── Self-model 모드 지원 (F5, v1.1.3+) ─────────────────────────────────────
#
# 기존 measure_document는 standard 모드(document_final.json) 전용.
# Self-model 카드(`output/cards/<id>_card.json`)는 schema가 달라 처리 불가했음.
# 아래 entry point는 openfieldtech scripts/verify_cards.py 패턴을 흡수해
# self-model 카드 디렉토리도 23지표 framework 일부로 자동 검사한다.

# F1 변형 본문 키 (재귀 합산 시 사용 — body·narrative·content)
BODY_KEYS = {"body", "narrative", "content", "text", "summary"}

# 사이즈별 본문 글자 임계 (verify_cards.py에서 흡수)
SIZE_THRESHOLDS = {"S": 14000, "L1": 7000, "L2": 10000, "L3": 5000, "?": 8000}

CALL_ID_PAT = re.compile(r"^(\d+\.\d+)(?:\.(L\d|XL\d|S))?$")


def _parse_call_id(stem: str) -> str:
    """파일명에서 사이즈 grade 추출 (예: '1.1' → S, '1.1.L2' → L2)."""
    s = stem.replace("_card", "")
    m = CALL_ID_PAT.match(s)
    if not m or m.group(2) is None:
        return "S"
    g2 = m.group(2)
    if g2.startswith("L"):
        return f"L{g2[1:]}"
    return "S"


def _collect_body_chars(node) -> int:
    """node 안의 모든 본문 문자열 길이 합산 (F1 robust)."""
    if isinstance(node, dict):
        total = 0
        for k, v in node.items():
            if k in BODY_KEYS and isinstance(v, str):
                total += len(v)
            else:
                total += _collect_body_chars(v)
        return total
    if isinstance(node, list):
        return sum(_collect_body_chars(x) for x in node)
    return 0


def _collect_body_text(node) -> str:
    """section value에서 본문 markdown만 추출 (F1 변형 robust, title 등 비-본문 키 제외).

    - str 직접 → 그대로 (자식 schema: sections[k] == 본문 문자열)
    - dict → BODY_KEYS(body/narrative/content/...) 문자열만 + dict/list 컨테이너만 재귀
      (title 같은 비-본문 leaf 문자열은 무시 → 헤딩이 형식 분석에 섞이지 않음)
    - list → 요소 재귀 연결
    """
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        parts = []
        for k, v in node.items():
            if k in BODY_KEYS and isinstance(v, str):
                parts.append(v)
            elif isinstance(v, (dict, list)):
                parts.append(_collect_body_text(v))
        return "\n".join(p for p in parts if p)
    if isinstance(node, list):
        return "\n".join(_collect_body_text(x) for x in node)
    return ""


def _check_self_model_card(card_path: Path, baseline_path=None, strict=False, tolerance=0.15) -> dict:
    """self-model 카드 1건 검사 (사이즈 임계 + 서식 게이트)."""
    from scripts import format_gate

    issues: list[dict] = []
    try:
        data = json.loads(card_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {
            "path": str(card_path),
            "status": "FAIL",
            "size": "?",
            "chars": 0,
            "issues": [{"severity": "FAIL", "msg": f"JSON parse 실패: {e}"}],
            "format": {},
        }

    size = _parse_call_id(card_path.stem)
    chars = _collect_body_chars(data)
    threshold = SIZE_THRESHOLDS.get(size, 8000)

    if chars < threshold * 0.5:
        issues.append({
            "severity": "FAIL",
            "msg": f"본문 매우 부족: {chars}자 (임계 {threshold} 절반 미만)",
        })
    elif chars < threshold:
        issues.append({
            "severity": "WARNING",
            "msg": f"본문 부족: {chars}자 (임계 {threshold})",
        })

    # 서식 게이트 (format_gate)
    sections = data.get("sections", {})
    sec_text = (
        {k: _collect_body_text(v) for k, v in sections.items()}
        if isinstance(sections, dict) else {}
    )
    base_text = None
    if baseline_path is not None:
        bp = Path(baseline_path)
        if not bp.exists():
            issues.append({"severity": "WARNING", "metric": "baseline",
                           "msg": f"baseline 카드 없음: {bp}"})
        else:
            try:
                bdata = json.loads(bp.read_text(encoding="utf-8"))
                bsec = bdata.get("sections", {})
                base_text = (
                    {k: _collect_body_text(v) for k, v in bsec.items()}
                    if isinstance(bsec, dict) else {}
                )
            except (OSError, json.JSONDecodeError):
                issues.append({"severity": "WARNING", "metric": "baseline",
                               "msg": f"baseline 파싱 실패: {bp}"})
    fmt = format_gate.measure_format(sec_text, base_text, strict=strict, tolerance=tolerance)
    issues.extend(fmt["issues"])

    status = (
        "FAIL" if any(i["severity"] == "FAIL" for i in issues)
        else ("WARNING" if issues else "PASS")
    )
    return {
        "path": str(card_path),
        "status": status,
        "size": size,
        "chars": chars,
        "issues": issues,
        "format": fmt["metrics"],
    }


def measure_self_model(output_dir: Path, baseline_dir=None, strict=False, tolerance=0.15) -> dict:
    """self-model 모드 — cards/*_card.json 일괄 검사 (사이즈 + 서식 게이트)."""
    output_dir = Path(output_dir)
    cards_dir = output_dir / "cards"
    card_files = sorted(cards_dir.glob("*_card.json"))
    results = []
    for p in card_files:
        bpath = (Path(baseline_dir) / p.name) if baseline_dir else None
        results.append(_check_self_model_card(p, bpath, strict, tolerance))

    total_fail = sum(1 for c in results if c["status"] == "FAIL")
    total_warning = sum(1 for c in results if c["status"] == "WARNING")

    def _has_format_issue(card, sev):
        return any(i.get("metric") and i["severity"] == sev for i in card.get("issues", []))

    format_warn_cards = sum(1 for c in results if _has_format_issue(c, "WARNING"))
    format_fail_cards = sum(1 for c in results if _has_format_issue(c, "FAIL"))
    overall = 5.0 - min(5.0, total_fail * 0.5 + total_warning * 0.1)
    return {
        "schema_version": "0.1.0",
        "mode": "self_model",
        "phase_a": {
            "total_cards": len(card_files),
            "PASS": sum(1 for c in results if c["status"] == "PASS"),
            "WARNING": total_warning,
            "FAIL": total_fail,
            "format_warn_cards": format_warn_cards,
            "format_fail_cards": format_fail_cards,
        },
        "cards": results,
        "total_fail": total_fail,
        "total_warning": total_warning,
        "overall": round(overall, 2),
    }


def _load_glossary(output_dir: Path) -> dict:
    """draft_outline.json 의 glossary(flat dict) 우선, 없으면 빈 dict.

    glossary 미존재 시 표기 일관성 지표는 0(기존 흐름 무변경).
    """
    outline_path = output_dir / "draft_outline.json"
    if outline_path.exists():
        try:
            data = json.loads(outline_path.read_text(encoding="utf-8"))
            g = data.get("glossary")
            if isinstance(g, dict):
                return g
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def run_quality_check(output_dir: Path, baseline_dir=None, strict=False, tolerance=0.15) -> dict:
    """mode 자동 판별 후 적절한 측정 함수로 라우팅 (v1.1.3+ entry point).

    standard 모드는 document_final.json·reference_list.json을 기대;
    self_model 모드는 cards/*_card.json을 기대. baseline/strict/tolerance는 self_model 전용.
    """
    from scripts.card_layout import detect_mode

    output_dir = Path(output_dir)
    mode = detect_mode(output_dir)
    if mode == "self_model":
        return measure_self_model(output_dir, baseline_dir, strict, tolerance)
    if mode == "standard":
        doc_path = output_dir / "document_final.json"
        if not doc_path.exists():
            doc_path = output_dir / "document_draft.json"
        if not doc_path.exists():
            return {
                "schema_version": "0.1.0",
                "mode": "standard",
                "error": "document_final.json도 document_draft.json도 없습니다.",
                "total_fail": 1,
                "total_warning": 0,
                "overall": 0.0,
            }
        doc = Document.load(doc_path)
        refs_path = output_dir / "reference_list.json"
        refs = None
        if refs_path.exists():
            refs = json.loads(refs_path.read_text(encoding="utf-8"))
        glossary = _load_glossary(output_dir)
        result = measure_document(doc, refs, glossary)
        result["mode"] = "standard"
        return result
    return {
        "schema_version": "0.1.0",
        "mode": "unknown",
        "total_fail": 0,
        "total_warning": 0,
        "overall": 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase A quality check (23 metrics)")
    ap.add_argument(
        "-i", "--input",
        help="document_final.json (standard 모드) 또는 output_dir (자동 판별)",
    )
    ap.add_argument("--refs", help="reference_list.json (학술·R&D 비율 체크)")
    ap.add_argument(
        "-o", "--output", default="./output/quality_report.json",
        help="리포트 저장 경로",
    )
    ap.add_argument("--baseline", help="self_model 회귀 검사용 보완 전 카드 디렉토리")
    ap.add_argument("--strict", action="store_true", help="서식 구조 결함을 FAIL로 승격")
    ap.add_argument("--tolerance", type=float, default=0.15,
                    help="분량 회귀 허용 비율 (기본 0.15)")
    args = ap.parse_args()

    if not args.input:
        ap.error("--input 인자가 필요합니다 (document JSON 또는 output 디렉토리)")

    input_path = Path(args.input)
    if input_path.is_dir():
        # v1.1.3+ self-model/standard 자동 판별 모드
        result = run_quality_check(input_path, args.baseline, args.strict, args.tolerance)
    else:
        # 기존 동작 — document_final.json 직접 지정
        doc = Document.load(input_path)
        refs = None
        if args.refs and Path(args.refs).exists():
            refs = json.loads(Path(args.refs).read_text(encoding="utf-8"))
        result = measure_document(doc, refs)
        result["mode"] = "standard"

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"OK: {out_path}")
    print(f"  mode: {result.get('mode', 'standard')}")
    print(f"  overall: {result.get('overall', 0)} / 5.0")
    print(f"  FAIL: {result.get('total_fail', 0)}, WARNING: {result.get('total_warning', 0)}")
    if "phase_a" in result and "tech_card_total" in result["phase_a"]:
        pa = result["phase_a"]
        print(f"  tech_cards: {pa.get('tech_card_total', 0)}, "
              f"project: {pa.get('project_card_total', 0)}, "
              f"product: {pa.get('product_card_total', 0)}")

    if result.get("total_fail", 0) > 0:
        return 2  # FAIL 가드
    return 0


if __name__ == "__main__":
    sys.exit(main())
