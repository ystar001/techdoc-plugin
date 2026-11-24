"""기존 품질 도구 흡수 — PLG-CQ-*(check_quality)·PLG-FG-*(format_gate)·VC-*(verify_cards) (v1.11-c, 설계 D3.5).

지표 이름·판정은 옮기기 전 도구 그대로다 — 측정은 `techdoc_core.qc.legacy`의 함수를 CLI 래퍼와 같이
부른다(로직 중복 없음). 게이트 하나 = 지적(FAIL·WARNING)을 내는 지표 하나. 수준은 지금 FAIL → 막음,
WARNING → 경고. 단 **절대 분량 하한**(self-model 사이즈 임계·VC 분량·섹션 길이·카드 최소 길이)은 E18에
따라 본체 기본에서 「경고」다 — 문서 종류 프로필이 켤 때만 막음(Task 4). CLI 래퍼의 FAIL 판정은 그대로다.

적용 범위(옮기기 전 도구와 같음):
- standard 모드(`model.standard` 있음): PLG-CQ 문서 지표 — `measure_document`(document JSON·참고문헌
  목록·용어집). 캡션 결번은 원래 standard에서 지적하지 않았으므로 self-model에서만.
- self-model 카드(`model.standard` 없음): PLG-CQ-self_model_length·캡션 3종·PLG-FG 10종·VC-A~E.
- baseline 회귀(ref_loss·num_token_loss·length_delta)와 `--strict` 승격은 CLI 전용(qc에는 기준 카드 입력이
  없다). 측정만 하는 지표(pattern_counts·render_nesting·sections_without_analysis_block)는 게이트가 아니다.

설정: `extra.check_quality.size_thresholds`(self-model 사이즈 임계 덮어쓰기 — 예 `{"S": 3000}`),
`extra.verify_cards.thresholds`(VC 분량 임계 덮어쓰기). 덮어쓰기가 없으면 qc는 범용 바닥
`GENERIC_FLOOR`(800자, 카드 규칙의 가장 낮은 하한)를 쓴다 — CLI 래퍼의 기본표(14,000 등)는 그대로.
캡션 번호 꼴은 `numbering.section`(F82).
"""
from __future__ import annotations

from collections.abc import Callable

from techdoc_core.constants import CARD_LENGTH_BY_IMPORTANCE
from techdoc_core.models import Document
from techdoc_core.qc.adapters import CARD_JSON_ERROR
from techdoc_core.qc.legacy.card_checks import THRESHOLDS as VC_THRESHOLDS
from techdoc_core.qc.legacy.card_checks import check_card_data
from techdoc_core.qc.legacy.doc_metrics import (
    SIZE_THRESHOLDS,
    check_captions,
    measure_document,
    self_model_section_text,
    self_model_size_issues,
)
from techdoc_core.qc.legacy.format_metrics import measure_format
from techdoc_core.qc.model import DocModel
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

# ── 공통 ──────────────────────────────────────────────────────────────────

def _memo(model: DocModel, key: str, fn: Callable):
    """한 모델에서 측정은 한 번 — 지표마다 게이트가 따로 돌아도 같은 결과를 나눠 쓴다."""
    cache = model.__dict__.setdefault("_legacy_cache", {})
    if key not in cache:
        cache[key] = fn()
    return cache[key]


def _extra(model: DocModel, name: str) -> dict:
    v = (model.extra or {}).get(name)
    return v if isinstance(v, dict) else {}


# qc 게이트의 범용 분량 하한 — 플러그인 카드 규칙(prompts/card_length_rules.md)의 가장 낮은 하한
# (기술 카드 low 800자). 모듈 기본표(SIZE_THRESHOLDS·VC THRESHOLDS 14,000 등)는 시리즈 방법론 편
# 값이고 CLI 계약이라 CLI 래퍼만 쓴다. qc에서는 문서 종류 묶음·시리즈 설정이 extra로 표를 실을 때만
# 그 값을 쓰고, 아무도 싣지 않으면(묶음 없는 kind) 이 범용 바닥으로 본다(E18 1·2).
GENERIC_FLOOR = CARD_LENGTH_BY_IMPORTANCE["low"]["tech"][0]
GENERIC_SIZE_THRESHOLDS = dict.fromkeys(SIZE_THRESHOLDS, GENERIC_FLOOR)


def _generic_vc_table() -> dict:
    # VC 표는 CLI가 verify_thresholds.json으로 키를 더할 수 있어 부를 때마다 키를 맞춘다
    return dict.fromkeys(VC_THRESHOLDS, GENERIC_FLOOR)


