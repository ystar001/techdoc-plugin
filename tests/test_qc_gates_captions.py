"""캡션·도표 게이트 12종 + F82 로마 숫자 캡션 (v1.11-b Task 4 — 시리즈 check_v2·prose_gates 이식, F85·F82).

V6·V12·V15·V17·V18(카드) · V40·V62·V63·V66·V73·V75·V80(산문). 원본 자기검사(selftest) 표본이 있는
게이트(V12·V40·V62·V63·V66·V73·V75·V80)는 그 표본을 옮겼다.
"""
import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.qc import numbering
from techdoc_core.qc.engine import run_qc, run_selftests
from techdoc_core.qc.gates import captions as ca
from techdoc_core.qc.registry import REGISTRY, sample_model

CARD_GATES = ["V6", "V12", "V15", "V17", "V18"]
TREE_GATES = ["V40", "V62", "V63", "V66", "V73", "V75", "V80"]
GATES = CARD_GATES + TREE_GATES
# 시리즈 관례 값 — 회귀 설정(make_configs)이 넣는 것과 같은 값
SERIES_CAPTION = {"standard_table_words": ["표준표", "임계값", "임계치", "파라미터", "기준값"]}
TABLE = "| 가 | 나 |\n|---|---|\n| 1 | 2 |"


def _n(gid, model):
    return len(REGISTRY[gid](model).findings)


def _c(gid, body, cid="1.1", **kw):
    return _n(gid, sample_model(cards={cid: {"sections": {"s1": {"title": "", "body": body}}}}, **kw))


def _t(gid, text, name="a.md", **kw):
    return _n(gid, sample_model(tree={name: text}, **kw))


def test_all_caption_gates_registered_with_samples():
    for g in GATES:
        assert g in REGISTRY, g
        assert len(REGISTRY[g].samples) >= 2, g
    assert run_selftests({g: REGISTRY[g] for g in GATES}) == []


def test_zero_targets_when_no_input():
    empty = sample_model()
    for g in GATES:
        out = REGISTRY[g](empty)
        assert out.targets_read == 0 and not out.findings, g


def test_specs_levels():
    """결함 게이트는 막음, 가독성·문체·관례 게이트는 경고(E18 11번), V80은 시범, V6은 면제 불가."""
    specs = load_gate_specs([("core", core_bundle_dir())])
    for g in ("V6", "V12", "V15", "V73", "V75"):
        assert specs[g].level == "막음", g
    for g in ("V17", "V18", "V40", "V62", "V63", "V66"):
        assert specs[g].level == "경고", g
    assert specs["V80"].level == "시범"
    assert specs["V6"].exemptable is False
    assert all(specs[g].exemptable for g in GATES if g != "V6")


# ── V6 캡션·본문 연계 ──

def test_v6_missing_caption_and_uncalled():
    assert _c("V6", TABLE) == 1                                            # 캡션 결손 1/1
    assert _c("V6", f"**표 1.1-1.** 값\n\n{TABLE}\n\n표 1.1-1은 값을 보인다.") == 0
    assert _c("V6", f"**표 1.1-1.** 값\n\n{TABLE}\n") == 1                 # 본문이 부르지 않는 도표
    assert _c("V6", f"**표 1.1-1.** {'가' * 91}\n\n{TABLE}\n\n표 1.1-1을 본다.") == 1  # 90자 초과


def test_v6_counts_each_missing_caption():
    """원본은 결손 수만큼 센다(fail += vis - caps)."""
    assert _c("V6", f"{TABLE}\n\n{TABLE.replace('가', '다')}\n\n```mermaid\nA-->B\n```") == 3


def test_v6_front_and_callout_exempt():
    assert _c("V6", TABLE, cid="0.1") == 0                                 # 앞부분은 번호 없는 제목
    assert _c("V6", "!!! 핵심\n\n    | 가 | 나 |\n    |---|---|\n    | 1 | 2 |\n") == 0  # 상자 안 표


def test_v6_not_exemptable():
    model = sample_model(cards={"1.1": {"sections": {"s1": {"title": "", "body": TABLE}}}},
                         exempt={"1.1": {"gates": ["V6"], "why": "시험"}})
    specs = load_gate_specs([("core", core_bundle_dir())])
    from techdoc_core.qc.config import default_config
    rep = run_qc(model, {"V6": specs["V6"]}, {"V6": REGISTRY["V6"]}, default_config(model.root))
    assert rep["results"][0]["count"] == 1 and not rep["exempted"]


