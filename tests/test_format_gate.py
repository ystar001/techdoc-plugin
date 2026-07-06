"""format_gate 서식 게이트 단위 테스트 (순수 함수)."""

from scripts import format_gate


def test_analyze_lists_counts_4multiple_and_flatten_risk():
    text = "- top\n    - four\n        - eight\n  - two\n   - three\n     - five"
    indent4, bad = format_gate.analyze_lists(text)
    assert indent4 == 2   # 4칸·8칸
    assert bad == 3       # 2·3·5칸


def test_analyze_lists_ignores_toplevel_and_nonlist():
    assert format_gate.analyze_lists("- a\nplain\n\n- b") == (0, 0)


def test_count_nonbullet_indent_flags_prose_not_bullets():
    text = "  설명을 욱여넣음\n  - 정상 불릿\n    네칸\n   세칸 텍스트"
    assert format_gate.count_nonbullet_indent(text) == 2  # 2칸 산문 + 3칸 산문


def test_count_inline_hierarchy_roman_and_alpha():
    text = "방법은 (i) 첫째 (ii) 둘째이며 (a-1) 세부와 (a-2) 추가가 있다."
    assert format_gate.count_inline_hierarchy(text) == 4


def test_count_inline_hierarchy_ignores_normal_parens():
    assert format_gate.count_inline_hierarchy("도입(2020년)에 (z) 항목") == 0


def test_count_top_plain_label_line_and_sentence_start():
    text = "(a) 분류 하나.\n결과는 (b) 둘째다."
    assert format_gate.count_top_plain(text) == 2


def test_count_redundant_summary():
    assert format_gate.count_redundant_summary("종합하면 X. 정리하면 Y. 종합적으로 Z.") == 3


def test_count_control_chars_flags_bel_bs_vt_ff_cr_only():
    text = "정상\t탭\n개행 \x0c FF \x07 BEL \x08 BS \x0b VT \x0d CR"
    assert format_gate.count_control_chars(text) == 5  # 탭·개행 제외


def test_count_control_chars_clean_zero():
    assert format_gate.count_control_chars("깨끗한 본문\t표\n다음 줄") == 0


def test_count_mermaid_label_risk_detects_unquoted_special():
    block = (
        "```mermaid\nflowchart TD\n"
        "subgraph 사과·감귤\n"
        "A -->|TAW=1000(θFC-θWP)Zr| B\n"
        "```"
    )
    # subgraph 특수문자 미인용 1 + 엣지 라벨 괄호 미인용 1
    assert format_gate.count_mermaid_label_risk(block) == 2


def test_count_mermaid_label_risk_quoted_and_xychart_and_literal_nl():
    safe = (
        '```mermaid\nflowchart TD\nsubgraph id["사과·감귤"]\n'
        'A -->|"라벨(설명)"| B\n```'
    )
    assert format_gate.count_mermaid_label_risk(safe) == 0
    risky = '```mermaid\nxychart-beta\nx-axis [기초선, 2026목표]\ntitle line\\n다음\n```'
    # 숫자머리 토큰 2026목표 1 + 리터럴 \n 1
    assert format_gate.count_mermaid_label_risk(risky) == 2


def test_count_mermaid_label_risk_ignores_non_mermaid_text():
    assert format_gate.count_mermaid_label_risk("본문에 subgraph 사과·감귤 언급") == 0


def test_count_inline_enumeration_flags_prose_not_bullets():
    text = "핵심은 세 가지다. 첫째, A이다. 둘째, B이다. 셋째, C이다."
    assert format_gate.count_inline_enumeration(text) == 1


def test_count_inline_enumeration_ignores_bullet_list():
    text = "- 첫째, A\n- 둘째, B"
    assert format_gate.count_inline_enumeration(text) == 0


def test_list_ratio_by_section_over_half_only():
    sections = {
        "sec1": "- a\n- b\n- c\n서술 한 줄",          # 3/4 = 75%
        "sec2": "- a\n서술1\n서술2\n서술3",            # 1/4 = 25%
    }
    out = format_gate.list_ratio_by_section(sections)
    assert out == {"sec1": 75}


def test_refs_extracts_ids():
    assert format_gate.refs("근거 [REF-001] 및 [REF-1234] 참조") == {"REF-001", "REF-1234"}


