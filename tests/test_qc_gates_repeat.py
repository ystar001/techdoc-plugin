"""같은 틀 되풀이 게이트 V88 (v1.11-b Task 7 — 신규, F88).

원리로 정의한 게이트라 합성 fixture로만 시험한다(E17).
"""
import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.qc.engine import run_selftests
from techdoc_core.qc.gates.repeat import chapter_of, heading_head
from techdoc_core.qc.registry import REGISTRY, sample_model


def _frame(head, n, sep=" — ", level="##"):
    return "".join(f"{level} {i}. {head}{sep}항목 {i}\n\n본문.\n\n" for i in range(1, n + 1))


def _f(tree, **kw):
    return REGISTRY["V88"](sample_model(tree=tree, **kw)).findings


def test_v88_registered_with_samples_and_spec():
    assert len(REGISTRY["V88"].samples) >= 2
    assert run_selftests({"V88": REGISTRY["V88"]}) == []
    spec = load_gate_specs([("core", core_bundle_dir())])["V88"]
    assert spec.layer == "본체" and spec.level == "경고"


def test_v88_counts_heads_over_three():
    assert _f({"3장/3.1. 가.md": _frame("무엇을 정하나", 3)}) == []
    out = _f({"3장/3.1. 가.md": _frame("무엇을 정하나", 5)})
    assert [f.loc for f in out] == ["3장/3.1. 가.md:13", "3장/3.1. 가.md:17"]
    assert "무엇을 정하나" in out[0].msg


def test_v88_heads_across_files_in_same_chapter():
    tree = {"3장/3.1. 가.md": _frame("어떻게 확인", 2), "3장/3.2. 나.md": _frame("어떻게 확인", 2, sep=": ")}
    out = _f(tree)
    assert [f.loc.split(":")[0] for f in out] == ["3장/3.2. 나.md"]


def test_v88_heads_without_separator_counted():
    text = "".join(f"## {i}. 한계와 요구\n\n본문.\n\n" for i in range(1, 5))
    assert len(_f({"3장/a.md": text})) == 1
    # 머리가 다르면 세지 않는다
    text = "".join(f"## {i}. 한계 {i}\n\n본문.\n\n" for i in range(1, 6))
    assert _f({"3장/a.md": text}) == []


def test_v88_allowlist():
    tree = {"3장/a.md": _frame("사례", 6)}
    assert len(_f(tree)) == 3
    assert _f(tree, extra={"repeat": {"allow_heads": ["사례"]}}) == []


def test_v88_per_chapter_not_global():
    tree = {f"{c}장/a.md": _frame("무엇을 정하나", 3) for c in (1, 2, 3)}
    assert _f(tree) == []
    # 폴더가 없는 원고는 절 파일 이름의 장 번호로 묶는다
    flat = {"1.1. 가.md": _frame("틀", 2), "1.2. 나.md": _frame("틀", 2), "2.1. 다.md": _frame("틀", 3)}
    assert len(_f(flat)) == 1


def test_v88_level_four_and_fenced_headings_ignored():
    text = _frame("틀", 3) + "#### 틀 — 넷\n\n```\n## 틀 — 다섯\n```\n"
    assert _f({"3장/a.md": text}) == []


def test_v88_max_repeats_config():
    tree = {"3장/a.md": _frame("틀", 3)}
    assert len(_f(tree, extra={"repeat": {"max_repeats": 2}})) == 1


def test_heading_head_strips_number_marks_anchor():
    assert heading_head("3.2.1 **무엇을 정하나** — 범위 {#x}") == "무엇을 정하나"
    assert heading_head("II.6.13 무엇을 정하나: 범위", "roman") == "무엇을 정하나"
    assert heading_head("2.A.7. 사례", "letter_middle") == "사례"
    assert heading_head("(1) 배경") == "배경"
    assert heading_head("3D 모델링") == "3D 모델링"


def test_chapter_of():
    assert chapter_of("제1부/제2장_노지/2.1. 정의.md") == "제1부/제2장_노지"
    assert chapter_of("2.1. 정의.md") == "장 2"
    assert chapter_of("II.6. 정의.md", "roman") == "장 II"
    assert chapter_of("INDEX.md") == "INDEX.md"