# ── F82 로마 숫자 캡션 ──

def test_f82_roman_caption_recognized():
    """roman 번호 꼴이면 「**표 I.1-1 제목**」(번호 뒤 마침표 없는 꼴)도 캡션 — arabic은 원본처럼 결손."""
    body = f"**표 I.1-1 설계 단계별 입력**\n\n{TABLE}\n\n표 I.1-1은 단계별 입력을 보인다."
    assert _c("V6", body, cid="I.1", numbering={"section": "roman"}) == 0
    assert _c("V6", body, cid="I.1") == 1                                  # arabic — 원본과 같음
    dotted = f"**표 II.8-1.** 설계 단계\n\n{TABLE}\n\n표 II.8-1은 단계를 보인다."
    assert _c("V6", dotted, cid="II.8", numbering={"section": "roman"}) == 0
    assert _c("V6", dotted, cid="II.8") == 0                               # 원본도 캡션으로 본다
    plain = "그림 I.2-1 흐름\n\n```mermaid\nA-->B\n```\n\n그림 I.2-1처럼 흐른다."
    assert _c("V6", plain, cid="I.2", numbering={"section": "roman"}) == 0


def test_f82_caption_num_shared():
    """카드·산문 게이트의 캡션 번호 조각은 numbering 한 곳에서 — arabic은 원본 문자열 그대로."""
    from techdoc_core.qc import prose
    from techdoc_core.qc.gates import structure
    assert numbering.CAPTION_TOKEN == r"[\dA-Za-z][0-9A-Za-z.\-]*"
    assert prose.CAP_PLAIN == r"(?:그림|표|차트|사진|다이어그램)\s[\dA-Za-z][0-9A-Za-z.\-]*\.(?=\s|$)"
    assert structure.CAP_PLAIN_AHEAD == \
        r"(?=(?:그림|표|차트|사진|다이어그램)\s[\dA-Za-z][0-9A-Za-z.\-]*\.\s)"
    text = "**표 I.1-1 제목**\n표 IV.18-8은 크다.\n\"caption\": \"그림 III.16-1 범주\""
    assert numbering.normalize_captions(text, "arabic") == text
    got = numbering.normalize_captions(text, "roman")
    assert got.split("\n")[0] == "**표 I.1-1. 제목**"
    assert got.split("\n")[1] == "표 IV.18-8은 크다."                     # 산문 호출은 그대로
    assert got.split("\n")[2] == "\"caption\": \"그림 III.16-1. 범주\""


def test_f82_v2_roman_caption_defined():
    """V2도 같은 정규화 — roman 문서의 마침표 없는 캡션을 「정의 없음」으로 잡지 않는다."""
    card = {"sections": {"s1": {"title": "", "body": f"**표 I.1-1 제목**\n\n{TABLE}\n\n표 I.1-1은 크다."}}}
    assert _n("V2", sample_model(cards={"I.1": card}, numbering={"section": "roman"})) == 0


# ── V12 도표 번호 정합 (원본 selftest) ──

def _one(seq):
    return sum(n for n, _ in ca.fig_number_issues(seq, "t"))


def _grp(seq):
    return sum(n for n, _ in ca.split_group_issues(seq, "g"))


def test_v12_selftest_single_card():
    assert _one([("표", "1.2-1"), ("표", "1.2-2")]) == 0
    assert _one([("표", "1.2-1"), ("표", "1.2-3")]) == 1
    assert _one([("표", "1.2-2"), ("표", "1.2-1")]) >= 1
    assert _one([("그림", "1.2-1"), ("차트", "1.2-1")]) >= 1


def test_v12_selftest_split_group():
    cont = ([("표", f"4.4-{i}") for i in range(1, 6)] + [("그림", "4.4-1")]
            + [("표", "4.4-6"), ("표", "4.4-7")] + [("표", f"4.4-{i}") for i in range(8, 12)])
    assert _grp(cont) == 0
    own = [("표", "7.1.L1-1"), ("표", "7.1.L1-2"), ("표", "7.1.L2-1"), ("표", "7.1.L2-2")]
    assert _grp(own) == 0
    assert _grp([("표", "11.3.XL1-5"), ("표", "11.3.XL1-7"), ("표", "11.3.XL1-6")]) >= 1
    assert _grp([("그림", "7.1.L2-2"), ("그림", "7.1.L2-3"), ("그림", "7.1.L2-1")]) >= 1
    assert _grp([("표", "4.4-1"), ("표", "4.4-2"), ("표", "4.4-5")]) == 2
    assert _grp([("표", "4.4-1"), ("표", "4.4-3"), ("표", "4.4-2")]) >= 1


