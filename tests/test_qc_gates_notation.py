"""용어·표기·기타 게이트 11종 (v1.11-b Task 5 — 시리즈 check_v2·prose_gates·math_hangul 이식, F85).

V22·V37·V42·V46·V47·V48·V49·V51·V64·V7·V14. 원본 자기검사(selftest) 표본이 있는 게이트
(V37·V42·V46·V47·V48·V49·V51·V64)는 그 표본을 옮겼다.
"""
import json

import pytest

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.qc import math_hangul
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.config import default_config, load_config
from techdoc_core.qc.engine import run_selftests
from techdoc_core.qc.gates import notation as no
from techdoc_core.qc.registry import REGISTRY, sample_model

GATES = ["V22", "V37", "V42", "V46", "V47", "V48", "V49", "V51", "V64", "V7", "V14"]
# 시리즈 관례 값 — 회귀 설정(make_configs)이 넣는 것과 같은 값
SERIES_TERMS = {"abbr_rule_sentence": "장마다 처음 나오는 곳에서"}


def _n(gid, model):
    return len(REGISTRY[gid](model).findings)


def _t(gid, text, name="a.md", **kw):
    return _n(gid, sample_model(tree={name: text}, **kw))


def _card(body, title="", **extra):
    return {"sections": {"s1": {"title": title, "body": body}}, **extra}


def test_all_notation_gates_registered_with_samples():
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
    """렌더가 깨지는 표기 결함은 막음, 문체·글꼴 선호(V42·V46·V47)는 경고. V7은 면제 불가."""
    specs = load_gate_specs([("core", core_bundle_dir())])
    for g in ("V22", "V37", "V48", "V49", "V51", "V64", "V7", "V14"):
        assert specs[g].level == "막음", g
    for g in ("V42", "V46", "V47"):
        assert specs[g].level == "경고", g
    assert specs["V7"].exemptable is False
    assert specs["V64"].layer == "문서종류" and specs["V14"].layer == "문서종류"


# ── V22 콜아웃 들여쓰기 ──

def test_v22_callout_indent():
    ok = _card('!!! note "가"\n\n    상자 안 본문이다.')
    two = _card('!!! note "가"\n  두 칸 본문이다.')
    out = _card('!!! note "가"\n밖으로 나간 본문이다.')
    empty = _card("본문이다.\n\n!!! warning\n\n")
    assert _n("V22", sample_model(cards={"1.1": ok})) == 0
    r = REGISTRY["V22"](sample_model(cards={"1.1": two, "1.2": out, "1.3": empty}))
    assert len(r.findings) == 3 and r.targets_read == 3
    assert r.findings[0].loc.startswith("1.1|s1:")
    assert "2칸" in r.findings[0].msg and "상자 밖" in r.findings[1].msg
    assert "본문 없음" in r.findings[2].msg


def test_v22_zero_targets_without_callout():
    r = REGISTRY["V22"](sample_model(cards={"1.1": _card("본문이다.")}))
    assert r.targets_read == 0 and not r.findings


# ── V37 수식 손상 (원본 selftest 표본) ──

@pytest.mark.parametrize("s", ["$$\\1 = f\\1(Y)$$", "$\\1_{\\1{scale}}$"])
def test_v37_must(s):
    assert _t("V37", s + "\n") == 1


@pytest.mark.parametrize("s", ["$\\pi = f(Y)$", "$x_1 = 2$", "$10\\%$"])
def test_v37_must_not(s):
    assert _t("V37", s + "\n") == 0


def test_v37_sees_fence_and_math_lines():
    # 원본은 원문 전체를 본다 — $$ 줄·펜스 안도
    assert _t("V37", "```\n$\\1 = x$\n```\n") == 1


# ── V42 사적 기호 (원본 selftest) ──

@pytest.mark.parametrize("s", ["【분기】는 도입 주체에서 나타난다.", "★ 눈에 띄는 값",
                               "⚠ 이 결과는 배에서 반대다."])
def test_v42_must(s):
    assert _t("V42", s + "\n") == 1


@pytest.mark.parametrize("s", ["| 중요도 | ★★ |", "「분기」라는 말", "별(*)표"])
def test_v42_must_not(s):
    assert _t("V42", s + "\n") == 0


def test_v42_skips_fence():
    assert _t("V42", "```\n★ 값\n```\n") == 0


# ── V46·V47·V49·V51 (원본 selftest) ──

@pytest.mark.parametrize("s,want", [("값은 `미판정`이다", 1), ("| `(자료 보완 필요)` |", 1),
                                    ("필드 `measured` 와 `quality_flag`", 0), ("`req·opt` 열", 0)])
def test_v46_selftest(s, want):
    assert _t("V46", s + "\n") == want


@pytest.mark.parametrize("s,want", [('*"부부가 함께 작업한다"* 고', 1), ("*기울인 말*", 1),
                                    ("*Pseudomonas syringae*", 0), ("**굵은 글씨**", 0),
                                    ("2 * 3 = 6, 4 * 가", 0)])
def test_v47_selftest(s, want):
    assert _t("V47", s + "\n") == want


