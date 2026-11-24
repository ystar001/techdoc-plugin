"""기존 품질 도구 래퍼의 결과 계약 (v1.11-c Task 3, 설계 D3.5 · 계획 Review Focus 2).

`check_quality`·`format_gate`·`verify_cards`의 측정은 qc 게이트(PLG·VC)와 같은 함수를 쓰도록
`techdoc_core/qc/legacy/`로 옮겼다. 기존 CLI는 래퍼로 남으며, 같은 입력에 v1.10.2와 같은
`total_fail`·`total_warning`·종료 코드를 내야 한다(autopilot `quality_fail` 트리거 불변).

기대값(EXPECTED)은 **옮기기 전 코드(v1.10.2 + v1.11-b)로 잰 값**을 적은 것이다 — 고치지 말 것.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ── 합성 fixture ──────────────────────────────────────────────────────────

_PARA = "스마트농업 시스템은 센서 자료를 모아 관개 시점을 정한다. 현장 검증에서 물 사용량이 줄었다. "
_TABLE = "\n\n| 항목 | 값 |\n|---|---|\n| 관수량 | 12 |\n\n"


def _body(n: int, *, tables: bool = True) -> str:
    """대략 n자 본문 — tables면 3,000자마다 표 하나(시각 밀도 경고가 안 나게)."""
    out, size = [], 0
    while size < n:
        chunk = _PARA * 10
        if tables:
            chunk += _TABLE
        out.append(chunk)
        size += len(chunk)
    return "".join(out)[:n].rstrip() + "다."


def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


_DIRTY = (
    "방법은 (i) 측정 (ii) 비교로 나뉜다.\n"
    "분류는 (a) 노지 (b) 시설이다.\n"
    "  들여쓴 설명 줄이다.\n"
    "- 상위\n  - 두 칸 하위\n"
    "종합하면 핵심은 두 축이다.\x07\n\n"
    "첫째 자료를 모은다. 둘째 모델을 맞춘다.\n\n"
    "```mermaid\nflowchart LR\nsubgraph 센서 계층\nA-->|수집·전송|B\nend\n```\n"
)


def self_model_fixture(root: Path) -> Path:
    """self-model 산출물 — 분량 PASS/WARN/FAIL·서식 결함·캡션 중복/결번/끊긴 참조·깨진 JSON."""
    out = root / "output"
    cards = out / "cards"
    _write(cards / "1.1_card.json", {
        "schema_version": "0.2.0", "id": "1.1",
        "sections": {
            "s1": {"title": "개요", "body": "표 1-1 관수량 비교\n\n" + _body(8000)},
            "s2": {"body": "본문은 표 1-1을 본다.\n그림 1-3 흐름도\n\n" + _body(7000)
                   + "\n\n그림 1-1을 보라. 표 1-9도 보라."},
        },
        "self_check": {"citation_count": 4},
    })
    _write(cards / "1.2_card.json", {
        "schema_version": "0.2.0", "id": "1.2",
        "sections": {"s1": {"body": _DIRTY + _body(2500, tables=False)}},
    })
    _write(cards / "1.3.L2_card.json", {
        "schema_version": "0.2.0",
        "sections": {
            "s1": {"body": "표 1-1 다시 정의한 표\n\n" + _body(6000)},
            "s2": {"body": "\n".join(f"- 항목 {i}" for i in range(20)) + "\n서술 한 줄"},
            "s3": {"body": _body(2000, tables=False)},
        },
    })
    _write(cards / "0.1_card.json", {
        "sections": {"s1": {"body": _body(3000)}},
        "self_check": {"front_matter": True},
    })
    _write(cards / "A-1_card.json", {
        "schema_version": "0.3.0",
        "sections": {"s1": {"body": _body(9000, tables=False) + "\n\n그리고 다음으로 이어지는"}},
        "validation": {"citation_count": 0},
    })
    _write(cards / "foo_card.json", {"sections": {"s1": {"body": _body(9500)}}})
    _write(cards / "broken_card.json", "{ 깨진 JSON")
    return out


def standard_fixture(root: Path, *, glossary: bool = True, refs: bool = True) -> Path:
    """standard 산출물 — 짧은 절·인용 부족·AI 추정·표기 변형·카드 부족·블록 미충족·캡션."""
    out = root / "output"
    sec_long = ("<h2>1.2 현황</h2><p>" + _body(2600, tables=False)
                + " 서울대학 연구에서 수확량이 12% 늘었다 [REF-001]. 한 연구소 AI 시험 3회 [REF-002]."
                + " 효과가 클 것으로 알려졌다. 정확도가 높은 것으로 알려졌다. 데이타 품질이 문제다."
                + " NDVI와 LAI, EVI, GNSS, RTK, LPWAN을 쓴다. 표 2-1 비교</p>"
                + "<p>표 2-1 다시</p><p>본문은 표 2-4를 본다. 종합 분석</p>")
    doc = {
        "schema_version": "0.1.0", "title": "합성 보고서",
        "sections": [
            {"section_id": "1.1", "title": "개요", "html_content": "<h2>1.1</h2><p>짧은 절</p>"},
            {"section_id": "1.2", "title": "현황", "html_content": sec_long},
        ],
        "tech_cards": [
            {"id": "1.2.1", "name": "관수 제어", "overview": _body(400), "principle": "원리",
             "components": "", "performance": "", "pros_cons": "", "differentiation": "",
             "references": "[REF-001]",
             "diagrams": [{"id": "그림 1-2", "mermaid": "flowchart LR\nA-->B", "caption": "흐름"}]},
        ],
        "project_cards": [
            {"id": "1.2.2", "name": "실증", "background": _body(300), "organization": "기관",
             "methodology": "방법", "results": "결과", "implications": "", "followup": "",
             "references": ""},
        ],
        "product_cards": [],
    }
    _write(out / "writer_state.json", {"cards": {}})
    _write(out / "document_final.json", doc)
    if refs:
        _write(out / "reference_list.json", {
            "total_refs": 10,
            "category_coverage": [{"category": "학술", "count": 2},
                                  {"category": "기업R&D", "count": 3}],
        })
    if glossary:
        _write(out / "draft_outline.json", {"glossary": {"데이터": "data"}})
    return out


def clean_self_model_fixture(root: Path) -> Path:
    out = root / "output"
    _write(out / "cards" / "2.1_card.json", {
        "schema_version": "0.2.0",
        "sections": {"s1": {"body": _body(15000)}},
        "self_check": {"citation_count": 3},
    })
    return out


# ── v1.10.2 측정값 (옮기기 전 코드로 잰 값 — 고치지 말 것) ───────────────────

EXPECTED_CQ = {
    # 이름: (total_fail, total_warning, CLI 종료 코드, 결과 전체 지문)
    "self_model": (2, 7, 2, "a39345a2be654ae8"),
    "self_model_strict": (2, 7, 2, "df2b8234da2e3b86"),
    "self_model_baseline": (2, 7, 2, "88072853f57c1c7e"),
    "standard": (5, 7, 2, "d10a193b6745b1ee"),
    "standard_no_glossary": (5, 6, 2, "80f54758891ac7bc"),
    "clean": (0, 0, 0, "fc0ce7a032e04c59"),
}
# 카드 id: 상태|FAIL 수 F WARN 수 W
EXPECTED_VC = {"0.1": "WARN|0F1W", "1.1": "PASS|0F0W", "1.2": "FAIL|1F0W", "1.3.L2": "WARN|0F1W",
               "A-1": "FAIL|1F3W", "broken": "FAIL|1F0W", "foo": "WARN|0F1W"}


def _canon(res: dict) -> str:
    """결과 전체를 경로와 무관한 정규 JSON으로 — 카드 경로는 파일 이름만."""
    import copy
    import hashlib

    r = copy.deepcopy(res)
    for c in r.get("cards", []):
        c["path"] = Path(c["path"]).name
        c.get("format", {}).pop("render_nesting", None)  # markdown 설치 여부에 따라 None
        for it in c.get("issues", []):
            if it.get("metric") == "baseline":
                it["msg"] = it["msg"].split(":")[0]
    blob = json.dumps(r, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _cq_run(tmp_path: Path, name: str) -> tuple[int, int, int, str]:
    from scripts import check_quality

    if name.startswith("self_model"):
        out = self_model_fixture(tmp_path)
    elif name == "standard":
        out = standard_fixture(tmp_path)
    elif name == "standard_no_glossary":
        out = standard_fixture(tmp_path, glossary=False)
    else:
        out = clean_self_model_fixture(tmp_path)
    kwargs: dict = {}
    if name == "self_model_strict":
        kwargs["strict"] = True
    if name == "self_model_baseline":
        base = tmp_path / "base"
        self_model_fixture(base)
        # 기준 카드에만 있는 REF·수치 — ref_loss·num_token_loss·length_delta가 나게
        p = base / "output" / "cards" / "1.2_card.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["sections"]["s1"]["body"] += " [REF-777] 수치 98765 " + _body(3000)
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        kwargs["baseline_dir"] = base / "output" / "cards"
    res = check_quality.run_quality_check(out, **kwargs)
    code = 2 if res.get("total_fail", 0) > 0 else 0
    return res["total_fail"], res["total_warning"], code, _canon(res)


def _vc_run(tmp_path: Path):
    from scripts import verify_cards

    out = self_model_fixture(tmp_path)
    cards = sorted((out / "cards").glob("*_card.json"))
    return {p.stem.removesuffix("_card"): (r := verify_cards.check_card(p))["status"]
            + f"|{len(r['issues'])}F{len(r['warns'])}W" for p in cards}


def snapshot(tmp_root: Path) -> dict:
    """기대값을 다시 재는 도우미(옮기기 전 코드에서 한 번 돌려 EXPECTED에 적었다)."""
    snap = {}
    for i, name in enumerate(EXPECTED_CQ):
        d = tmp_root / f"cq{i}"
        d.mkdir(parents=True)
        snap[name] = _cq_run(d, name)
    d = tmp_root / "vc"
    d.mkdir(parents=True)
    snap["vc"] = _vc_run(d)
    return snap


@pytest.mark.parametrize("name", list(EXPECTED_CQ))
def test_wrapper_contract_equivalence(tmp_path, name):
    assert _cq_run(tmp_path, name) == EXPECTED_CQ[name]


def test_wrapper_contract_equivalence_verify_cards(tmp_path):
    assert _vc_run(tmp_path) == EXPECTED_VC


def test_wrapper_contract_verify_cards_exit_code(tmp_path, monkeypatch, capsys):
    import sys

    from scripts import verify_cards

    dirty = self_model_fixture(tmp_path / "a") / "cards"
    clean = clean_self_model_fixture(tmp_path / "b") / "cards"
    for d, code in ((dirty, 2), (clean, 0)):
        monkeypatch.setattr(sys, "argv", ["verify_cards", str(d)])
        assert verify_cards.main() == code
    capsys.readouterr()
