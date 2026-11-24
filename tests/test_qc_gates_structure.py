"""구조·상호참조 게이트 12종 (v1.11-b Task 2 — 시리즈 check_v2·prose_gates 이식, F85).

V2·V21·V26·V30·V31·V34·V39·V44·V57·V59·V72·V78. 원본 자기검사(selftest) 표본이 있는 게이트
(V2·V21·V30·V39·V44·V57·V72·V78)는 그 표본을 옮겼다.
"""
import json

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.config import load_config
from techdoc_core.qc.engine import run_selftests
from techdoc_core.qc.gates import structure as st
from techdoc_core.qc.model import TreeFile
from techdoc_core.qc.numbering import section_file_re
from techdoc_core.qc.registry import REGISTRY, sample_model

GATES = ["V2", "V21", "V26", "V30", "V31", "V34", "V39", "V44", "V57", "V59", "V72", "V78"]


def _n(gid, model):
    return len(REGISTRY[gid](model).findings)


def _card(body, title="", **extra):
    return {"sections": {"s1": {"title": title, "body": body}}, **extra}


def test_all_structure_gates_registered_with_samples():
    for g in GATES:
        assert g in REGISTRY, g
        assert len(REGISTRY[g].samples) >= 2, g
    assert run_selftests({g: REGISTRY[g] for g in GATES}) == []


# ── V2 끊어진 상호참조 ──

def test_v2_selftest_split_and_dead_section_refs():
    # 원본 selftest — 분할 카드의 기저 ID는 절로 실재한다. 진짜 죽은 참조는 잡는다
    x2 = ["0.4", "1.4.L1", "1.4.L2", "11.1.XL3", "10.1.L2", "3.3.bak_pre_rewrite",
          "A-1.4.L1", "B-10.L3", "C-1.XL4", "D-10", "D-6.L1", "E1.XL3", "F5", "F6.L3",
          "G1.XL2", "H-15", "I-1"]
    cards = {c: _card("x") for c in x2}
    for s in ["1.4절에서 다룬 엣지 컴퓨팅", "11.1절의 벼 사례", "10.1절", "0.4절",
              "에이커당 $18.1 절감을 검증했다", "비용 18.1 절감"]:
        m = sample_model(cards={**cards, "9.9": _card(s)})
        assert _n("V2", m) == 0, s
    for s in ["18.1절에서 다룬다", "1.5절 참조", "11.2절"]:
        m = sample_model(cards={**cards, "9.9": _card(s)})
        assert _n("V2", m) == 1, s
    assert st.base_id("11.1.XL3") == "11.1" and st.base_id("E1.XL3") == "E1"
    assert st.base_id("D-6.L1") == "D-6" and st.base_id("2.A.8") == "2.A.8"
    apps = st.appendix_letters_of(x2)
    assert set("ABCDEFGHI") <= apps and "J" not in apps
    assert st.appendix_letters_of(["2.A.8", "1.A.0", "5.2", "10.3"]) == set()
    assert st.appendix_letters_of(["A-1", "J-1", "C-5"]) == {"A", "J", "C"}


def test_v2_chapter_and_appendix_refs():
    cards = {"1.1": _card("제3장과 章1·4를 본다. 별첨 B 참조."), "A-1": _card("x")}
    out = REGISTRY["V2"](sample_model(cards=cards))
    # 제3장 없음 · 章4 없음(나열) · 별첨 B 없음
    assert len(out.findings) == 3
    assert all(f.loc.startswith("1.1|s1:") for f in out.findings)
    assert out.targets_read == 2


def test_v2_outline_declares_appendix():
    m = sample_model(cards={"1.1": _card("별첨 B 참조.")}, outline={"appendices": [{"id": "B"}]})
    assert _n("V2", m) == 0


def test_v2_draft_heading_is_section():
    m = sample_model(cards={"1.1": _card("3.4절을 본다.")}, draft={"p.md": "## 3.4 제목\n본문"})
    assert _n("V2", m) == 0


def test_v2_item_refs():
    card = {"sections": {"s1": {"title": "관측의 세 층위 (I)", "body": "x"},
                         "s2": {"title": "b", "body": "「관측의 세 층위」 항과 「없는 항」 항, 「내용연수」 항목"}}}
    assert _n("V2", sample_model(cards={"1.1": card})) == 1