def test_v12_gate_counts_and_split_groups():
    assert _c("V12", "**표 1.1-1.** 가\n\n**표 1.1-3.** 나\n") == 1                  # 결번
    assert _c("V12", "**표 1.1-1.** 가\n\n**표 1.1-2.** 나\n") == 0
    # 분할 묶음은 첫 카드에서 한 번 — 이어 매긴 번호는 결번이 아니다
    cards = {"4.4.L1": {"sections": {"s": {"title": "", "body": "**표 4.4-1.** 가\n"}}},
             "4.4.L2": {"sections": {"s": {"title": "", "body": "**표 4.4-2.** 나\n"}}}}
    assert _n("V12", sample_model(cards=cards)) == 0
    cards["4.4.L2"]["sections"]["s"]["body"] = "**표 4.4-4.** 나\n"
    out = REGISTRY["V12"](sample_model(cards=cards))
    assert len(out.findings) == 2 and out.findings[0].loc.startswith("4.4.L1|-:")


def test_v12_chart_caption_in_sequence():
    body = '```chart\n{"caption": "그림 1.1-2. 둘째"}\n```\n\n**그림 1.1-1.** 첫째\n'
    assert _c("V12", body) == 1                                            # 등장 순서 역전


def test_v12_exempt_by_card_key():
    model = sample_model(cards={"1.1": {"sections": {"s": {"title": "", "body": "**표 1.1-2.** 가\n"}}}},
                         exempt={"1.1|-": {"gates": ["V12"], "why": "시험"}})
    specs = load_gate_specs([("core", core_bundle_dir())])
    from techdoc_core.qc.config import default_config
    rep = run_qc(model, {"V12": specs["V12"]}, {"V12": REGISTRY["V12"]}, default_config(model.root))
    assert rep["results"][0]["count"] == 0 and rep["exempted"] == {"V12": 1}


# ── V15 표 뒤 빈 줄 ──

def test_v15_table_swallows_paragraph():
    assert _c("V15", f"{TABLE}\n다음 문단이다.") == 1
    assert _c("V15", f"{TABLE}\n\n다음 문단이다.") == 0
    assert _c("V15", "```\n| a | b |\n코드다\n```") == 0                  # 펜스 안은 표가 아니다


# ── V17 캡션 규약 ──

def test_v17_caption_conventions():
    assert _c("V17", "**표 1.1-1** 값") == 1                               # 번호 뒤 마침표 없음
    assert _c("V17", "**표 1.1-1.** 값을 정리했다") == 1                  # 서술형
    assert _c("V17", "**표 1.1-1.** 무엇을 재나") == 1                    # 물음꼴
    assert _c("V17", "**표 1.1-1.** 값과 근거 [REF-001]") == 1            # 출처
    assert _c("V17", "표 1.1-1. 값 | 단위 | 비고") == 1                    # 머리행 삼킴
    assert _c("V17", "**표 1.1-1.** 관측 항목과 주기") == 0
    assert _c("V17", "표 1.1-1. 관측 항목과 주기") == 0


# ── V18 설명 문단의 가독성 ──

def test_v18_description_readability():
    long_para = "가" * 701 + "다."
    assert _c("V18", f"**그림 1.1-1.** 흐름\n\n{long_para}") == 1
    assert _c("V18", "**그림 1.1-1.** 흐름\n\n값은 **가**와 **나**와 **다**로 갈린다.") == 1
    assert _c("V18", "**그림 1.1-1.** 흐름\n\n값은 크다) 그래서 본다.") == 1
    assert _c("V18", "**그림 1.1-1.** 흐름\n\n값은 위에서 아래로 흐른다.") == 0
    # 표는 표를 건너뛰고 설명을 본다
    assert _c("V18", f"**표 1.1-1.** 값\n{TABLE}\n\n{long_para}") == 1


def test_v18_skip_table_titles_config():
    body = f"**표 0.1-1.** 판 이력\n{TABLE}\n\n{'가' * 701}다."
    assert _c("V18", body) == 0                                            # 기본 — 판 이력·개정 이력
    assert _c("V18", body, extra={"caption": {"skip_table_titles": ["개정 이력"]}}) == 1


