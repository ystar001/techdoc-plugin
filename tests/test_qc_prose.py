"""산문 공용 헬퍼·사전 묶음 (v1.11-b — 시리즈 prose_gates에서 이식)."""
import json

from techdoc_core.qc.dicts import load_dict
from techdoc_core.qc.prose import paragraphs, prose_lines, sections, strip_en_gloss


def test_prose_lines_skip_fence_table_quote_heading_caption():
    text = "본문 하나.\n```\n코드\n```\n| 표 |\n> 인용\n## 1.1 표제\n**표 1.** 캡션\n본문 둘."
    assert [ln for _, ln in prose_lines(text)] == ["본문 하나.", "본문 둘."]


def test_paragraphs_join_lines_and_split_list_items():
    text = "## 1.1 가\n첫 줄\n둘째 줄\n\n- 항목 하나\n- 항목 둘\n"
    paras = list(paragraphs(text))
    assert paras[0][1] == "첫 줄 둘째 줄" and paras[0][2] == "가"
    assert [p[1] for p in paras[1:]] == ["- 항목 하나", "- 항목 둘"]


def test_sections_by_heading():
    out = list(sections("## 1.1 가\n본문\n### 1.1.1 나\n더"))
    assert [(lv, num, title) for lv, num, title, _, _ in out] == [(2, "1.1", "가"), (3, "1.1.1", "나")]


def test_strip_en_gloss():
    assert strip_en_gloss("표준(SOP, Standard Operating Procedure)") == "표준(SOP)"


def test_core_dicts_load_without_domain():
    spacing = load_dict("spacing_list.json", [("core", None)])
    assert len(spacing["items"]) >= 20
    limits = load_dict("gate_limits.json", [("core", None)])
    assert "V80" in limits and "V82" not in limits


def test_dict_lower_layer_replaces_and_extends(tmp_path):
    (tmp_path / "dicts").mkdir()
    (tmp_path / "dicts" / "spacing_list.json").write_text(
        json.dumps({"items": [{"id": "X1", "re": "가나"}]}), encoding="utf-8")
    replaced = load_dict("spacing_list.json", [("core", None), ("series", tmp_path)])
    assert [i["id"] for i in replaced["items"]] == ["X1"]
    (tmp_path / "dicts" / "spacing_list.json").write_text(
        json.dumps({"extend": True, "items": [{"id": "X1", "re": "가나"}]}), encoding="utf-8")
    extended = load_dict("spacing_list.json", [("core", None), ("series", tmp_path)])
    assert len(extended["items"]) >= 21