def test_v2_peer_doc_item_ref_needs_config():
    body = "방제편 16.3의 「다른 편 항」 항을 본다."
    assert _n("V2", sample_model(cards={"1.1": _card(body)})) == 1
    m = sample_model(cards={"1.1": _card(body)},
                     extra={"structure": {"peer_doc_names": ["[가-힣]{1,6}편"]}})
    assert _n("V2", m) == 0


def test_v2_figure_undefined_and_duplicate_not_exemptable_loc():
    out = REGISTRY["V2"](sample_model(cards={"1.1": _card("표 1.1-2를 본다. 표 2.1-1은 남의 표.")}))
    assert len(out.findings) == 1
    assert not out.findings[0].loc.startswith(("1.1|", "1.1:"))  # 원본은 hit()를 거치지 않음
    ok = "**표 1.1-2.** 제목\n\n| a |\n|---|\n\n표 1.1-2를 본다."
    assert _n("V2", sample_model(cards={"1.1": _card(ok)})) == 0
    dup = "**표 1.1-1.** 가\n\n표 1.1-1. 나\n"
    assert _n("V2", sample_model(cards={"1.1": _card(dup)})) == 1


def test_v2_no_cards_is_zero_target():
    out = REGISTRY["V2"](sample_model(tree={"a.md": "1.5절"}))
    assert out.targets_read == 0 and out.findings == []


# ── Review Focus 1: 로마 숫자 부 ──

def test_roman_section_refs_not_false_positive():
    roman = {"section": "roman", "appendix": "letter"}
    cards = {"II.6.L1": _card("x"), "II.6.3": _card("II.6.3절을 본다. 제6장도 본다.")}
    tree = {"II/II.6.md": "## II.6.3 제목\n\nII.6.3절을 본다.\n"}
    m = sample_model(cards=cards, tree=tree, numbering=roman)
    assert _n("V2", m) == 0 and _n("V30", m) == 0
    # 앵커 없는 로마 숫자 참조는 roman에서 잡는다
    dead = sample_model(cards={"II.6": _card("II.9.9절을 본다.")},
                        tree={"a.md": "## II.6.1 제목\n\nII.9.9절을 본다.\n"}, numbering=roman)
    assert _n("V2", dead) == 1 and _n("V30", dead) == 1
    # 같은 글을 arabic으로 읽으면 원본 정규식 그대로 — 로마 숫자 참조는 보지 않고, 아라비아는 잡는다
    ar = sample_model(cards={"II.6": _card("II.9.9절을 본다. 7.7절도.")},
                      tree={"a.md": "## II.6.1 제목\n\nII.9.9절을 본다. 7.7.1절도.\n"})
    assert _n("V2", ar) == 1 and _n("V30", ar) == 1


# ── V21 핵심요약 규약 ──

_G_OK = {"goal": "기록의 요건이 무엇인지 알고, 값 하나를 판단에 쓸 수 있게 적을 수 있다.",
         "questions": ["기록의 요건은 무엇인가?", "여덟 항목은 어떤 차례로 채우나?"]}


def test_v21_selftest_goal_box():
    assert st.is_goal_form(_G_OK) and not st.goal_defects(_G_OK)
    assert not st.is_goal_form({"summary": "옛 꼴 요약이다."}) and not st.is_goal_form("문자열")
    q = _G_OK["questions"]
    assert st.goal_defects({"goal": "짧다.", "questions": q})
    assert st.goal_defects({"goal": _G_OK["goal"] + " 둘째 문장이다.", "questions": q})
    assert st.goal_defects({"goal": _G_OK["goal"], "questions": ["하나뿐인가?"]})
    assert st.goal_defects({"goal": _G_OK["goal"], "questions": ["가?", "나?", "다?", "라?", "마?"]})
    assert st.goal_defects({"goal": _G_OK["goal"], "questions": ["기록의 요건은 무엇인가", "차례는?"]})
    assert st.goal_defects({"goal": _G_OK["goal"], "questions": ["가" * 81 + "?", "나?"]})
    assert st.goal_questions(_G_OK) == q and st.goal_questions({"summary": "x"}) == []


def test_v21_missing_summary_only_body_cards():
    m = sample_model(cards={"1.1": _card("x"), "0.1": _card("x"), "A-1": _card("x")})
    out = REGISTRY["V21"](m)
    assert len(out.findings) == 1 and out.findings[0].loc.startswith("1.1|-:")
    assert out.targets_read == 3