def test_nums_excludes_ref_numbers_and_keeps_decimals():
    # REF-001 의 001 은 제외, 1,200 과 3.5 는 단일 토큰
    assert format_gate.nums("[REF-001] 수확량 1,200kg 증가 3.5%") == {"1,200", "3.5"}


def test_render_nesting_returns_none_when_markdown_absent(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "markdown":
            raise ImportError("no markdown")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert format_gate.render_nesting({"sec1": "- a\n    - b"}) is None


DIRTY = {
    "sec1": "방법은 (i) 첫째 (ii) 둘째.\n- a\n- b\n- c\n서술",
    "sec2": "종합하면 핵심은 두 축이다.",
}
CLEAN = {"sec1": "본 절은 정의를 서술한다. 근거가 명확하다."}


def test_measure_format_clean_has_no_issues():
    r = format_gate.measure_format(CLEAN)
    assert r["issues"] == []
    assert r["metrics"]["inline_hierarchy"] == 0
    assert r["metrics"]["ref_loss"] is None


def test_measure_format_dirty_warns_not_fail_by_default():
    r = format_gate.measure_format(DIRTY)
    sev = {i["metric"]: i["severity"] for i in r["issues"]}
    assert sev["inline_hierarchy"] == "WARNING"
    assert sev["high_list_ratio"] == "WARNING"
    assert sev["redundant_summary"] == "WARNING"
    assert all(i["severity"] != "FAIL" for i in r["issues"])


def test_measure_format_strict_promotes_structural_to_fail():
    r = format_gate.measure_format(DIRTY, strict=True)
    sev = {i["metric"]: i["severity"] for i in r["issues"]}
    assert sev["inline_hierarchy"] == "FAIL"        # 구조 결함 승격
    assert sev["redundant_summary"] == "WARNING"    # 비구조는 WARN 유지
    assert sev["high_list_ratio"] == "WARNING"


def test_measure_format_baseline_regression():
    base = {"sec1": "근거 [REF-001] [REF-002]. 수확 1,200kg." + "긴내용" * 200}
    cur = {"sec1": "근거 [REF-001]."}  # REF-002 손실 + 분량 급감
    r = format_gate.measure_format(cur, baseline=base)
    assert r["metrics"]["ref_loss"] == 1
    assert r["metrics"]["length_delta"] < -0.15
    metrics_emitted = {i["metric"] for i in r["issues"]}
    assert "ref_loss" in metrics_emitted and "length_delta" in metrics_emitted


def test_measure_format_baseline_none_keeps_regression_null():
    r = format_gate.measure_format(CLEAN, baseline=None)
    assert r["metrics"]["ref_loss"] is None
    assert r["metrics"]["num_token_loss"] is None
    assert r["metrics"]["length_delta"] is None


def test_measure_format_new_metrics_present_and_warn():
    sections = {
        "sec1": "본문 \x0c 제어문자.\n\n핵심은 셋이다. 첫째, A. 둘째, B. 셋째, C.",
        "sec2": "```mermaid\nflowchart TD\nsubgraph 사과·감귤\nend\n```",
    }
    r = format_gate.measure_format(sections)
    m = r["metrics"]
    assert m["control_chars"] == 1
    assert m["inline_enumeration"] == 1
    assert m["mermaid_label_risk"] == 1
    sev = {i["metric"]: i["severity"] for i in r["issues"]}
    assert sev["control_chars"] == "WARNING"
    assert sev["inline_enumeration"] == "WARNING"
    assert sev["mermaid_label_risk"] == "WARNING"


def test_measure_format_strict_promotes_control_chars():
    r = format_gate.measure_format({"sec1": "본문 \x07 신호"}, strict=True)
    sev = {i["metric"]: i["severity"] for i in r["issues"]}
    assert sev["control_chars"] == "FAIL"


def test_render_nesting_fenced_code_not_counted_as_nesting():
    # 코드블록 안 들여쓴 리스트 유사 텍스트가 중첩으로 오계수되지 않아야 함(F37).
    import importlib.util

    if importlib.util.find_spec("markdown") is None:
        return
    sections = {"sec1": "- top\n\n```text\n    - looks like nested\n```"}
    out = format_gate.render_nesting(sections)
    assert out == {"sec1": 0}
