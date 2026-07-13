"""정형 사양 블록 테스트 (v1.9.0 워크스트림 F — F32).

함수 명세·상태벡터 스키마·파라미터 표준표를 구조화 JSON으로 담고,
markdown 렌더 + CSV/JSON 추출.
"""
from techdoc_core.formal_blocks import (
    param_table_to_csv,
    render_formal_blocks,
    render_function_spec,
    render_param_table,
)


def test_render_function_spec_table():
    spec = [{"name": "forecast", "signature": "forecast(crop, env) -> Record",
             "io": "crop,env → Record", "unit": "-", "range": "-", "default": "-",
             "source": "§19.4"}]
    md = render_function_spec(spec)
    assert "forecast(crop, env) -> Record" in md
    assert md.count("|") >= 6  # markdown 표


def test_render_param_table_md():
    t = {"columns": ["param", "value", "unit"], "rows": [["Kc", "1.15", "-"], ["Zr", "0.6", "m"]]}
    md = render_param_table(t)
    assert "| param | value | unit |" in md
    assert "| Kc | 1.15 | - |" in md


def test_param_table_to_csv():
    t = {"columns": ["param", "value"], "rows": [["Kc", "1.15"], ["Zr", "0.6"]]}
    csv = param_table_to_csv(t)
    lines = csv.strip().splitlines()
    assert lines[0] == "param,value"
    assert "Kc,1.15" in lines


def test_render_formal_blocks_combines_all():
    card = {"formal_blocks": {
        "function_spec": [{"name": "f", "signature": "f()", "io": "", "unit": "",
                           "range": "", "default": "", "source": ""}],
        "param_table": {"columns": ["a"], "rows": [["1"]]},
        "state_vector_schema": {"type": "object", "properties": {"x": {"type": "number"}}},
    }}
    md = render_formal_blocks(card)
    assert "함수 명세" in md
    assert "파라미터 표준표" in md
    assert "상태벡터 스키마" in md
    assert "```json" in md  # state_vector는 JSON 코드블록


def test_render_formal_blocks_empty_when_absent():
    assert render_formal_blocks({"title": "x"}) == ""