def test_v21_goal_box_and_one_sentence():
    good = sample_model(cards={"1.1": _card("x", quick_summary=_G_OK)})
    assert _n("V21", good) == 0
    bad = sample_model(cards={"1.1": _card("x", quick_summary={**_G_OK, "goal": "짧다."})})
    assert _n("V21", bad) == 1
    summ = "이 절은 관측값을 기록하는 요건과 그 쓰임을 다룬다."
    old = sample_model(cards={"1.1": _card("x", quick_summary={"summary": summ, "one_sentence": "→ 끝"})})
    assert _n("V21", old) == 1


def test_v21_jargon_is_config_only():
    summ = "이 절은 칼만이득으로 관측값을 고르는 요건을 다룬다."
    card = {"1.1": _card("x", quick_summary={"summary": summ})}
    assert _n("V21", sample_model(cards=card)) == 0
    m = sample_model(cards=card, extra={"structure": {"qs_jargon": ["칼만이득", "EnKF"]}})
    assert _n("V21", m) == 1


def test_v21_no_cards_zero_target():
    assert REGISTRY["V21"](sample_model(tree={"a.md": "x"})).targets_read == 0


# ── V57 절 끝 결론 ──

def test_v57_missing_and_good_conclusion():
    assert _n("V57", sample_model(cards={"1.1": _card("본문 3건.")})) == 1
    conc = ["관측은 기록이다.", "기록은 판단의 바탕이다.", "판단은 3건으로 묶인다."]
    good = sample_model(cards={"1.1": _card("본문 3건.", conclusion=conc)})
    assert _n("V57", good) == 0
    # 핵심 질문 셋인데 결론 둘 → 지적
    qs = {**_G_OK, "questions": ["가는 무엇인가?", "나는 무엇인가?", "다는 무엇인가?"]}
    few = sample_model(cards={"1.1": _card("본문 3건.", conclusion=conc[:2], quick_summary=qs)})
    assert _n("V57", few) == 1


def test_v57_targets_only_body_sections():
    out = REGISTRY["V57"](sample_model(cards={"0.1": _card("x"), "A-1": _card("x"), "1.1.L1": _card("x")}))
    assert out.targets_read == 0 and out.findings == []


# ── V59 별첨 문자 ──

def test_v59_appendix_letters_continuous():
    assert _n("V59", sample_model(cards={"A-1": _card("x"), "C-1": _card("x")})) == 1
    assert _n("V59", sample_model(cards={"A-1": _card("x"), "B-1": _card("x")})) == 0
    out = REGISTRY["V59"](sample_model(cards={"1.1": _card("x")}))
    assert out.findings == [] and out.targets_read == 1
    assert REGISTRY["V59"](sample_model()).targets_read == 0


# ── V26 개요 절 아래 분업·항해 ──

def test_v26_overview_nav_subsection():
    assert _n("V26", sample_model(tree={"a.md": "## 1.A.0 개요\n\n### 부 사이 분업\n\n### 작물 개관\n"})) == 1
    assert _n("V26", sample_model(tree={"a.md": "## 1.A.1 본론\n\n### 부 사이 분업\n"})) == 0
    assert REGISTRY["V26"](sample_model()).targets_read == 0


# ── V30 md 상호참조 ──

def test_v30_selftest_dead_xrefs():
    anc = {"5.A.1", "1.A.0.4", "3.2.1"}
    must = ["5.A.2에서 다룬다", "1.A.0.5 참조", "3.2.2절을 보라", "(3.1.1 참조)",
            "M3 4.2.1절", "표준은 7.1.7절에서 정한다", "6.2.1·6.2.3에서 본다",
            "WOFOST 7.1.7 판과 별개로 7.1.8절을 본다"]
    nots = ["5.A.1에서 다룬다", "2024.10.1 발표", "2017.8.3 개정", "IEEE 802.15.4 기반",
            "Zigbee 3.0 (IEEE 802.15.4)", "DSSAT v4.8.5 공개", "v4.8.5.0 (2024년 12월)",
            "WOFOST 7.1.7과 WCC 2.1", "OGC WMS 1.3.0 표준",
            "LoRaWAN 1.0(2015)에서 1.0.1(2017)·1.0.2(2018)·1.0.3(2018)·1.0.4(2020)",
            "LoRaWAN 1.1·1.0.4·LR-FHSS", "Transformers v4.29.0+(2023.05)", "버전 3.3.2 배포",
            "형제 편 5.B.3 으로 넘어간다",
            "2014년 WOFOST 7.1.7 + WCC 2.1. PCSE 이전 세대(7.1.7까지)의 표준이었다"]
    for s in must:
        assert st.dead_xrefs(s, anc, ("5.B.",)), s
    for s in nots:
        assert not st.dead_xrefs(s, anc, ("5.B.",)), s


