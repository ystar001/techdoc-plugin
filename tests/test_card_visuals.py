from pathlib import Path

from techdoc_core.models import TechCard, ProjectCard, ProductCard
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
