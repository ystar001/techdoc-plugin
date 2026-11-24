"""집필 흔적 게이트 V87 (v1.11-b Task 6 — 신규, F87).

원리로 정의한 게이트라 합성 fixture로만 시험한다(E17). 꼴마다 위반·통과, 코드 안 무시, 허용 목록.
"""
import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.qc.engine import run_selftests
from techdoc_core.qc.registry import REGISTRY, sample_model


def _f(text, **kw):
    return REGISTRY["V87"](sample_model(tree={"a.md": text}, **kw)).findings


def _kinds(text, **kw):
    return [f.msg.split(":", 1)[0] for f in _f(text, **kw)]


def test_v87_registered_with_samples_and_spec():
    assert len(REGISTRY["V87"].samples) >= 2
    assert run_selftests({"V87": REGISTRY["V87"]}) == []
    spec = load_gate_specs([("core", core_bundle_dir())])["V87"]
    assert spec.layer == "본체" and spec.level == "경고"


# ── call_id ──
def test_v87_call_id_split_markers():
    assert _kinds("계산은 3.2.L2와 A-1.XL3에 있다.") == ["call_id", "call_id"]
    assert _kinds("별첨 D1.L2를 본다.") == ["call_id"]


def test_v87_call_id_roman_numbering():
    assert _kinds("자세한 내용은 II.6.L2에서.", numbering={"section": "roman"}) == ["call_id"]


def test_v87_call_id_pass():
    # 분할 표지 없는 절 번호, 붙지 않은 L2, 소문자 머리
    assert _f("3.2절과 별첨 A-1을 본다. L2 정규화와 v2.L1 표기.") == []


def test_v87_heading_anchor_link_target_ignored():
    text = "## 3.2 원리 {#3.2.L2}\n\n[원리](3.2.L2_card.json)를 본다.\n<a id=\"3.2.L2\"></a>\n"
    assert _f(text) == []


# ── filename ──
def test_v87_plugin_work_files():
    text = "값은 3.2_card.json과 writer_state.json, research_round_3.json, KeyRef/REF-001.md에 있다."
    assert _kinds(text) == ["filename"] * 4


def test_v87_filename_pass():
    assert _f("관측값은 CSV 파일로 내려받는다. config.json은 설정이다.") == []


def test_v87_extra_file_patterns():
    text = "params_4b.py를 고쳤다."
    assert _f(text) == []
    # v1.11-c: file_patterns는 allow와 같은 글롭 꼴, 정규식은 `re:` 접두
    assert _kinds(text, extra={"leak": {"file_patterns": ["*.py"]}}) == ["filename"]
    assert _kinds(text, extra={"leak": {"file_patterns": ["params_?b.py"]}}) == ["filename"]
    assert _kinds(text, extra={"leak": {"file_patterns": [r"re:\w+\.py"]}}) == ["filename"]
    assert _f(text, extra={"leak": {"file_patterns": ["*.txt"]}}) == []


def test_v87_allow_list():
    text = "reference_list.json의 구조를 설명한다. 3.2.L2도."
    assert len(_f(text)) == 2
    allow = {"leak": {"allow": ["reference_list.json", "*.L2"]}}
    assert _f(text, extra=allow) == []


# ── split · this_card ──
def test_v87_split_note():
    assert _kinds("다음 분할에서 사례를, 이전 분할에서 원리를 보았다.") == ["split", "split"]
    assert _f("시료를 분할해 다음 단계로 보낸다.") == []


def test_v87_this_card():
    assert _kinds("이 카드는 원리를 다룬다.") == ["this_card"]
    assert _f("모이 카드라는 이름. 이 절은 원리를 다룬다.") == []


# ── 코드 무시 · 원천 ──
def test_v87_fenced_and_inline_code_ignored():
    text = "```json\n{\"f\": \"writer_state.json\", \"id\": \"3.2.L2\"}\n```\n`이 카드` 와 ``3.2.L2``\n"
    assert _f(text) == []


def test_v87_html_comment_ignored():
    assert _f("<!-- 3.2.L2 writer_state.json\n다음 분할 -->\n본문.") == []


def test_v87_card_level_fields():
    card = {"sections": {"s1": {"title": "", "body": "본문"}},
            "scope_note": "이 카드는 원리만 본다.",
            "split_continuation_note": "다음 분할(3.2.L2)에서 이어진다."}
    out = REGISTRY["V87"](sample_model(cards={"3.2.L1": card})).findings
    assert sorted(f.msg.split(":", 1)[0] for f in out) == ["call_id", "split", "this_card"]
    assert all(f.loc.startswith("3.2.L1|") for f in out)


def test_v87_line_loc():
    out = _f("첫 줄.\n\n이 카드는 둘째.")
    assert [f.loc for f in out] == ["a.md:3"]