def _table(base: dict, override) -> dict:
    """임계 덮어쓰기 — 정수 값만 base 위에 겹친다. 덮어쓰기가 없으면 base(범용 바닥) 그대로."""
    if not isinstance(override, dict):
        return dict(base)
    ov = {k: v for k, v in override.items() if isinstance(v, int)}
    return {**base, **ov}


def _style(model: DocModel) -> str | None:
    return (model.numbering or {}).get("section")


def _sm_cards(model: DocModel) -> dict[str, dict]:
    """self-model 카드 — standard 모드면 없음(옮기기 전 도구는 cards/만 봤다)."""
    return {} if model.standard is not None else model.cards


# ── self-model: 사이즈·서식·캡션 ─────────────────────────────────────────────

def _sm_rows(model: DocModel) -> list[tuple[str, list[dict], dict, str]]:
    """(카드 id, 사이즈 지적, 서식 결과, 본문) — check_quality self-model과 같은 측정(strict·baseline 없음)."""
    def build():
        table = _table(GENERIC_SIZE_THRESHOLDS,
                       _extra(model, "check_quality").get("size_thresholds"))
        rows = []
        for cid, card in _sm_cards(model).items():
            _size, _chars, issues = self_model_size_issues(card, cid, table)
            sec = self_model_section_text(card)
            rows.append((cid, issues, measure_format(sec), "\n".join(sec.values())))
        return rows

    return _memo(model, "sm_rows", build)


def _sm_size(model: DocModel) -> GateOutput:
    rows = _sm_rows(model)
    return GateOutput(len(rows), [Finding(cid, f"[{i['severity']}] {i['msg']}")
                                  for cid, issues, _f, _b in rows for i in issues])


def _fg(metric: str) -> Callable[[DocModel], GateOutput]:
    def run(model: DocModel) -> GateOutput:
        rows = _sm_rows(model)
        return GateOutput(len(rows), [Finding(cid, i["msg"]) for cid, _s, fmt, _b in rows
                                      for i in fmt["issues"] if i["metric"] == metric])
    return run


# ── standard: Phase A 문서 지표 ──────────────────────────────────────────────

def _std_result(model: DocModel) -> dict | None:
    st = model.standard
    if not st or not isinstance(st.get("doc"), dict):
        return None

    def build():
        return measure_document(Document.from_dict(st["doc"]), st.get("reference_list"),
                                st.get("glossary") or {}, _style(model))

    return _memo(model, "std", build)


def _std_targets(model: DocModel, unit: str) -> int:
    doc = (model.standard or {}).get("doc") or {}
    if unit == "reflist":
        return 1 if (model.standard or {}).get("reference_list") else 0
    return len(doc.get(unit) or [])


def _issue_msg(i: dict) -> str:
    msg = f"{i['metric']}: 기대 {i.get('expected') or '-'} · 실제 {i.get('actual') or '-'}"
    return msg + (f" — {i['action']}" if i.get("action") else "")


def _cq(metric: str, unit: str) -> Callable[[DocModel], GateOutput]:
    def run(model: DocModel) -> GateOutput:
        res = _std_result(model)
        if res is None:
            return GateOutput(0)
        items = [Finding(i.get("section_id") or "문서", _issue_msg(i))
                 for i in res["issues"] if i["metric"] == metric]
        return GateOutput(_std_targets(model, unit), items)
    return run


# ── 캡션 3종 — 두 모드 공통 ────────────────────────────────────────────────

def _captions(model: DocModel) -> tuple[int, dict]:
    res = _std_result(model)
    if res is not None:
        return _std_targets(model, "sections"), res["phase_a"]["caption_issues"]
    rows = _sm_rows(model)
    caps = _memo(model, "sm_caps",
                 lambda: check_captions("\n".join(b for *_x, b in rows), _style(model)))
    return len(rows), caps


def _cap(kind: str, standard_too: bool) -> Callable[[DocModel], GateOutput]:
    label = {"duplicate": "캡션 번호 중복", "gap": "캡션 번호 결번",
             "dangling_ref": "정의 없는 캡션 참조"}[kind]

    def run(model: DocModel) -> GateOutput:
        if model.standard is not None and not standard_too:
            return GateOutput(0)
        n, caps = _captions(model)
        return GateOutput(n, [Finding("문서", f"{label}: {c}") for c in caps[kind]])
    return run


# ── VC: verify_cards A~E ─────────────────────────────────────────────────

