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
