"""문장(산문) 게이트 18종 (v1.11-b Task 3 — 시리즈 check_v2·prose_gates 이식, F85).

V23·V24·V25·V27·V28·V29·V35·V36·V41·V41W·V43·V50·V53·V54·V56·V69·V76·V81. 원본 자기검사(selftest)
표본이 있는 게이트(V35·V36·V41·V43·V50·V53·V54·V56·V69·V76·V81·V41 넓힘)는 그 표본을 옮겼다.
"""
import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.qc.engine import run_selftests
from techdoc_core.qc.gates import sentences as se
from techdoc_core.qc.registry import REGISTRY, sample_model

GATES = ["V23", "V24", "V25", "V27", "V28", "V29", "V35", "V36", "V41", "V41W", "V43", "V50",
         "V53", "V54", "V56", "V69", "V76", "V81"]
TREE_GATES = [g for g in GATES if g != "V23"]
# 시리즈 관례 값 — 회귀 설정(make_configs)이 넣는 것과 같은 값
SERIES_MARKERS = {"goalbox": "qs-goalbox", "cited_refs": r"^\*\*인용 참고문헌", "conclusion": r"결론\s*$"}


def _n(gid, model):
    return len(REGISTRY[gid](model).findings)


def _t(gid, text, name="a.md", **kw):
    return _n(gid, sample_model(tree={name: text}, **kw))


def _card(body, title=""):
    return {"sections": {"s1": {"title": title, "body": body}}}


def test_all_sentence_gates_registered_with_samples():
    for g in GATES:
        assert g in REGISTRY, g
        assert len(REGISTRY[g].samples) >= 2, g
    assert run_selftests({g: REGISTRY[g] for g in GATES}) == []


def test_zero_targets_when_no_input():
    empty = sample_model()
    for g in GATES:
        out = REGISTRY[g](empty)
        assert out.targets_read == 0 and not out.findings, g


def test_specs_levels_readability_warning():
    """E18 11번 — 가독성 게이트의 플러그인 기본은 경고, 결함 게이트만 막음, 시범 셋."""
    specs = load_gate_specs([("core", core_bundle_dir())])
    assert {g: specs[g].level for g in ("V23", "V24", "V50")} == dict.fromkeys(
        ("V23", "V24", "V50"), "막음")
    for g in ("V25", "V27", "V28", "V29", "V35", "V36", "V41", "V43", "V53", "V54", "V56", "V69"):
        assert specs[g].level == "경고", g
    for g in ("V76", "V81", "V41W"):
        assert specs[g].level == "시범", g


# ── V23 붙어 버린 두 문장 (카드) ──

def test_v23_glued_and_echoed():
    assert _n("V23", sample_model(cards={"1.1": _card("양방향 결합이다 현장에서 잰 값이 있다.")})) == 1
    assert _n("V23", sample_model(cards={"1.1": _card("양방향 결합이다. 현장에서 잰 값이 있다.")})) == 0
    # 가운뎃점 열거 뒤 수관형사 — 한 문장
    lst = "걷는다·안 걷는다·갖지 않는다 세 갈래를 세로로 놓고 본다."
    assert _n("V23", sample_model(cards={"1.1": _card(lst)})) == 0
    # 표·펜스 줄은 산문이 아니다
    assert _n("V23", sample_model(cards={"1.1": _card("| 결합이다 현장에서 |\n```\n이다 그래서 x\n```")})) == 0
    # 종결어미 없이 「그래서」로 이어진 되풀이 — 접합(V23_GLUE)이 아니라 되풀이만 잡힌다
    echo = "기준을 못 채우면 단위를 다시 잡는 것 그래서 관측을 못 채우면 단위를 다시 잡는 것."
    out = REGISTRY["V23"](sample_model(cards={"1.1": _card(echo)}))
    assert len(out.findings) == 1 and out.findings[0].loc.startswith("1.1|s1:")
    assert out.targets_read == 1


# ── V24 메타 서술 · 집필지시 누수 ──