@pytest.mark.parametrize("s,want", [("약 22억 US$는", 1), ("17.47 $/m³에서", 1), ("약 $420B", 0),
                                    ("US\\$로", 0), ("\\$/acre", 0), ("$x/y$", 0),
                                    ("코드 `US$는` 안", 0)])
def test_v49_selftest(s, want):
    assert _t("V49", s + "\n") == want


def test_v51_selftest():
    assert _t("V51", "[분석: 비교분석] 농업 FL\n") == 1
    assert _t("V51", "[REF-1] 분석: 비교\n") == 0


def test_line_gates_skip_fence():
    text = "```\n값은 `미판정`이다 *기울임* US$는 [분석: 가]\n```\n"
    for g in ("V46", "V47", "V49", "V51"):
        assert _t(g, text) == 0, g


# ── V48 수식 안 한글 (math_hangul 원본 selftest) ──

@pytest.mark.parametrize("src,want", [
    (r"$$\Delta Y_{\text{관측}} = \underbrace{\tau}_{\text{개입 효과}}$$",
     [("작은", "관측"), ("작은", "개입 효과")]),
    (r"$$ET_c = K_c \times ET_0 \quad \text{(작물 증발산)}$$", []),
    (r"$$영농 = a + b$$", [("맨", "영농")]),
    (r"$x_\text{책임}$", [("작은", "책임")]),
    (r"$\frac{\text{수량}}{\text{면적}}$", []),
    (r"가격 \$3 과 \$5", []),
    ("약 $420B 대비 약 1.8배, USDA $232.7B 와", []),
    ("$x_1 = 3$ 과 $2^{원}$", [("작은", "원")]),
    ("관측이 $R$은 크고 정확할수록($R$ 작을수록)", []),
    (r"$\mathrm{영농} + \operatorname{관리}$", [("맨", "영농"), ("맨", "관리")]),
])
def test_math_hangul_selftest(src, want):
    assert [(k, f) for _, k, f in math_hangul.scan_md(src)] == want


def test_v48_gate_counts_fragments_and_line():
    r = REGISTRY["V48"](sample_model(tree={"a.md": "가\n\n$$영농 = a_{관측}$$\n"}))
    assert len(r.findings) == 2 and r.findings[0].loc == "a.md:3"
    assert "명조" in r.findings[0].msg and "0.707" in r.findings[1].msg
    assert _t("V48", "```\n$$영농$$\n```\n") == 0


# ── V64 약어 장 첫 등장 풀이 (원본 selftest) ──

_V64_T = {
    "개요/0.4. 표기.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n**약어표**\n\n| 군 | 약어 | 풀이 |\n"
                       "|---|---|---|\n| 기관 | FAO | 국제연합 식량농업기구 |\n| | IoT | 사물인터넷 |",
    "제1부/제1장_가/1.1. 가.md": "국제연합 식량농업기구(FAO)가 정했다. 다시 FAO는.\n\n| 기술 | IoT |\n\n"
                              "주: IoT: 사물인터넷.",
    "제1부/제2장_나/2.1. 나.md": "FAO가 정했다. 센서(IoT·드론)를 쓴다.",
}


def _v64(tree, terms=SERIES_TERMS):
    return REGISTRY["V64"](sample_model(tree=tree, extra={"terms": terms} if terms else None))


def test_v64_selftest_chapter_first_use():
    msgs = [f.msg for f in _v64(_V64_T).findings]
    assert len(msgs) == 2 and any("FAO" in m for m in msgs) and any("IoT" in m for m in msgs)


def test_v64_off_without_rule_sentence():
    tree = {k: v.replace("장마다 처음 나오는 곳에서", "") for k, v in _V64_T.items()}
    r = _v64(tree)
    assert not r.findings and r.targets_read == 0


def test_v64_off_by_default_plugin():
    """플러그인 기본에는 규약 문장이 없다 — 시리즈 층 설정이 켠다."""
    r = _v64(_V64_T, terms=None)
    assert not r.findings and r.targets_read == 0


def test_v64_note_line_with_english_gloss():
    tree = {"개요/0.4. 표기.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n| 군 | 약어 | 풀이 |\n"
                               "|---|---|---|\n| 기관 | SOP | 표준 운영 절차 |",
            "제1부/제1장_가/1.1. 가.md": "| 절차 | SOP |\n\n주: SOP(Standard Operating Procedure): 표준 운영 절차."}
    assert not _v64(tree).findings


def test_v64_chemical_formula_not_abbr():
    assert not no.ABBR_TOKEN.search("NO₃⁻ 와 NH₄⁺") and no.ABBR_TOKEN.search("NDVI 와 SOP")


def test_v64_d_first_chapter_unit():
    tree = {"개요/0.4. 표기.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n| 약어 | 풀이 |\n|---|---|\n"
                               "| FAO | 국제연합 식량농업기구 |",
            "제1부_제1장. 가/1.1. 가.md": "국제연합 식량농업기구(FAO)가 정했다.",
            "제1부_제1장. 가/1.2. 나.md": "FAO가 다시 정했다.",
            "제1부_제2장. 나/2.1. 다.md": "FAO가 정했다."}
    assert [f.loc for f in _v64(tree).findings] == ["제1부_제2장. 나/2.1. 다.md:1"]