def test_v30_tree_anchors_peer_and_appendix():
    tree = {"a.md": "## 3.2.1 제목\n\n3.2.1절과 3.2.2절, 별첨 A-1·별첨 B-2.\n",
            "b.md": "# A-1 별첨 머리\n\n**표 3.2.1-1.** 표\n"}
    out = REGISTRY["V30"](sample_model(tree=tree))
    assert len(out.findings) == 2 and out.targets_read == 2
    m = sample_model(tree={"a.md": "5.B.3을 본다.\n"},
                     extra={"structure": {"peer_prefix": ["5.B."]}})
    assert _n("V30", m) == 0
    assert _n("V30", sample_model(tree={"a.md": "5.B.3을 본다.\n"})) == 1


# ── V31 표제 형식 ──

def test_v31_heading_forms():
    assert _n("V31", sample_model(tree={"a.md": "## 1.1 왜 노지인가\n"})) == 1
    assert _n("V31", sample_model(tree={"a.md": "## 1.1 관측 체계\n### 1.1.1 수분 관측 — 원리\n"})) == 1
    assert _n("V31", sample_model(tree={"a.md": "## 1.1 관측 체계\n"})) == 0


def test_v31_meta_words_config():
    text = {"a.md": "## 1.1 이 작물편의 구성\n"}
    assert _n("V31", sample_model(tree=text)) == 0
    assert _n("V31", sample_model(tree=text, extra={"prose": {"meta_words": ["작물편"]}})) == 1


# ── V34 절 도입부 ──

def test_v34_section_lead():
    assert _n("V34", sample_model(tree={"a.md": "## 1.1 가\n\n### 1.1.1 나\n본문\n"})) == 1
    lead = ("이 절은 관측값을 기록하는 요건과 그 쓰임을 정하고 남는 물음을 다음 절로 넘긴다. "
            "관측 주기와 기록 단위도 함께 밝힌다.")
    assert _n("V34", sample_model(tree={"a.md": f"## 1.1 가\n\n{lead}\n\n### 1.1.1 나\n"})) == 0


def test_v34_intro_exempt_titles_config():
    text = {"a.md": "## 0.1 발간사\n\n### 1. 발간에 부쳐\n"}
    assert _n("V34", sample_model(tree=text)) == 1
    m = sample_model(tree=text, extra={"structure": {"intro_exempt_titles": ["발간사"]}})
    assert _n("V34", m) == 0


# ── V39 표제 꼴 ──

def test_v39_selftest_head_forms():
    must = ["# 8.1 — 무엇을 보고 무엇을 정하나", "## 처방이 부딪힐 때", "## 9.2 작기를 돌아볼 때",
            "## 이 표준은 이로운가", "### 왜 노지인가?", "## 무엇을 재고 판단하며"]
    nots = ["# 9.2 — 처방 조정과 작기 평가", "## 작기 평가", "## 열린 고리의 한계", "## 경험을 적어 두는 일",
            "## 여건이 맞지 않을 때 함께 넘는 길", "## 한 값으로 합치는 일", "## 참가",
            "# 12.1 — 전주기 종합", "## 수확 적기 판정", "## 넷 가운데 하나"]
    for h in must:
        assert _n("V39", sample_model(tree={"a.md": h})) == 1, h
    for h in nots:
        assert _n("V39", sample_model(tree={"a.md": h})) == 0, h


def test_v39_same_title_section_and_item_and_index_skip():
    text = "## 1.1 결론\n\n### 1.1.1 결론\n"
    assert _n("V39", sample_model(tree={"a.md": text})) == 1
    out = REGISTRY["V39"](sample_model(tree={"INDEX.md": "## 왜 노지인가?"}))
    assert out.findings == [] and out.targets_read == 0


# ── V44 물음꼴 볼드 소표제 ──

