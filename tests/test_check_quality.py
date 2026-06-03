"""Plan E — check_quality self-model 모드 지원 (F5) tests.

기존 measure_document(standard 모드)는 별도 통합 테스트로 검증되며,
본 테스트는 v1.1.3에 추가된 self-model 모드 진입점·라우팅에 집중한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_self_model_card(cards_dir: Path, card_id: str, body_text: str) -> None:
    cards_dir.mkdir(parents=True, exist_ok=True)
    (cards_dir / f"{card_id}_card.json").write_text(
        json.dumps({
            "id": card_id,
            "name": "T",
            "sections": {
                "sec1_definition_scope": {"body": body_text},
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_undefined_abbreviation_detected():
    # 풀이 없이 처음 등장한 약어 → 미정의로 카운트
    from scripts.check_quality import check_abbreviation_consistency

    n = check_abbreviation_consistency("본문에서 XYZ 기술을 쓴다.", defined=set())
    assert n >= 1


def test_defined_abbreviation_not_flagged():
    from scripts.check_quality import check_abbreviation_consistency

    n = check_abbreviation_consistency("사물인터넷(IoT) 기반. 이후 IoT 재등장.", defined={"IOT"})
    assert n == 0


def test_terminology_consistency_uses_glossary():
    # glossary 용어가 본문에 일관 사용되는지 — 변형 발견 시 카운트
    from scripts.check_quality import check_terminology_consistency

    miss = check_terminology_consistency("데이타 처리", glossary={"데이터": "data"})
    assert miss >= 1


def test_run_quality_check_unknown_mode(tmp_path):
    from scripts.check_quality import run_quality_check

    result = run_quality_check(tmp_path)
    assert result["mode"] == "unknown"
    assert result.get("total_fail", 0) == 0


def test_run_quality_check_self_model_pass(tmp_path):
    from scripts.check_quality import run_quality_check

    _write_self_model_card(tmp_path / "cards", "1.1", "내용 " * 8000)  # 16k자
    result = run_quality_check(tmp_path)
    assert result["mode"] == "self_model"
    assert result["phase_a"]["total_cards"] == 1
    assert result["total_fail"] == 0


def test_run_quality_check_self_model_fail_on_short_body(tmp_path):
    from scripts.check_quality import run_quality_check

    _write_self_model_card(tmp_path / "cards", "1.1", "짧음")
    result = run_quality_check(tmp_path)
    assert result["mode"] == "self_model"
    assert result["total_fail"] >= 1


def test_run_quality_check_self_model_detects_variant_body_keys(tmp_path):
    """F1 변형: body 대신 narrative/content 사용해도 char count 합산."""
    from scripts.check_quality import run_quality_check

    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "5.6.L2_card.json").write_text(json.dumps({
        "id": "5.6.L2",
        "sections": {
            "sec3_trends": {"narrative": "동향 본문 " * 3000},  # narrative 변형
            "sec5_limits": {"content": "한계 본문 " * 3000},    # content 변형
        },
    }, ensure_ascii=False), encoding="utf-8")

    result = run_quality_check(tmp_path)
    # 합산이 정상 동작하면 6000+ chars로 L2 임계(10000) 근처
    cards_result = result.get("cards", [])
    assert cards_result
    assert cards_result[0]["chars"] > 5000


def test_check_quality_cli_dir_mode_writes_report(tmp_path):
    """CLI: -i <directory> → self_model 자동 판별 + quality_report.json 저장."""
    from scripts.check_quality import main as cq_main
    import sys as _sys

    _write_self_model_card(tmp_path / "cards", "2.1", "충분한 본문 " * 5000)

    argv_backup = list(_sys.argv)
    try:
        _sys.argv = [
            "check_quality", "-i", str(tmp_path),
            "-o", str(tmp_path / "quality_report.json"),
        ]
        rc = cq_main()
    finally:
        _sys.argv = argv_backup

    report_path = tmp_path / "quality_report.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["mode"] == "self_model"
    # 충분히 긴 본문이면 PASS, exit 0
    assert rc == 0