def test_v24_meta_paragraph_and_quote():
    assert _t("V24", "이 장은 관측 체계를 다룬다.\n") == 1
    assert _t("V24", "> 이 절은 무엇을 다루는가에 답한다.\n") == 1
    assert _t("V24", "관측 체계는 2.E.4에 있다.\n") == 0
    assert _t("V24", "본문 작업을 하고 카드의 도입부를 쓴다.\n") == 2  # 집필 지시 둘


def test_v24_meta_words_config():
    s = "이 작물편은 관측 체계를 다룬다.\n"
    assert _t("V24", s) == 0
    assert _t("V24", s, extra={"prose": {"meta_words": ["작물편"]}}) == 1


# ── V25 도표 되읽기 ──

def test_v25_row_reread_after_table():
    tbl = "| 가 | 나 |\n|---|---|\n| 1 | 2 |\n\n"
    assert _t("V25", tbl + "첫째 줄은 관수량이다.\n") == 1
    assert _t("V25", "두 줄을 적는다. 첫째 줄은 문장이다.\n") == 0  # 앞에 표가 없다
    assert _t("V25", tbl + "## 1.1 가\n\n첫째 줄은 관수량이다.\n") == 0  # 표제를 넘지 않는다


# ── V27 문장 길이 · V28 줄표 · V29 강조 밀도 ──

def test_v27_sentence_length_and_cite_exemption():
    long_s = "가" * 161 + "다."
    assert _t("V27", long_s + "\n") == 1
    assert _t("V27", "가" * 150 + "다.\n") == 0
    assert _t("V27", "## 1.1 근거·인용\n\n" + long_s + "\n") == 0
    # 마크업·영문 원어 풀이는 세지 않는다
    s = "**" + "가" * 150 + "**[REF-001] 절차(SOP, Standard Operating Procedure Long Name)다."
    assert _t("V27", s + "\n") == 0


def test_v28_dash_uses():
    assert se.dash_uses("A — 삽입구 — 뒤에 본문이 열 자 넘게 이어진다") == 1
    assert se.dash_uses("A — B — C") == 2
    assert _t("V28", "가는 — 나는 — 다이다.\n") == 1
    assert _t("V28", "가는 — 짧은 삽입 — 뒤에 이어지는 본문이 충분히 길다.\n") == 0


def test_v29_bold_density_runin_excluded():
    assert _t("V29", "값은 **가**와 **나**를 본다.\n") == 1
    assert _t("V29", "**가**와 **나**를 본다.\n") == 0  # 첫머리 짧은 굵게는 러닝헤드로 뺀다(원본)
    assert _t("V29", "**주장.** 값은 **가**다.\n") == 0
    assert _t("V29", "- **대상** — 값\n- **크기** — 값\n") == 0  # 목록 항목은 저마다 한 문단


# ── V35 낯선 표현 · V36 구성 설명 (원본 selftest) ──

V35_MUST = ["그 편들이 딛고 선 공통 원리", "나머지는 그 둘을 떠받치는 장치다", "현장이 손에 쥐는 것",
            "한자를 걷어내고", "다섯 장이 그것을 되받아 판정한다", "구조로 여물어 온 것", "다시 짚는다"]
V35_NOT = ["밭의 자리를 고른다", "사람이 맡는 몫", "기준을 세운다", "짚단을 묶는다", "결과를 넘겨짚는다"]
V36_MUST = ["왼쪽 「구분」 칸을 따라 내려가면 열다섯 편이", "「사람이 맡는 몫」 열이 이 표의 요점이다",
            "표는 왼쪽에 작목을 두고 오른쪽에 기준값을 붙인다", "행은 6개이고 열은 4개다",
            "행은 16개(개입 15 + 합계)이고 열은 9개다", "표는 왼쪽에 단계를 두고 오른쪽에 기준을 붙입니다",
            "상자는 7개입니다", "상자는 다섯 개다", "한 행을 가로로 읽으면",
            "세 행은 농가·지도컨설팅·정책거버넌스이고, 「과거 역할」 열은",
            "부제가 「—」인 두 편은 부제를 두지 않는 편이지 빠뜨린 것이 아니다",
            "이 절은 먼저 정의를 보고", "(「세대론을 신중히 읽기」 항에서 다시 다룬다)",
            "다음 절에서 그 구조를 살펴본다."]
