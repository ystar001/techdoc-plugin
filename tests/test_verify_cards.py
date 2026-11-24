"""verify_cards 승격판 (v1.10.2 — F101·F64·F69·F73·F79)."""
import json

from scripts.verify_cards import check_card, load_threshold_overrides, parse_call_id


def _write(d, name, card):
    p = d / name
    p.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    return p


def test_parse_call_id_signature_kept():
    assert parse_call_id("D-2.XL3_card") == ("XL3", "XL3")
    assert parse_call_id("1.1") == ("S", None)


def test_quick_summary_not_counted_and_not_tail(tmp_path):
    card = {"sections": {"s1": {"body": "가" * 15000 + "다."}},
            "quick_summary": {"summary": "요약 " * 50 + "**굵게**"}}
    r = check_card(_write(tmp_path, "1.1_card.json", card))
    assert r["chars"] == 15002
    assert r["status"] == "PASS"


def test_tail_strips_markdown_emphasis(tmp_path):
    card = {"sections": {"s1": {"body": "가" * 15000 + "**끝이다.**"}}}
    assert check_card(_write(tmp_path, "1.1_card.json", card))["status"] == "PASS"


def test_tail_uses_last_section_in_list_form(tmp_path):
    card = {"sections": [{"body": "가" * 8000 + "다."}, {"body": "나" * 8000 + "끊긴"}]}
    r = check_card(_write(tmp_path, "1.1_card.json", card))
    assert any("종결부" in w for w in r["warns"])


def test_unknown_id_warns(tmp_path):
    r = check_card(_write(tmp_path, "부록-가_card.json",
                          {"sections": {"s": {"body": "가" * 9000 + "다."}}}))
    assert any("ID 꼴 인식 실패" in w for w in r["warns"])


def test_threshold_override_file_applies(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    (tmp_path / "verify_thresholds.json").write_text('{"S": 3000}', encoding="utf-8")
    ov = load_threshold_overrides(cards)
    try:
        r = check_card(_write(cards, "1.1_card.json", {"sections": {"s": {"body": "가" * 4000 + "다."}}}))
        assert ov["applied"] == {"S": 3000}
        assert r["status"] == "PASS"
    finally:
        from scripts import verify_cards
        verify_cards.THRESHOLDS["S"] = 14000


def test_tail_prefers_conclusion_after_sections(tmp_path):
    # 실데이터 회귀(R0 1.2): 마지막 절이 수식 상자로 끝나도 읽는 순서상 끝은 결론
    card = {"sections": {"s1": {"body": "가" * 15000 + "\n!!! 수식 \"산출\"\n    = 17~19년"}},
            "conclusion": ["첫째 결론이다.", "둘째 결론이다."]}
    assert check_card(_write(tmp_path, "1.2_card.json", card))["status"] == "PASS"
