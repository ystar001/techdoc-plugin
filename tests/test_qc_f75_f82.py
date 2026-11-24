"""F82 나머지(①캡션 번호 꼴·③시각 필드 id만 있는 캡션)·F75(코드 네임스페이스) 재현 (v1.11-c Task 3)."""
from __future__ import annotations

import json
from pathlib import Path

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.qc.registry import REGISTRY, sample_model


def _n(gid: str, model) -> int:
    return len(REGISTRY[gid](model).findings)


def _card(body: str, **kw) -> dict:
    return {"sections": {"s1": {"body": body}}, **kw}


# ── F82 ① check_quality 캡션 정규식 → numbering.caption_num_re ──

ROMAN = "표 II.8-1 비교\n표 II.8-3 다른 표\n본문은 표 II.8-9를 본다."


def test_f82_check_captions_roman_numbering():
    from scripts.check_quality import check_captions

    got = check_captions(ROMAN, "roman")
    assert got == {"duplicate": [], "gap": ["표 II.8-2"], "dangling_ref": ["표 II.8-9"]}


def test_f82_check_captions_arabic_unchanged():
    from scripts.check_quality import CAPTION_RE, check_captions

    # 아라비아(기본)는 v1.10.2 정규식과 같다 — 로마 숫자·「1.2-3」은 캡션이 아니다
    assert check_captions(ROMAN) == {"duplicate": [], "gap": [], "dangling_ref": []}
    assert check_captions("표 1.2-3 제목") == {"duplicate": [], "gap": [], "dangling_ref": []}
    assert CAPTION_RE.pattern == r"(표|그림|식)\s*(\d+)-(\d+)"
    text = "표 3-1 제목\n표 3-1 또\n그림 3-2 흐름\n본문 표 3-7 참조"
    assert check_captions(text) == {"duplicate": ["표 3-1"], "gap": ["그림 3-1"],
                                    "dangling_ref": ["표 3-7"]}


def test_f82_run_quality_check_reads_numbering_from_project_config(tmp_path):
    from scripts.check_quality import run_quality_check

    out = tmp_path / "output"
    (out / "cards").mkdir(parents=True)
    (out / "cards" / "II.8_card.json").write_text(
        json.dumps(_card(ROMAN), ensure_ascii=False), encoding="utf-8")
    assert run_quality_check(out)["phase_a"]["caption_issues"]["gap"] == []
    (tmp_path / "techdoc.project.yaml").write_text("numbering:\n  section: roman\n",
                                                   encoding="utf-8")
    caps = run_quality_check(out)["phase_a"]["caption_issues"]
    assert caps["gap"] == ["표 II.8-2"] and caps["dangling_ref"] == ["표 II.8-9"]


def test_f82_qc_caption_gates_follow_numbering():
    m = sample_model(cards={"II.8": _card(ROMAN)}, numbering={"section": "roman"})
    assert _n("PLG-CQ-caption_gap", m) == 1
    assert _n("PLG-CQ-caption_dangling_ref", m) == 1
    assert _n("PLG-CQ-caption_gap", sample_model(cards={"II.8": _card(ROMAN)})) == 0


# ── F82 ③ 시각 필드에 id만 있고 캡션에 번호가 없음 → 경고 (V89) ──

def _vis(field: str, **item) -> dict:
    return {"sections": {"s1": {"body": "본문"}}, field: [item]}


def test_f82_visual_id_without_caption_number_warns():
    m = sample_model(cards={"1.1": _vis("diagrams", id="그림 1-2", mermaid="flowchart LR",
                                        caption="관수 흐름")})
    out = REGISTRY["V89"](m)
    assert len(out.findings) == 1 and out.targets_read == 1
    assert out.findings[0].loc.startswith("1.1:diagrams[1]")
    assert "그림 1-2" in out.findings[0].msg
    m2 = sample_model(cards={"1.1": _vis("figures", id="fig-3", path="a.png", caption="")})
    assert _n("V89", m2) == 1


def test_f82_visual_numbered_caption_or_no_id_passes():
    ok = [
        _vis("diagrams", id="그림 1-2", mermaid="x", caption="그림 1-2 관수 흐름"),
        _vis("diagrams", id="d1", mermaid="x", caption="**그림 II.8-1** 흐름"),
        _vis("figures", id="f1", path="a.png", caption="표 3-1 비교"),
        _vis("diagrams", mermaid="x", caption="번호 없는 캡션"),  # id가 없으면 이 게이트 밖
    ]
    for card in ok:
        assert _n("V89", sample_model(cards={"1.1": card})) == 0, card
    assert REGISTRY["V89"](sample_model(cards={"1.1": _card("본문")})).targets_read == 0