V36_NOT = ["표 3.1-1과 같다", "왼쪽 다리", "다음 작기에 반영한다.", "관수량은 열에 따라 다르다",
           "수확물을 상자에 담는다", "왼쪽에 있는 필지부터 물을 준다", "행은 순서대로 읽는다"]


def test_v35_selftest():
    for s in V35_MUST:
        assert _t("V35", s + "\n") >= 1, s
    for s in V35_NOT:
        assert _t("V35", s + "\n") == 0, s


def test_v36_selftest():
    for s in V36_MUST:
        assert _t("V36", s + "\n") >= 1, s
    for s in V36_NOT:
        assert _t("V36", s + "\n") == 0, s


# ── V41 서수 나열 · V41W 넓힘 (원본 selftest) ──

def test_v41_selftest():
    assert _t("V41", "첫째, 관리를 본다. 둘째, 근거를 밝힌다. 셋째, 경계를 정한다.\n") == 1
    for s in ["1. **관리를 본다** — 첫째, 둘째, 셋째가 들어 있어도 목록이다.", "첫째, 하나. 둘째, 둘.",
              "| 첫째, 둘째, 셋째, | 표 칸 |", "첫째로 보고 둘째로 정한다 셋째로 기록한다"]:
        assert _t("V41", s + "\n") == 0, s


def test_v41w_selftest():
    for s, want in [("## 1. 가\n\n첫째 축은 시간이다.\n\n둘째 축은 공간이다.\n", 1),
                    ("## 1. 가\n\n생물적 위협의 첫째 유형은 병해다.\n\n둘째 유형은 해충이다.\n", 1),
                    ("## 1. 가\n\n첫째, 가.\n\n둘째, 나.\n\n셋째, 다.\n", 1),
                    ("## 1. 가\n\n첫째 축은 시간이다.\n\n## 2. 나\n\n둘째 축은 공간이다.\n", 0),
                    ("## 1. 가\n\n첫째, 가. 둘째, 나. 셋째, 다.\n", 0),
                    ("## 1. 가\n\n1. 첫째 축은 시간\n2. 둘째 축은 공간\n", 0),
                    ("## 1. 가\n\n첫째 해에는 심는다. 둘째 해에는 거둔다.\n", 0)]:
        assert _t("V41W", s) == want, s


def test_v41w_skips_index():
    s = "## 1. 가\n\n첫째 축은 시간이다.\n\n둘째 축은 공간이다.\n"
    assert _t("V41W", s, name="제1부/INDEX.md") == 0


# ── V43 문서 주어 결손 · V50 겹친 말 (원본 selftest) ──

def test_v43_selftest():
    for s in ["국내 기준은 이 문서가 확보하지 못했다", "이 문서는 확보하지 못했다",
              "이 가이드는 국내 사례를 찾지 못했다"]:
        assert _t("V43", s + "\n") == 1, s
    for s in ["국내 기준은 아직 확인되지 않았다", "농가가 자료를 확보하지 못했다",
              "| 이 문서는 확보하지 못했다 |"]:
        assert _t("V43", s + "\n") == 0, s


def test_v50_selftest():
    for s, want in [("조건이 다른 다른 연구의", 1), ("선후행 선후행 제약과 자원 용량 자원 용량 제약", 2),
                    ("농진청 농진청 시범지구", 1), ("기준이 있어야 표준이 표준이 된다", 0),
                    ("다른 연구와 다른 결과", 0), ("하나 둘 셋", 0), ("모델 불확실성 모델 불확실성 성숙", 1)]:
        assert _t("V50", s + "\n") == want, s
    assert _t("V50", "```\n다른 다른\n```\n") == 0  # 펜스 안은 보지 않는다
    assert _t("V50", "| 다른 다른 연구 |\n") == 1  # 원본: 표 칸도 본다


# ── V53 그림 구성 설명 · V54 안내·제목 되풀이 · V56 자기 선언 · V69 표 읽어 주기 ──

