"""webbook_md2html 테스트 (v1.9.0 워크스트림 A·B — F52·F38·F48).

md → HTML 순수 변환. 수식($$/$) 보호(F38)·fenced mermaid 보호(F48)·REF 링크화.
"""
from techdoc_core.renderers.webbook_md2html import md_to_html


def test_table_and_list_render():
    """A1 — 표·리스트가 HTML로 렌더."""
    html, _toc = md_to_html("| a | b |\n|---|---|\n| 1 | 2 |\n\n- x\n- y")
    assert "<table" in html
    assert "<li>x</li>" in html


def test_inline_math_subscripts_preserved():
    """F38 — 인라인 수식 $V_{s,max}$의 밑줄이 emphasis로 잠식되지 않음."""
    html, _ = md_to_html("공식 $V_{s,max} = a_{i}$ 이다.")
    assert "V_{s,max}" in html
    assert "a_{i}" in html
    assert "<em>" not in html  # 밑줄이 <em>으로 변환되면 실패


def test_display_math_preserved():
    """F38 — 디스플레이 수식 $$…$$ 보존."""
    html, _ = md_to_html("식은 다음과 같다.\n\n$$ E = m c^2 $$\n")
    assert "$$" in html and "m c^2" in html


def test_fenced_mermaid_to_pre_escaped():
    """F48 — fenced ```mermaid → <pre class=mermaid>, 내용 HTML 이스케이프(<br/> 보존)."""
    html, _ = md_to_html('```mermaid\ngraph TD\nA["라벨<br/>줄"]-->B\n```')
    assert '<pre class="mermaid">' in html
    assert "&lt;br/&gt;" in html  # textContent용 이스케이프


def test_nested_list_two_levels():
    """F26 — 4칸 들여쓰기 2단 중첩 리스트가 중첩 <ul>로 렌더."""
    html, _ = md_to_html("- 상위 A\n    - 하위 A1\n    - 하위 A2\n- 상위 B")
    assert html.count("<ul>") >= 2
    assert "하위 A1" in html


def test_refs_linkified():
    """REF 토큰이 참고문헌 앵커로 링크화."""
    html, _ = md_to_html("근거가 있다 [REF-0004].", refs_href="../참고문헌/index.html")
    assert 'data-ref="REF-0004"' in html
    assert 'href="../참고문헌/index.html#REF-0004"' in html


def test_h2_toc_extracted():
    """H2 헤딩이 페이지 TOC로 추출."""
    _html, toc = md_to_html("## 첫 절\n내용\n\n## 둘째 절\n내용")
    names = [name for _id, name in toc]
    assert "첫 절" in names and "둘째 절" in names
