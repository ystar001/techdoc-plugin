"""Phase A 품질 검증 (결정론적 측정 23개 항목).

항목 분류:
  기본 12개: 섹션 길이·컴포넌트·인용 수·AI추정 비율·서술 형식·용어 일치 등
  기술연구 5개: 대학·기업·연구기관 패턴 (REQ-012~014)
  카드 시스템 6개: 섹션당 카드 수·블록 충족률·최소 길이·종합분석 블록

v1.11-c: 측정 코드는 `techdoc_core.qc.legacy.doc_metrics`로 옮겼다 — qc 게이트 PLG-CQ-*가 같은
함수를 쓴다. 이 모듈은 기존 공개 이름(`run_quality_check`·`measure_document`·`measure_self_model`·
`_parse_call_id`·`SIZE_THRESHOLDS` 등)과 결과 계약(`total_fail`·`total_warning`·`overall`·`mode`·
`phase_a`, FAIL이면 종료 코드 2)을 그대로 지키는 래퍼다. 캡션 번호 꼴은 프로젝트 설정
(`techdoc.project.yaml`의 `numbering.section`)을 따른다 — 없으면 아라비아(F82).

사용법:
    python -m scripts.check_quality --input ./output/document_final.json \
        --refs ./output/reference_list.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import scripts.extract_glossary  # noqa: F401 — 옮기기 전처럼 cp949 콘솔 안전화(import 부수효과)
from techdoc_core.models import Document
from techdoc_core.qc.legacy.doc_metrics import (
    _KNOWN_VARIANTS,
    BODY_KEYS,
    CAPTION_RE,
    SIZE_THRESHOLDS,
    TAG_RE,
    _check_self_model_card,
    _collect_body_chars,
    _collect_body_text,
    _parse_call_id,
    caption_re,
    check_abbreviation_consistency,
    check_captions,
    check_institution_number_pattern,
    check_product_pattern,
    check_project_pattern,
    check_terminology_consistency,
    count_ai_estimates,
    count_citations,
    load_glossary,
    measure_document,
    self_model_section_text,
    self_model_size_issues,
    strip_html,
)

__all__ = [
    "BODY_KEYS", "CAPTION_RE", "SIZE_THRESHOLDS", "TAG_RE", "_KNOWN_VARIANTS",
    "_check_self_model_card", "_collect_body_chars", "_collect_body_text", "_parse_call_id",
    "caption_re", "check_abbreviation_consistency", "check_captions",
    "check_institution_number_pattern", "check_product_pattern", "check_project_pattern",
    "check_terminology_consistency", "count_ai_estimates", "count_citations", "main",
    "measure_document", "measure_self_model", "run_quality_check", "self_model_section_text",
    "self_model_size_issues", "strip_html",
]

_load_glossary = load_glossary  # 옮기기 전 이름


def _numbering_style(output_dir: Path) -> str | None:
    """`<output_dir>/../techdoc.project.yaml`의 `numbering.section` — 없거나 못 읽으면 None(아라비아)."""
    cfg_file = output_dir.parent / "techdoc.project.yaml"
    if not cfg_file.is_file():
        return None
    try:
        from techdoc_core.qc.config import load_config

        return load_config(output_dir.parent, cfg_file).numbering.get("section")
    except Exception:  # 설정 오류는 qc가 보고한다 — 여기서는 기본 꼴로 측정을 이어간다
        return None


def measure_self_model(output_dir: Path, baseline_dir=None, strict=False, tolerance=0.15,
                       numbering_style: str | None = None) -> dict:
    """self-model 모드 — cards/*_card.json 일괄 검사 (사이즈 + 서식 게이트)."""
    output_dir = Path(output_dir)
    cards_dir = output_dir / "cards"
    card_files = sorted(cards_dir.glob("*_card.json"))
    results = []
    for p in card_files:
        bpath = (Path(baseline_dir) / p.name) if baseline_dir else None
        results.append(_check_self_model_card(p, bpath, strict, tolerance))

    # 문서 단위 캡션 정합(F42) — 전 카드 본문 집계. _body_text는 리포트에서 제거.
    all_body = "\n".join(c.pop("_body_text", "") for c in results)
    # 카드 diagrams·figures 캡션은 정의(최종 리뷰 I4) — 시각 필드가 없으면 결과는 전과 같다
    visual = "\n".join(c.pop("_visual_caps", "") for c in results)
    caption_issues = check_captions(all_body, numbering_style, visual)
    caption_count = (
        len(caption_issues["duplicate"])
        + len(caption_issues["gap"])
        + len(caption_issues["dangling_ref"])
    )

    total_fail = sum(1 for c in results if c["status"] == "FAIL")
    total_warning = sum(1 for c in results if c["status"] == "WARNING") + caption_count

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
            "caption_issues": caption_issues,
        },
        "cards": results,
        "total_fail": total_fail,
        "total_warning": total_warning,
        "overall": round(overall, 2),
    }


def run_quality_check(output_dir: Path, baseline_dir=None, strict=False, tolerance=0.15,
                      numbering_style: str | None = None) -> dict:
    """mode 자동 판별 후 적절한 측정 함수로 라우팅 (v1.1.3+ entry point).

    standard 모드는 document_final.json·reference_list.json을 기대;
    self_model 모드는 cards/*_card.json을 기대. baseline/strict/tolerance는 self_model 전용.
    `numbering_style`이 없으면 프로젝트 설정에서 읽는다(없으면 아라비아 — F82).
    """
    from scripts.card_layout import detect_mode

    output_dir = Path(output_dir)
    if numbering_style is None:
        numbering_style = _numbering_style(output_dir)
    mode = detect_mode(output_dir)
    if mode == "self_model":
        return measure_self_model(output_dir, baseline_dir, strict, tolerance, numbering_style)
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
        result = measure_document(doc, refs, glossary, numbering_style)
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