def test_v53_selftest_and_caption_scope():
    for s in ["위에서 아래로 네 부가 이어지고", "12장 상자에는 표준 운영 절차가", "제4부 아래에서 점선으로 이어진다"]:
        assert se.LAYOUT_WORDS.search(s), s
    for s in ["잎을 세어 평균을 낸다", "가로축은 파종 후 일수다"]:
        assert not se.LAYOUT_WORDS.search(s), s
    assert _t("V53", "**그림 1.1-1.** 흐름\n\n위에서 아래로 네 부가 이어진다.\n") == 1
    assert _t("V53", "그림 1.1-1. 흐름\n\n상자에는 절차가 있다.\n") == 1  # 굵게 없는 정본 꼴
    assert _t("V53", "**표 1.1-1.** 흐름\n\n위에서 아래로 네 부가 이어진다.\n") == 0
    assert _t("V53", "위에서 아래로 네 부가 이어진다.\n") == 0


def test_v54_selftest_overview_and_caption_call():
    s = "경계와 그것을 다루는 편은 0.2절에 있다.\n"
    assert _t("V54", s, name="개요/0.1. 가.md") == 1
    assert _t("V54", s, name="제1부/1.1. 가.md") == 0  # 안내 문장은 개요에서만
    assert _t("V54", "이 값은 12.3절의 기준온도를 쓴다.\n", name="개요/0.1. 가.md") == 0
    cap = ("**표 0.2-2.** 이 문서가 다른 편에 넘기는 일과 그 근거\n\n"
           "이 문서가 다른 편에 넘기는 일과 그 근거는 표 0.2-2와 같다.\n")
    assert _t("V54", cap) == 1
    m = se.CAPTION_CALL.match("이 문서가 다른 편에 넘기는 일과 그 근거는 표 0.2-2와 같다.")
    assert m and se.caption_overlap(m.group("subj"), "이 문서가 다른 편에 넘기는 일과 그 근거") >= 0.5


def test_v54_overview_prefixes_config():
    s = "경계와 그것을 다루는 편은 0.2절에 있다.\n"
    assert _t("V54", s, name="0_개요.md") == 0
    assert _t("V54", s, name="0_개요.md", extra={"prose": {"overview_prefixes": ["0_", "개요/"]}}) == 1


def test_v54_guide_words_config():
    s = "자세한 값은 방제편에 있다.\n"
    assert _t("V54", s, name="개요/0.1. 가.md") == 0
    assert _t("V54", s, name="개요/0.1. 가.md", extra={"prose": {"guide_words": [r"\S+편"]}}) == 1


def test_v56_selftest():
    for s in ["그것을 그 위에 둔 것이 이 문서의 정식화다", "이 문서의 독자는 농가다", "독자는 선도농가, 지도사 셋이다"]:
        assert _t("V56", s + "\n") == 1, s
    assert _t("V56", "이 문서는 농가를 대상으로 작성되었다\n") == 0
    assert _t("V56", "## 이 문서의 독자는 농가다\n") == 0  # 표제는 보지 않는다


V69_MUST = ["표 6.1-1에서 사용 시점이 「작기 전 기간」인 항목은 둘뿐이다",
            "기상재해편은 첫째 항목을 '폐루프의 단계'로 적고",
            "표 2.1-1의 마지막 열(주로 걸리는 국면)을 세어 보면", "표 10.1-2에서 형태 열이 인계인 네 행을 골라",
            "전달 내용 열을 위에서부터 읽으면", "표 18.2-1의 셋째 열이 이미 그 문제를 드러낸다",
            "표 10.2-1의 등급 칸을 순서 코드로"]
V69_NOT = ["표 8.1.L1-2에서 보듯 DSSAT는 모듈 분화로", "방법론 표준 열 편은 모두", "표 12.1-1의 열 편 가운데",
           "관수를 실행하는 날", "처방은 이행 기록과 함께(표 9.1-2) 남긴다",
           "여덟 항목이 일곱 단계에 나뉘어 채워진다(표 8.1-1)"]


def test_v69_selftest():
    for s in V69_MUST:
        assert _t("V69", s + "\n") >= 1, s
    for s in V69_NOT:
        assert _t("V69", s + "\n") == 0, s
    assert _t("V69", "| 표 6.1-1에서 사용 시점 열을 본다 |\n") == 0  # 표 줄은 보지 않는다


