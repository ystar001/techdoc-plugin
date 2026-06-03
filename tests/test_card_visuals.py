from pathlib import Path

from techdoc_core.models import TechCard, ProjectCard, ProductCard
from techdoc_core.renderers.card_renderer import render_card_visuals, render_tech_card
from scripts.generate_chart import specs_to_figures


def _roundtrip(card):
    cls = type(card)
    return cls.from_dict(card.to_dict())


def test_tech_card_visual_fields_default_empty():
    c = TechCard(id="1.1.1", name="관개")
    assert c.figures == [] and c.diagrams == []


def test_tech_card_visual_fields_roundtrip():
    c = TechCard(
        id="1.1.1", name="관개",
        figures=[{"path": "figures/g.png", "caption": "생육곡선"}],
        diagrams=[{"mermaid": "graph TD; A-->B", "caption": "흐름도"}],
    )
    r = _roundtrip(c)
    assert r.figures[0]["path"] == "figures/g.png"
    assert r.diagrams[0]["mermaid"] == "graph TD; A-->B"


def test_project_and_product_cards_have_visual_fields():
    p = ProjectCard(id="2.1.1", name="프로젝트", figures=[{"path": "x.png"}])
    q = ProductCard(id="3.1.1", name="제품", diagrams=[{"mermaid": "graph LR; A-->B"}])
    assert _roundtrip(p).figures[0]["path"] == "x.png"
    assert _roundtrip(q).diagrams[0]["mermaid"] == "graph LR; A-->B"


def test_legacy_card_without_visual_fields_loads_empty():
    legacy = {"id": "1.1.1", "name": "관개", "blocks": {"overview": "x"}}
    c = TechCard.from_dict(legacy)
    assert c.figures == [] and c.diagrams == []


def test_specs_to_figures_renders_and_returns_refs(tmp_path):
    specs = [
        {"id": "fig1", "type": "bar", "caption": "수확량",
         "data": {"labels": ["A", "B"], "values": [3, 5]}},
    ]
    figures = specs_to_figures(specs, tmp_path)
    assert len(figures) == 1
    assert figures[0]["caption"] == "수확량"
    # path가 실제 생성된 파일을 가리킴
    assert (tmp_path / Path(figures[0]["path"]).name).exists()


def test_specs_to_figures_empty_list(tmp_path):
    assert specs_to_figures([], tmp_path) == []


def test_render_card_visuals_figure_and_diagram():
    card = TechCard(
        id="1.1.1", name="관개",
        figures=[{"path": "figures/g.png", "caption": "생육곡선"}],
        diagrams=[{"mermaid": "graph TD; A-->B", "caption": "흐름도"}],
    )
    html = render_card_visuals(card)
    assert "<figure" in html and 'src="figures/g.png"' in html
    assert "생육곡선" in html
    assert '<pre class="mermaid">' in html and "graph TD; A-->B" in html


def test_render_card_visuals_empty_is_blank():
    assert render_card_visuals(TechCard(id="1", name="x")) == ""


def test_render_tech_card_includes_visuals():
    card = TechCard(id="1.1.1", name="관개", overview="개요",
                    figures=[{"path": "g.png", "caption": "c"}])
    html = render_tech_card(card)
    assert "<figure" in html and 'src="g.png"' in html
