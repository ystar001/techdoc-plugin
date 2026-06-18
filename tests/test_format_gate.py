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