def test_v69_roman_caption_number():
    s = "표 II.6-1의 마지막 열(주로 걸리는 국면)을 세어 보면\n"
    assert _t("V69", s) == 0  # 아라비아 번호 꼴은 원본 그대로
    assert _t("V69", s, numbering={"section": "roman"}) == 1


# ── V76 띄어쓰기 (원본 selftest_new) ──

V76_MUST = ["측정할수 있다", "볼수없다", "측정할 수있다", "어쩔 수 밖에 없다", "그 동안 쌓인", "그 때 물을 준다",
            "이 때 기준은", "그 중 하나", "그 다음 단계", "관수할때 본다", "확인할것이다", "측정하는것이 좋다",
            "쓰지않는다", "하지못한다", "기록해야한다", "쓰게되었다", "제 3장에서", "3월 부터 5월 까지",
            "밭 에서 잰다", "값은 커녕", "수 백 건", "하나 뿐이다", "여러가지 값"]
V76_NOT = ["측정할 수 있다", "수없이 많다", "수밖에 없다", "그동안", "그 때문에", "이 때문에", "그 중요성은",
           "관수할 때", "물때를 맞춘다", "날것으로 먹는다", "들것에 싣는다", "측정할수록 정확하다",
           "하지 않는다", "해야 한다", "제3장", "3월부터 5월까지", "한가지로 본다", "둘뿐이다", "수학",
           "`할수 있다`", "[링크](할수있다.md)", "할 뿐 아니라", "일 뿐이다", "목적함수 밖에 있다",
           "못지않다", "머지않아", "바라 마지않는다", "담아 둘 뿐이다"]


def test_v76_selftest():
    for s in V76_MUST:
        assert _t("V76", s + "\n") >= 1, s
    for s in V76_NOT:
        assert _t("V76", s + "\n") == 0, s
    assert _t("V76", "```\n측정할수 있다\n```\n") == 0
    assert _t("V76", "측정할수 있다\n", name="INDEX.md") == 0


# ── V81 굵은 글씨 (원본 selftest_new2) ──

_V81_T = {
    "a.md": "## 1. 가\n\n**생육 예찰**은 지금을 본다. 다시 **생육 예찰**을 쓴다.\n\n- **입력** — 값\n- 출력 — 값\n\n"
            "| 머리 | **굵은 머리** |\n|---|---|\n| 칸 | **굵은 칸** |\n\n**표 1.1-1.** 제목 **굵음**\n\n"
            "## **굵은 표제**\n\n값은 **12.5%** 이다.\n\n"
            "<div class=\"quick-summary qs-goalbox\"><strong>목표</strong></div>\n\n## 2. 결론\n\n- **답** 이다\n",
    "c.md": "## 3. 결론\n\n- 답이다.\n\n**인용 참고문헌 (3건).** REF-1\n",
    "b.md": "- **가** — 1\n- **나** — 2\n\n1. **다** — 1\n2. **라** — 2\n\n"
            "**주장.** 첫머리 러닝헤드는 반복이 아니다. **주장.**\n\n**표 2.1-1.** 제목\n",
}


def test_v81_selftest_with_series_markers():
    out = REGISTRY["V81"](sample_model(tree=_V81_T, extra={"prose": {"markers": SERIES_MARKERS}}))
    got = " ".join(f.msg for f in out.findings)
    for w in ("반복 굵게 — 생육 예찰", "일부만 굵음(1/2)", "표 칸 안 굵게 — 굵은 칸", "캡션 안 굵게",
              "표제 안 굵게", "숫자만 굵게", "목표」 상자", "결론 안 굵게"):
        assert w in got, w
    assert not any(f.loc.startswith("c.md") for f in out.findings)
    for w in ("굵은 머리", "(2/2)", "주장"):
        assert w not in got, w


def test_v81_plugin_default_markers_off():
    """플러그인 기본 — 목표 상자·결론 표식은 꺼짐(시리즈 관례), 인용 참고문헌 줄은 렌더러 꼴이라 켜짐."""
    out = REGISTRY["V81"](sample_model(tree=_V81_T))
    got = " ".join(f.msg for f in out.findings)
    assert "목표」 상자" not in got and "결론 안 굵게" not in got
    assert "반복 굵게 — 생육 예찰" in got
    assert not any(f.loc.startswith("c.md") for f in out.findings)
