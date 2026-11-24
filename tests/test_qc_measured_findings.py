"""실제 문서 검출 측정에서 찾은 게이트 결함 재현 — 합성 표본만 (v1.11-c Task 8, findings F109~F117).

측정한 문서의 수치는 통과 조건이 아니다(E17). 여기 표본은 결함의 꼴만 옮긴 작은 합성 문서다.
"""
import techdoc_core.qc.gates  # noqa: F401
from techdoc_core.qc.engine import format_report, run_qc
from techdoc_core.qc.registry import REGISTRY, Finding, GateOutput, sample_model


def _run(gid, model):
    return REGISTRY[gid](model)


def _card(body, title="", **extra):
    return {"sections": {"s1": {"title": title, "body": body}}, **extra}


# ── F109 V87: 렌더 트리가 있으면 카드 필드는 읽지 않는다 ──

def test_f109_v87_card_fields_not_read_when_reader_text_exists():
    cards = {"3.2.L1": {"scope_note": "이 카드는 원리만 다룬다. 다음 분할 3.2.L2에서 잇는다.",
                        "split_continuation_note": "writer_state.json 참고",
                        "sections": {"s1": {"title": "원리", "body": "원리 본문."}}}}
    m = sample_model(cards=cards, tree={"a.md": "## 원리\n\n원리 본문.\n"})
    out = _run("V87", m)
    assert out.findings == []
    assert out.targets_read == 1  # 렌더 파일 하나만


def test_f109_v87_card_fields_read_without_reader_text():
    cards = {"3.2.L1": {"scope_note": "이 카드는 원리만 다룬다.",
                        "sections": {"s1": {"title": "원리", "body": "원리 본문."}}}}
    out = _run("V87", sample_model(cards=cards))
    assert len(out.findings) == 1 and "카드 필드" in out.findings[0].loc


def test_f109_v87_card_fields_configurable():
    cards = {"3.2.L1": {"editor_memo": "이 카드는 임시다.", "scope_note": "이 카드는 원리다.",
                        "sections": {"s1": {"title": "원리", "body": "본문."}}}}
    m = sample_model(cards=cards, extra={"leak": {"card_fields": ["editor_memo"]}})
    out = _run("V87", m)
    assert [f.loc for f in out.findings] == ["3.2.L1|editor_memo: 카드 필드"]


# ── F110 V68: 단체 지은이 ──

def test_f110_v68_institution_is_group_author():
    refs = [{"id": "REF-001", "title": "Standard", "authors": [], "institution": "ProSTEP iViP"},
            {"id": "REF-002", "title": "Nobody", "authors": [], "institution": ""}]
    out = _run("V68", sample_model(references=refs))
    assert [f.msg for f in out.findings] == ["지은이 빈칸 — REF-002 Nobody"]


def test_f110_v68_group_author_fields_configurable():
    refs = [{"id": "REF-001", "title": "Standard", "authors": [], "institution": "ProSTEP iViP"}]
    m = sample_model(references=refs, extra={"citation": {"group_author_fields": []}})
    assert len(_run("V68", m).findings) == 1  # 시리즈 층처럼 지은이 칸만 보는 설정


# ── F111 지적은 (위치, 글) 고유 ──

def _uniq(out: GateOutput) -> bool:
    keys = [(f.loc, f.msg) for f in out.findings]
    return len(keys) == len(set(keys))


TBL = "| 가 | 나 |\n|---|---|\n| 1 | 2 |\n"


def test_f111_v6_uncalled_each_names_its_table():
    body = "".join(f"**표 1.1-{i}.** 값 {i}\n\n{TBL}\n" for i in range(1, 4))
    out = _run("V6", sample_model(cards={"1.1": _card(body)}))
    assert len(out.findings) == 3 and _uniq(out)  # 결손 수만큼 세되 지적마다 대상이 다르다
    assert any("표 1.1-2" in f.msg for f in out.findings)


def test_f111_v6_missing_captions_distinct():
    out = _run("V6", sample_model(cards={"1.1": _card(TBL + "\n" + TBL)}))
    assert len(out.findings) == 2 and _uniq(out)