def _vc_rows(model: DocModel) -> list[tuple[str, dict]]:
    def build():
        table = _table(_generic_vc_table(), _extra(model, "verify_cards").get("thresholds"))
        return [(cid, check_card_data(card, cid, table)) for cid, card in _sm_cards(model).items()]
    return _memo(model, "vc_rows", build)


def _vc(letter: str) -> Callable[[DocModel], GateOutput]:
    def run(model: DocModel) -> GateOutput:
        rows = _vc_rows(model)
        return GateOutput(len(rows), [Finding(cid, f"[{sev}] {msg}") for cid, r in rows
                                      for lt, sev, msg in r["checks"] if lt == letter])
    return run


def _vc_a(model: DocModel) -> GateOutput:
    """A — 카드 JSON 읽기 실패(어댑터가 읽지 못해 모델에 없는 카드)."""
    if model.standard is not None:
        return GateOutput(0)
    bad = [e for e in model.load_errors if CARD_JSON_ERROR in e]
    items = [Finding(e.split(":", 1)[0].removesuffix(".json").removesuffix("_card"), e)
             for e in bad]
    return GateOutput(len(model.cards) + len(bad), items)


# ── 표본(자기검사) ─────────────────────────────────────────────────────────

def _card(body: str, **kw) -> dict:
    return {"sections": {"s1": {"body": body}}, **kw}


_CLEAN = sample_model(cards={"1.1": _card("짧은 본문이다.")})
_FG_DIRTY = {
    "inline_hierarchy": "방법은 (i) 측정 (ii) 비교다.",
    "top_plain_label": "분류는 (a) 노지다.",
    "nonbullet_indent": "설명이다.\n  들여쓴 줄이다.",
    "flatten_risk_indent": "- 상위\n  - 하위",
    "high_list_ratio": "- 가\n- 나\n- 다\n서술이다.",
    "redundant_summary": "종합하면 두 축이다.",
    "control_chars": "값\x07이다.",
    "mermaid_label_risk": "```mermaid\nflowchart LR\nA-->|수집·전송|B\n```",
    "inline_enumeration": "첫째 모은다. 둘째 맞춘다.",
    "visual_density": "가" * 3200,
}
FG_METRICS = tuple(_FG_DIRTY)

for _m in FG_METRICS:
    gate(f"PLG-FG-{_m}", samples=[
        Sample(sample_model(cards={"1.1": _card(_FG_DIRTY[_m])}), 1),
        Sample(_CLEAN, 0),
    ])(_fg(_m))

gate("PLG-CQ-self_model_length", samples=[
    # 범용 바닥 800자: 1.1 절반 미만 + 1.2.L2 바닥 미만(500자)
    Sample(sample_model(cards={"1.1": _card("짧다."), "1.2.L2": _card("가" * 500)}), 2),
    Sample(sample_model(cards={"1.1": _card("짧다.")},
                        extra={"check_quality": {"size_thresholds": {"S": 3}}}), 0),
])(_sm_size)

_CAP_SM = sample_model(cards={
    "1.1": _card("표 1-1 비교\n표 1-3 다른 표\n본문은 표 1-9를 본다."),
    "1.2": _card("표 1-1 또 정의"),
})
_CAP_STD = sample_model(standard={"doc": {"sections": [
    {"section_id": "1.1", "html_content": "<p>표 2-1 비교</p>\n<p>표 2-1 다시</p><p>본문 표 2-7 참조</p>"},
]}})
gate("PLG-CQ-caption_duplicate", samples=[Sample(_CAP_SM, 1), Sample(_CLEAN, 0)])(
    _cap("duplicate", True))
gate("PLG-CQ-caption_gap", samples=[Sample(_CAP_SM, 1), Sample(_CAP_STD, 0)])(_cap("gap", False))
gate("PLG-CQ-caption_dangling_ref", samples=[Sample(_CAP_SM, 1), Sample(_CAP_STD, 1),
                                             Sample(_CLEAN, 0)])(_cap("dangling_ref", True))


def _std_sample(**doc) -> DocModel:
    base = {"sections": [{"section_id": "1.1", "html_content": "<h2>1.1</h2><p>짧다</p>"}]}
    return sample_model(standard={"doc": {**base, **doc.pop("doc", {})}, **doc})