def test_v44_bold_question():
    for s in ["**왜 이 다섯인가.**", "**무엇이 다른가?**", "**어디까지 쓸 수 있을까.**"]:
        assert _n("V44", sample_model(tree={"a.md": s})) == 1, s
    for s in ["**적용.**", "**주장**", "**기술의 화려함이 아니라 잃는 크기가 순서를 정한다.**",
              "| **왜 이 다섯인가.** |", "```\n**왜 이 다섯인가.**\n```"]:
        assert _n("V44", sample_model(tree={"a.md": s})) == 0, s


# ── V72 별첨 번호 꼴 ──

def test_v72_appendix_caption_number():
    assert _n("V72", sample_model(tree={"a.md": "**표 A-1-2.** 작기 일정"})) == 1
    for s in ["**표 A-2.** 작기 일정", "표 3.1-2", "## 표 A-1-2 표제는 보지 않음"]:
        assert _n("V72", sample_model(tree={"a.md": s})) == 0, s
    assert REGISTRY["V72"](sample_model(tree={"INDEX.md": "표 A-1-2"})).targets_read == 0


def test_v72_letters_from_config():
    m = sample_model(tree={"a.md": "표 M-1-2"})
    assert _n("V72", m) == 1  # 기본 A-Z
    m = sample_model(tree={"a.md": "표 M-1-2"}, extra={"structure": {"appendix_letters": "A-K"}})
    assert _n("V72", m) == 0


# ── V78 항 안 번호 층위 ──

def test_v78_selftest_subitems():
    ok = "# 1.1 — 가\n\n## 1. 갈래\n\n### 1) 가\n\n본문\n\n### 2) 나\n\n    1. 상자 안 목록\n\n## 2. 결론\n\n1. 답\n2. 답\n"
    cases = [(ok, ""),
             ("## 1. 갈래\n\n### 1) 가\n\n### ① 나\n", "섞임"),
             ("## 1. 갈래\n\n### 1) 가\n\n### 3) 나\n", "어긋남"),
             ("## 1. 갈래\n\n### 1) 가\n\n### 2) 종합\n", "종합"),
             ("## 1. 갈래\n\n### 1) 가\n\n1. 목록\n2. 목록\n", "목록과"),
             ("## 1. 갈래\n\n" + "".join(f"### {n}) 가\n\n" for n in range(1, 9)), "묶을"),
             ("## 1. 갈래\n\n### 1) 가\n\n### 나\n", "없는 소항"),
             ("## 1. 갈래\n\n```mermaid\n### 1) 가\n```\n\n1. 목록\n", "")]
    for s, want in cases:
        got = " ".join(m for _, m in st.subitem_issues(s))
        assert (want in got) if want else not got, (s[:30], got)


def test_v78_only_section_files():
    bad = "## 1. 갈래\n\n### 1) 가\n\n### 3) 나\n"
    assert _n("V78", sample_model(tree={"제1부/1.1. 가.md": bad})) == 1
    for rel in ("개요/1.1. 가.md", "부록/1.1. 가.md", "INDEX.md", "가.md"):
        out = REGISTRY["V78"](sample_model(tree={rel: bad}))
        assert out.findings == [] and out.targets_read == 0, rel
    m = sample_model(tree={"0_앞/1.1. 가.md": bad},
                     extra={"structure": {"folder_names": ["0_"]}})
    assert _n("V78", m) == 0


def test_section_file_re_styles():
    assert section_file_re("arabic").match("3.1. 가.md")
    assert not section_file_re("arabic").match("II.6. 가.md")
    assert section_file_re("roman").match("II.6. 가.md")


# ── 어댑터: outline 경로 ──

def test_outline_path_loaded(tmp_path):
    out = tmp_path / "output"
    (out / "cards").mkdir(parents=True)
    (out / "cards" / "1.1_card.json").write_text(json.dumps(_card("별첨 B 참조.")), encoding="utf-8")
    (out / "final_outline.json").write_text(json.dumps({"appendices": ["B"]}), encoding="utf-8")
    model = build_model(tmp_path, load_config(tmp_path))
    assert model.outline == {"appendices": ["B"]}
    assert _n("V2", model) == 0


def test_draft_param_in_sample_model():
    m = sample_model(draft={"p.md": "x"})
    assert m.draft == [TreeFile("p.md", "x")]