def test_f111_v14_each_ghost_token_separately():
    m = sample_model(cards={"1.1": _card("본문은 NDVI를 쓴다.", quick_summary="NDVI와 EVI, GNDVI")})
    out = _run("V14", m)
    assert len(out.findings) == 2 and _uniq(out)


def test_f111_v30_same_dead_ref_twice_distinct():
    m = sample_model(tree={"a.md": "## 1.1 제목\n\n별첨 C-1을 보라. 다시 별첨 C-1.\n"})
    out = _run("V30", m)
    assert len(out.findings) == 2 and _uniq(out)


def test_f111_v87_same_trace_twice_on_line_distinct():
    out = _run("V87", sample_model(tree={"a.md": "이 카드는 짧다. 이 카드는 끝난다.\n"}))
    assert len(out.findings) == 2 and _uniq(out)


def test_f111_v68_repeated_reference_entry_distinct():
    md = "## 영문\n- et al. (2020). T. [REF-001]\n- et al. (2020). T. [REF-001]\n"
    out = _run("V68", sample_model(reference_md={"참고문헌.md": md}))
    assert len(out.findings) == 2 and _uniq(out)


def test_f111_engine_reports_duplicates_without_changing_count():
    from pathlib import Path

    from techdoc_core.bundles.schema import GateSpec
    from techdoc_core.qc.config import Paths, ProjectConfig

    def dup(model):
        return GateOutput(1, [Finding("a.md:1", "같은 글")] * 2)

    spec = GateSpec(id="VX", title="시험", layer="본체", core=["품질"], level="경고",
                    inputs=["tree"])
    p = Path(".")
    cfg = ProjectConfig(root=p, paths=Paths(p, p, p, p, p, p))
    rep = run_qc(sample_model(tree={"a.md": "x\n"}), {"VX": spec}, {"VX": dup}, cfg)
    row = rep["results"][0]
    assert row["count"] == 2 and row["duplicates"] == 1  # 건수는 그대로, 중복은 따로 알림
    assert "[중복] VX 1건" in format_report(rep)


# ── F112 V57: 분할 카드는 부모 절 단위 · 결론 절도 결론 ──

def _split(body, title="본문", **extra):
    return {"sections": {"s1": {"title": title, "body": body}}, **extra}


def test_f112_v57_split_group_without_conclusion_is_target():
    cards = {"1.4.L1": _split("앞 본문."), "1.4.L2": _split("뒤 본문.")}
    out = _run("V57", sample_model(cards=cards))
    assert out.targets_read == 1
    assert [f.loc for f in out.findings] == ["1.4|-: 결론"]


def test_f112_v57_last_split_conclusion_section_counts():
    cards = {"1.4.L1": _split("앞 본문."),
             "1.4.L2": {"sections": {"s1": {"title": "본문", "body": "뒤 본문."},
                                     "s2": {"title": "1.4 종합 — 다음 장으로", "body": "정리한다."}}}}
    assert _run("V57", sample_model(cards=cards)).findings == []


def test_f112_v57_conclusion_section_roman():
    cards = {"II.6.L1": _split("앞."),
             "II.6.L2": {"sections": {"s1": {"title": "II.6 종합 — 지도", "body": "정리."}}}}
    m = sample_model(cards=cards, numbering={"section": "roman", "appendix": "letter"})
    out = _run("V57", m)
    assert out.targets_read == 1 and out.findings == []


def test_f112_v57_parent_card_present_keeps_original_target():
    """부모 카드가 있으면 원본처럼 부모만 본다(분할은 따로 세지 않음)."""
    conc = ["관측은 기록이다.", "기록은 판단의 바탕이다.", "판단은 묶인다."]
    cards = {"1.4": _split("본문.", conclusion=conc), "1.4.L1": _split("앞.")}
    out = _run("V57", sample_model(cards=cards))
    assert out.targets_read == 1 and out.findings == []


def test_f112_v57_conclusion_titles_configurable():
    cards = {"1.1": {"sections": {"s1": {"title": "종합", "body": "정리."}}}}
    m = sample_model(cards=cards, extra={"structure": {"conclusion_titles": []}})
    assert len(_run("V57", m).findings) == 1