_STD_LONG = "<h2>1.1</h2><p>" + "관수 시점을 정한다 [REF-001] [REF-002] [REF-003]. " * 80 + "</p>"
_STD_GOOD = _std_sample(doc={"sections": [{"section_id": "1.1", "html_content": _STD_LONG}]})
_CQ = {
    # 지표: (게이트 id, 대상 단위, 지적 표본, 깨끗한 표본)
    "section_length": ("PLG-CQ-section_length", "sections", _std_sample(), _STD_GOOD),
    "section_citations": ("PLG-CQ-section_citations", "sections", _std_sample(), _STD_GOOD),
    "ai_estimate_ratio": ("PLG-CQ-ai_estimate_ratio", "sections",
                          _std_sample(doc={"sections": [{"section_id": "1.1", "html_content":
                                      "<p>효과가 큰 것으로 알려졌다.</p>"}]}), _STD_GOOD),
    "undefined_abbreviations": ("PLG-CQ-undefined_abbreviations", "sections",
                                _std_sample(doc={"sections": [{"section_id": "1.1", "html_content":
                                            "<p>NDVI LAI EVI GNSS RTK</p>"}]},
                                            glossary={"데이터": "data"}), _STD_GOOD),
    "terminology_inconsistencies": ("PLG-CQ-terminology_inconsistencies", "sections",
                                    _std_sample(doc={"sections": [{"section_id": "1.1",
                                                "html_content": "<p>데이타 처리</p>"}]}),
                                    _STD_GOOD),
    "academic_ratio": ("PLG-CQ-academic_ratio", "reflist",
                       _std_sample(reference_list={"total_refs": 10, "category_coverage": [
                           {"category": "학술", "count": 1}, {"category": "기업R&D", "count": 5}]}),
                       _std_sample(reference_list={"total_refs": 10, "category_coverage": [
                           {"category": "학술", "count": 5}, {"category": "기업R&D", "count": 5}]})),
    "rd_ratio": ("PLG-CQ-rd_ratio", "reflist",
                 _std_sample(reference_list={"total_refs": 10, "category_coverage": [
                     {"category": "학술", "count": 5}, {"category": "기업R&D", "count": 1}]}),
                 _std_sample(reference_list={"total_refs": 10, "category_coverage": [
                     {"category": "학술", "count": 5}, {"category": "기업R&D", "count": 5}]})),
    "tech_cards_per_section": ("PLG-CQ-tech_cards_per_section", "sections", _std_sample(),
                               _std_sample(doc={"sections": [], "tech_cards": []})),
    "tech_card_block_fill": ("PLG-CQ-tech_card_block_fill", "tech_cards",
                             _std_sample(doc={"tech_cards": [{"id": "1.1.1", "name": "t",
                                                              "overview": "개요"}]}),
                             _std_sample()),
    "undersized_tech_cards": ("PLG-CQ-undersized_cards", "tech_cards",
                              _std_sample(doc={"tech_cards": [{"id": "1.1.1", "name": "t",
                                                               "overview": "개요"}]}),
                              _std_sample()),
}
CQ_GATES = {metric: v[0] for metric, v in _CQ.items()}

for _metric, (_gid, _unit, _dirty, _clean) in _CQ.items():
    gate(_gid, samples=[Sample(_dirty, 1), Sample(_clean, 0)])(_cq(_metric, _unit))


# ── VC ──
gate("VC-A", samples=[
    Sample(sample_model(load_errors=[f"9.9_card.json: {CARD_JSON_ERROR} — Expecting value"]), 1),
    Sample(_CLEAN, 0),
])(_vc_a)
gate("VC-B", samples=[
    Sample(sample_model(cards={"1.1": _card("본문이다.", schema_version="0.9.0")}), 1),
    Sample(sample_model(cards={"1.1": _card("본문이다.", schema_version="0.2.0")}), 0),
])(_vc("B"))
gate("VC-C", samples=[
    # 1.1 분량 절반 미만(FAIL) + foo ID 꼴 인식 실패(WARN)
    Sample(sample_model(cards={"1.1": _card("짧다."), "foo": _card("가" * 9000 + "다.")}), 2),
    Sample(sample_model(cards={"1.1": _card("짧다.")},
                        extra={"verify_cards": {"thresholds": {"S": 2}}}), 0),
])(_vc("C"))
gate("VC-D", samples=[
    Sample(sample_model(cards={"1.1": _card("그리고 다음으로 이어지는")}), 1),
    Sample(sample_model(cards={"1.1": _card("끝맺는다.")}), 0),
])(_vc("D"))
gate("VC-E", samples=[
    Sample(sample_model(cards={"1.1": _card("본문.", validation={"citation_count": 0})}), 1),
    Sample(sample_model(cards={"1.1": _card("본문.", validation={"citation_count": 2})}), 0),
])(_vc("E"))