# ── F75 코드 네임스페이스 (V90) ──

def _table(*rows: tuple[str, str]) -> str:
    return "| 코드 | 뜻 |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in rows) + "\n"


def test_f75_same_code_defined_differently_in_two_sections():
    m = sample_model(cards={
        "8.3": _card("근거 계층은 다음과 같다.\n\n" + _table(("E1", "무작위 대조 시험"),
                                                     ("E2", "관찰 연구"))),
        "19.1": _card("산정 절차\n\n" + _table(("E1", "비용 항목 식별"), ("E3", "할인율 적용"))),
    })
    out = REGISTRY["V90"](m)
    assert [f.msg.split(" ")[0] for f in out.findings] == ["E1"]
    assert out.findings[0].loc.startswith("19.1:")
    assert "8.3" in out.findings[0].msg and "무작위 대조" in out.findings[0].msg


def test_f75_line_definitions_and_identical_range():
    # 10.4 에스컬레이션 L0~L3과 17.5 발현 시차 L0~L3 — 문자와 구간이 같이 겹친다(카드 재현 경로)
    esc = "\n".join(f"- **L{i}**: 에스컬레이션 {i}단계" for i in range(4))
    lag = "\n".join(f"L{i} — 발현 {i}개월 이내" for i in range(4))
    m = sample_model(cards={"10.4": _card(esc), "17.5": _card(lag)})
    assert sorted(f.msg.split(" ")[0] for f in REGISTRY["V90"](m).findings) == \
        ["L0", "L1", "L2", "L3"]


def test_f75_no_warning_for_same_meaning_or_same_section():
    same = _table(("E1", "무작위 대조 시험"))
    m = sample_model(cards={"8.3": _card(same), "9.1": _card(same + "\nE1 사용 예시.")})
    assert _n("V90", m) == 0
    # 한 절의 분할 카드(8.3.L1·8.3.L2)는 같은 절 — 다시 정의해도 경고 아님
    m = sample_model(cards={"8.3.L1": _card(_table(("E1", "무작위 대조"))),
                            "8.3.L2": _card(_table(("E1", "관찰 연구")))})
    assert _n("V90", m) == 0
    # 짧게 줄여 다시 적은 정의(한쪽이 다른 쪽을 포함)는 같은 뜻으로 본다
    m = sample_model(cards={"8.3": _card(_table(("E1", "무작위 대조 시험(RCT)"))),
                            "9.1": _card(_table(("E1", "무작위 대조 시험")))})
    assert _n("V90", m) == 0


def test_f75_references_and_mentions_are_not_definitions():
    m = sample_model(cards={
        "1.1": _card("본문은 [REF-001]을 인용한다.\n\n" + _table(("REF-001", "논문 A"))),
        "2.1": _card(_table(("REF-001", "보고서 B")) + "\nE1은 8.3절의 근거 계층이다."),
        "3.1": _card("E1 등급을 쓴다. 문장 안의 E1: 정의 아님"),
    })
    assert _n("V90", m) == 0


def test_f75_allow_and_pattern_override():
    cards = {"8.3": _card(_table(("E1", "무작위 대조"))),
             "19.1": _card(_table(("E1", "비용 항목")))}
    assert _n("V90", sample_model(cards=cards, extra={"code_namespace": {"allow": ["E1"]}})) == 0
    alt = {"8.3": _card(_table(("Q-01", "가"))), "19.1": _card(_table(("Q-01", "나")))}
    assert _n("V90", sample_model(cards=alt)) == 1
    assert _n("V90", sample_model(cards=alt, extra={"code_namespace": {
        "pattern": r"E\d"}})) == 0


def test_f75_prose_files_when_no_cards():
    m = sample_model(draft={"8.3. 근거.md": _table(("E1", "무작위 대조")),
                            "19.1. 산정.md": _table(("E1", "비용 항목"))})
    assert _n("V90", m) == 1


def test_f75_selftest_samples_pass():
    from techdoc_core.qc.engine import run_selftests

    assert run_selftests({g: REGISTRY[g] for g in ("V89", "V90")}) == []


def test_f82_f75_gate_specs_present():
    from techdoc_core.bundles.loader import load_gate_specs

    specs = load_gate_specs([("본체", Path(__file__).resolve().parents[1] / "bundles" / "core")])
    assert specs["V89"].level == "경고" and specs["V90"].level == "경고"