# ── F113 V88: 장을 가로지르는 표제 틀 ──

_HEADS = ["무엇을 정하나", "어떤 순서로 하나", "어떻게 확인하나"]


def _chapter(n, heads=_HEADS):
    return "".join(f"## {n}.{i} {h} — 항목 {n}\n\n본문.\n\n" for i, h in enumerate(heads, 1))


def test_f113_v88_frame_across_chapters():
    tree = {f"{n}장/{n}.1. 가.md": _chapter(n) for n in range(1, 5)}
    out = _run("V88", sample_model(tree=tree))
    assert len(out.findings) == 4  # 틀이 나온 장마다 하나
    assert all("장에 걸쳐" in f.msg for f in out.findings)


def test_f113_v88_frame_below_chapter_threshold():
    tree = {f"{n}장/{n}.1. 가.md": _chapter(n) for n in range(1, 4)}
    assert _run("V88", sample_model(tree=tree)).findings == []


def test_f113_v88_frame_threshold_configurable():
    tree = {f"{n}장/{n}.1. 가.md": _chapter(n) for n in range(1, 3)}
    m = sample_model(tree=tree, extra={"repeat": {"frame_chapters": 2}})
    assert len(_run("V88", m).findings) == 2


def test_f113_v88_block_heads_exempt_frame():
    tree = {f"{n}장/{n}.1. 가.md": _chapter(n) for n in range(1, 6)}
    m = sample_model(tree=tree, extra={"repeat": {"block_heads": _HEADS}})
    assert _run("V88", m).findings == []


def test_f113_v88_different_heads_no_frame():
    tree = {f"{n}장/{n}.1. 가.md": _chapter(n, [f"배경 {n}", f"방법 {n}", f"결과 {n}"])
            for n in range(1, 6)}
    assert _run("V88", sample_model(tree=tree)).findings == []


# ── F114 V24·V56: 자칭 서술·자기 선언 꼴 ──

def test_f114_v24_new_verbs_and_section_noun():
    text = ("이 절은 설계 단계의 경계를 정한다.\n\n이 섹션은 도구 배정을 정리한다.\n\n"
            "이 장은 무엇을 확인해야 하는지 묻는다.\n")
    assert len(_run("V24", sample_model(tree={"a.md": text})).findings) == 3


def test_f114_v24_general_prose_not_flagged():
    text = "이 장비는 값을 정한다.\n\n이 절차를 따라 본다.\n\n이 판단은 사람이 정리한다.\n"
    assert _run("V24", sample_model(tree={"a.md": text})).findings == []


def test_f114_v24_word_lists_replaceable_by_config():
    """시리즈 층처럼 원본 목록을 지키는 설정 — 새 동사(정한다)는 빠진다."""
    text = "이 절은 경계를 정한다.\n\n이 장은 관측 체계를 다룬다.\n"
    m = sample_model(tree={"a.md": text}, extra={"prose": {
        "selfref_nouns": ["장", "절", "항", "영역", "판"],
        "selfref_verbs": ["답한다", "다룬다", "적는다", "세운다", "하는 일", "무엇인가"]}})
    assert len(_run("V24", m).findings) == 1


def test_f114_v56_this_documents_interpretation():
    text = "단계 구분은 이 문서의 해석이다.\n\n배정은 이 문서의 판단이며 바뀔 수 있다.\n"
    assert len(_run("V56", sample_model(tree={"a.md": text})).findings) == 2


def test_f114_v56_source_label_not_flagged():
    text = "단계 구분(이 문서의 정리)은 표와 같다.\n"
    assert _run("V56", sample_model(tree={"a.md": text})).findings == []


# ── F115 V87: 계획 문서 인용 ──

def test_f115_v87_plan_doc_citations_by_config():
    text = "요구는 둘이다(PRD §1.2). 우선순위는 PRD REQ-003을 따른다. 계획은 case_plan.md에.\n"
    m = sample_model(tree={"a.md": text},
                     extra={"leak": {"plan_docs": ["PRD", "case_plan.md"]}})
    msgs = [f.msg for f in _run("V87", m).findings]
    assert len(msgs) == 3 and all(x.startswith("plan_doc:") for x in msgs)