def test_v64_natural_order_in_chapter():
    """「5.10」이 「5.2」 뒤 — 첫 등장 자리가 글자 순으로 바뀌지 않는다."""
    tree = {"0.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n| FAO | 식량농업기구 |",
            "p/c/5.10. 가.md": "FAO가 다시 나온다.",
            "p/c/5.2. 나.md": "FAO가 처음 나온다."}
    assert [f.loc for f in _v64(tree).findings] == ["p/c/5.2. 나.md:1"]


def test_v64_roman_natural_order():
    """roman 번호 꼴 — 장 안 파일 순서를 로마 숫자 값으로(V → IX, 글자 순이면 IX가 앞)."""
    tree = {"0.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n| FAO | 식량농업기구 |",
            "p/c/IX.1. 가.md": "FAO가 나중에 나온다.",
            "p/c/V.1. 나.md": "FAO가 처음 나온다."}
    m = sample_model(tree=tree, extra={"terms": SERIES_TERMS}, numbering={"section": "roman"})
    assert [f.loc for f in REGISTRY["V64"](m).findings] == ["p/c/V.1. 나.md:1"]
    # arabic(기본)은 원본 그대로 글자 순
    assert [f.loc for f in _v64(tree).findings] == ["p/c/IX.1. 가.md:1"]


# ── V7 이미지 라이선스 ──

def test_v7_image_without_ledger_fails():
    m = sample_model(cards={"1.1": _card("그림 ![가](assets/images/a.png) 이다.")})
    r = REGISTRY["V7"](m)
    assert len(r.findings) == 1 and r.targets_read == 1
    assert r.findings[0].loc.startswith("1.1 이미지")


def test_v7_ledger_lists_image():
    m = sample_model(cards={"1.1": _card("![가](assets/images/a.png) ![나](b.png \"t\")")},
                     image_license="a.png\tCC-BY\n")
    r = REGISTRY["V7"](m)
    assert len(r.findings) == 1 and "b.png" in r.findings[0].msg and r.targets_read == 2


def test_v7_no_images_no_target():
    r = REGISTRY["V7"](sample_model(cards={"1.1": _card("본문이다.")}))
    assert r.targets_read == 0 and not r.findings


def test_v7_ledger_path_from_config(tmp_path):
    lic = tmp_path / "output" / "assets" / "images" / "LICENSE.tsv"
    lic.parent.mkdir(parents=True)
    lic.write_text("a.png\tCC-BY\n", encoding="utf-8")
    assert default_config(tmp_path).paths.image_license == lic
    model = build_model(tmp_path, default_config(tmp_path))
    assert model.image_license == "a.png\tCC-BY\n"
    (tmp_path / "techdoc.project.yaml").write_text(
        "paths:\n  image_license: x/LIC.tsv\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.paths.image_license == tmp_path / "x" / "LIC.tsv"
    assert build_model(tmp_path, cfg).image_license is None


# ── V14 요약·본문 일치 ──

def test_v14_summary_ghost_tokens():
    card = _card("본문은 NDVI 값을 쓴다.",
                 quick_summary={"summary": "NDVI와 EVI 지수로 12.5% 늘었다.", "one_sentence": ""})
    r = REGISTRY["V14"](sample_model(cards={"1.1": card}))
    # EVI · 12.5% 두 건(원본은 한 자리를 n건으로 센다)
    assert len(r.findings) == 2 and r.targets_read == 1
    assert r.findings[0].loc.startswith("1.1|-:")


def test_v14_goal_form_and_refs_stripped():
    card = _card("본문은 LAI를 쓴다.",
                 quick_summary={"goal": "LAI 값을 읽는다.",
                                "questions": ["3.2절의 GDD는?", "표 3.2-1의 값은?"]})
    r = REGISTRY["V14"](sample_model(cards={"1.1": card}))
    assert [f.msg for f in r.findings] == [r.findings[0].msg] and "GDD" in r.findings[0].msg


def test_v14_string_and_list_forms():
    assert _n("V14", sample_model(cards={"1.1": _card("값 2.5배", quick_summary="값 2.5배")})) == 0
    assert _n("V14", sample_model(cards={"1.1": _card("가", quick_summary=["SOFC 3.1"])})) == 2


def test_v14_keyword_names_not_ghosts():
    card = _card("본문이다.", quick_summary={"summary": "quick summary REF-001 http"})
    assert _n("V14", sample_model(cards={"1.1": card})) == 0


def test_v14_roman_section_refs_stripped():
    card = _card("본문이다.", quick_summary="II.6.3절에서 본다.")
    assert _n("V14", sample_model(cards={"II.6": card}, numbering={"section": "roman"})) == 0


def test_v14_json_card_roundtrip(tmp_path):
    cards = tmp_path / "output" / "cards"
    cards.mkdir(parents=True)
    (cards / "1.1_card.json").write_text(json.dumps(
        _card("본문", quick_summary="ABC 값"), ensure_ascii=False), encoding="utf-8")
    model = build_model(tmp_path, default_config(tmp_path))
    assert _n("V14", model) == 1