# ── V40 근거 등급 열 (원본 selftest) ──

def test_v40_selftest():
    must = "**표 17.6-1.** 핵심 파라미터 표준표\n\n| 파라미터 | 값 | 단위 |\n|---|---|---|"
    nots = ["**표 6.1-2.** 마늘 관수 임계값의 근거 등급\n\n| 값 | 근거 등급 |\n|---|---|",
            "| 영역 | 기준 | 국내 노지 근거 |\n|---|---|---|\n\n**표 8.2-1.** 영역별 판단 기준과 핵심 파라미터",
            "**표 3.1-1.** 국내 현황\n\n| 항목 | 값 |"]
    ex = {"caption": SERIES_CAPTION}
    assert _t("V40", must, extra=ex) == 1
    for s in nots:
        assert _t("V40", s, extra=ex) == 0, s


def test_v40_off_without_series_words():
    must = "**표 17.6-1.** 핵심 파라미터 표준표\n\n| 파라미터 | 값 | 단위 |\n|---|---|---|"
    out = REGISTRY["V40"](sample_model(tree={"a.md": must}))
    assert out.targets_read == 0 and not out.findings


# ── V62 표의 참조 열 · V63 표 열 이름 (원본 selftest) ──

def test_v62_selftest_and_gate():
    assert ca.REF_HEAD.search("관련 절") and not ca.REF_HEAD.search("장 생육조사의 필요성")
    assert ca.ref_val_re("A-L").match("11.2 도입 성숙도") and not ca.ref_val_re("A-L").match("관측 계층")
    assert _t("V62", "| 항목 | 관련 절 |\n|---|---|\n| 가 | 3.2 |\n| 나 | 4.1 |") == 1
    assert _t("V62", "| 항목 | 관련 절 |\n|---|---|\n| 가 | 관측 |\n| 나 | 기록 |") == 0
    # 분담·분업·구성 표는 장 자체가 내용
    assert _t("V62", "**표 1.1-1.** 절 분담\n\n| 항목 | 관련 절 |\n|---|---|\n| 가 | 3.2 |") == 0


def test_v62_roman_section_values():
    t = "| 항목 | 관련 절 |\n|---|---|\n| 가 | II.6 |\n| 나 | III.2 |"
    assert _t("V62", t, numbering={"section": "roman"}) == 1
    assert _t("V62", t) == 0                                               # arabic — 원본과 같음


def test_v63_selftest():
    for t, w in (("무엇을 재나", 1), ("왜 필요한가", 1), ("담는 것", 1), ("주로 펼치는 사람과 때", 1),
                 ("하는 일", 1), ("내용", 0), ("주 사용자", 0), ("사용 시점", 0), ("측정 대상", 0),
                 ("무엇", 1), ("판정 기준", 0), ("역할", 0)):
        assert _t("V63", f"| {t} | 값 |\n|---|---|\n| 1 | 2 |") == w, t


# ── V66 자리 호출 (원본 selftest) ──

def test_v66_selftest():
    yes = ["아래 그림처럼 물은 근권을 지난다", "위의 표에서 보듯", "다음 표는 작목별 값이다", "앞 그림과 같이",
           "아래표에 정리했다", "이어지는 그림은 흐름을 보인다", "아래 도표 3.1-2에서"]
    no = ["다음 표준을 따른다", "아래 표토는 젖어 있다", "그림 3.1-1처럼", "표 2.2-1에서 보듯", "다음 작기에 반영한다",
          "앞 절에서 다룬 값", "위 표준 편이 정한다", "다음 그림자 효과", "아래로 흐른다"]
    for s in yes:
        assert ca.POS_REF.search(s), s
    for s in no:
        assert not ca.POS_REF.search(s), s


def test_v66_gate():
    assert _t("V66", "아래 그림처럼 흐른다.") == 1
    assert _t("V66", "흐름은 다음과 같다.\n\n```mermaid\nA-->B\n```") == 1
    assert _t("V66", "그림 3.1-1처럼 흐른다.") == 0
    assert _t("V66", "아래 그림처럼 흐른다.", name="INDEX.md") == 0         # 목차는 보지 않는다


# ── V73 mermaid 물결표 · V75 그래프 축 이름 (원본 selftest) ──