def test_f115_v87_plan_docs_default_empty():
    text = "요구는 둘이다(PRD §1.2).\n"
    assert _run("V87", sample_model(tree={"a.md": text})).findings == []


# ── F116 V2·V14·V47 꼴 ──

def test_f116_v2_sub_tables_not_duplicate_numbers():
    body = (f"**표 1.1-1.** 범위 (가) 요약\n\n{TBL}\n**표 1.1-1.** (나) 전체 (계속)\n\n{TBL}\n"
            "표 1.1-1을 본다.\n")
    m = sample_model(cards={"1.1": _card(body)})
    assert not [f for f in _run("V2", m).findings if "번호 중복" in f.msg]


def test_f116_v2_sub_tables_roman_bold_caption():
    """roman 문서 꼴 — 번호 뒤 마침표 없이 굵은 캡션 줄 전체."""
    body = (f"**표 IV.19-1 범위 (가) 요약**\n\n{TBL}\n**표 IV.19-1 (나) 전체 (계속)**\n\n{TBL}\n"
            "표 IV.19-1을 본다.\n")
    m = sample_model(cards={"IV.19": _card(body)},
                     numbering={"section": "roman", "appendix": "letter"})
    assert not [f for f in _run("V2", m).findings if "번호 중복" in f.msg]


def test_f116_v2_plain_duplicate_still_flagged():
    body = f"**표 1.1-1.** 가\n\n{TBL}\n**표 1.1-1.** 나\n\n{TBL}\n"
    m = sample_model(cards={"1.1": _card(body)})
    assert [f for f in _run("V2", m).findings if "번호 중복" in f.msg]


def test_f116_v14_token_cut_at_hyphen_dropped():
    m = sample_model(cards={"1.1": _card("본문은 AI 보조 설계를 쓴다.",
                                         quick_summary="AI-보조 설계를 본다")})
    assert _run("V14", m).findings == []


def test_f116_v47_asterisk_inside_inline_code_not_italic():
    text = "경로는 `case/*/ai/<단계>/log.md`와 `case/*`에 둔다.\n"
    assert _run("V47", sample_model(tree={"a.md": text})).findings == []
    assert len(_run("V47", sample_model(tree={"a.md": "*기울인 말*\n"})).findings) == 1


# ── F117 V21: 한 줄 정리 칸은 설정으로 ──

def _goal_qs(**more):
    return {"goal": "기록의 요건이 무엇인지 알고, 값 하나를 판단에 쓸 수 있게 적을 수 있다.",
            "questions": ["기록의 요건은 무엇인가?", "여덟 항목은 어떤 차례로 채우나?"], **more}


def test_f117_v21_one_sentence_allowed_by_default():
    qs = {"one_sentence": "한 줄.", "summary": "기록은 판단의 바탕이며 값 하나를 적을 때 근거를 함께 둔다."}
    m = sample_model(kind="methodology", cards={"1.1": _card("x", quick_summary=qs)})
    assert _run("V21", m).findings == []


def test_f117_v21_retired_fields_from_config():
    qs = {"one_sentence": "한 줄.", "summary": "기록은 판단의 바탕이며 값 하나를 적을 때 근거를 함께 둔다."}
    m = sample_model(kind="methodology", cards={"1.1": _card("x", quick_summary=qs)},
                     extra={"structure": {"summary_retired_fields": ["one_sentence"]}})
    msgs = [f.msg for f in _run("V21", m).findings]
    assert msgs == ["1.1 한 줄 정리가 남아 있다(one_sentence)"]


def test_f117_v21_summary_limits_from_config():
    qs = {"summary": "짧다."}
    base = sample_model(kind="methodology", cards={"1.1": _card("x", quick_summary=qs)})
    assert len(_run("V21", base).findings) == 1  # 기본 20~160자
    loose = sample_model(kind="methodology", cards={"1.1": _card("x", quick_summary=qs)},
                         extra={"structure": {"summary_limits": {"min_chars": 1}}})
    assert _run("V21", loose).findings == []
