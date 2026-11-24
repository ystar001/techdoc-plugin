"""차트 출력 결정성 (v1.10.2 — F67)."""
import pytest

from scripts.generate_chart import generate_figure

SPEC = {"id": "f1", "type": "bar", "title": "물 절감률",
        "data": {"labels": ["가", "나"], "values": [1, 2]}}


@pytest.mark.parametrize("fmt", ["png", "svg"])
def test_same_spec_same_bytes(tmp_path, fmt):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = generate_figure(SPEC, tmp_path / "a", fmt=fmt).read_bytes()
    b = generate_figure(SPEC, tmp_path / "b", fmt=fmt).read_bytes()
    assert a == b


def test_svg_has_no_date(tmp_path):
    out = generate_figure(SPEC, tmp_path, fmt="svg")
    assert out.suffix == ".svg"
    assert b"<dc:date>" not in out.read_bytes()


def test_spec_format_key_selects_svg(tmp_path):
    out = generate_figure({**SPEC, "format": "svg"}, tmp_path)
    assert out.suffix == ".svg"