def test_v73_selftest_and_gate():
    assert len(ca.MER_TILDE.findall('A["투입비 −8~20%"] --> B["1~3일"]')) >= 2  # noqa: RUF001
    assert len(ca.MER_TILDE.findall("A ~~~ B")) < 2
    assert len(ca.MER_TILDE.findall('A["-8#126;20% +2#126;3"]')) >= 2
    assert len(ca.MER_TILDE.findall('A["-8∼20% +2∼3"]')) < 2  # noqa: RUF001
    assert _t("V73", '```mermaid\nA["8~20%"] --> B["1~3일"]\n```') == 1
    assert _t("V73", 'A["8~20%"] --> B["1~3일"]') == 0                    # mermaid 밖


def test_v75_selftest():
    for t, w in (('{"type":"bar","categories":["가"],"values":[1],"unit":"%"}', 1),
                 ('{"type":"line","x":[1,2],"series":{"a":[1,2]},"ylabel":"비율(%)"}', 1),
                 ('{"type":"paired_bar","categories":["가"],"series":{"a":[1]},"xlabel":"작물","ylabel":" "}', 1),
                 ('{"type":"bar","categories":["가"],"values":[1],"xlabel":"권역","ylabel":"손실률(%)"}', 0),
                 ('{"type":"radar","axes":["a","b","c"],"series":{"a":[1,2,3]}}', 0),
                 ('{"type":"heatmap","rows":["a"],"cols":["b"],"matrix":[[1]]}', 0),
                 ('{"type": "bar", 깨진 명세', 0)):
        assert bool(ca.chart_axis_missing(t)) == bool(w), t
        assert _t("V75", f"```chart\n{t}\n```") == w, t


def test_v75_plugin_chart_types_and_keys():
    """플러그인 generate_chart의 comparison·x_label/y_label도 본다. 시리즈 설정은 원본 집합·키로."""
    comp = '{"type":"comparison","x_label":"작물","y_label":"수량"}'
    assert _t("V75", f"```chart\n{comp}\n```") == 0
    assert _t("V75", '```chart\n{"type":"comparison"}\n```') == 1
    series = {"caption": {"chart_axis_types": ["bar"], "chart_axis_keys": {"x": ["xlabel"], "y": ["ylabel"]}}}
    assert _t("V75", '```chart\n{"type":"comparison"}\n```', extra=series) == 0
    assert _t("V75", '```chart\n{"type":"bar","x_label":"a","y_label":"b"}\n```', extra=series) == 1


# ── V80 그림 안 글 길이 (원본 selftest) ──

def test_v80_selftest_mermaid():
    long_k = "가" * 25
    for lines, want in [(['A["짧은 글<br/>둘째 줄"] --> B["다음"]'], 0),
                        ([f'A["{long_k}"]'], 1), ([f'A[{long_k}]'], 1), ([f'A -->|"{long_k}"| B'], 1),
                        ([f'A["{"가" * 20}<br/>{"나" * 20}"]'], 0), (['A["Soil moisture sensor network 40"]'], 0),
                        ([f'subgraph S ["{long_k}"]'], 1),
                        (['x-axis "가가가가가가가가가가가가가가가가가가가가가" [a, b]'], 1),
                        (['x-axis "월" ["1월", "2월"]'], 0),
                        (['classDef big fill:#fff,stroke:#000,font-size:14px'], 0),
                        ([f'%% {long_k}'], 0), ([f'A(("{long_k}"))'], 1)]:
        assert bool(ca.mermaid_text_issues(lines)) == bool(want), lines[0]


def test_v80_selftest_chart_and_gate():
    long_k = "가" * 25
    for raw, want in [('{"type":"bar","categories":["가"],"xlabel":"권역","ylabel":"손실률(%)"}', 0),
                      ('{"type":"bar","categories":["가"],"xlabel":"권역별 연평균 관개 효율 개선 폭과 그 변화의 범위",'
                       '"ylabel":"%"}', 1),
                      ('{"type":"bar","categories":["' + long_k + '"],"xlabel":"가","ylabel":"나"}', 1),
                      ('{"type":"line","x":[1,2],"xlabel":"월","ylabel":"mm"}', 0), ("깨진 명세", 0)]:
        assert bool(ca.chart_text_issues(raw)) == bool(want), raw
    out = REGISTRY["V80"](sample_model(tree={"a.md": f'```mermaid\nA["{long_k}"]\n```\n'}))
    assert len(out.findings) == 1 and out.findings[0].loc == "a.md:2" and out.targets_read == 1
