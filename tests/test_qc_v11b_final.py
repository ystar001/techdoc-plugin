"""v1.11-b 최종 리뷰 반영 — 문서 종류별 적용·가독성 수준·로마 숫자 캡션·사전 층·카드 블록 허용·카드 타입 격리."""
import json
from pathlib import Path

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import core_bundle_dir, load_gate_specs
from techdoc_core.constants import DEFAULT_SECTION_TITLES
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.config import default_config, layer_dirs, load_config
from techdoc_core.qc.engine import exit_code, run_qc
from techdoc_core.qc.registry import REGISTRY, sample_model
from techdoc_core.renderers.markdown_tree import render_card_md

TABLE = "| 가 | 나 |\n|---|---|\n| 1 | 2 |"


def _specs():
    return load_gate_specs([("core", core_bundle_dir())])


def _card(body, **extra):
    return {"sections": {"s1": {"title": "", "body": body}}, **extra}


def _res(report, gid):
    return next(r for r in report["results"] if r["gate"] == gid)


def _msgs(gid, model):
    return [f.msg for f in REGISTRY[gid](model).findings]


# ── 1. 문서 종류별 적용(kinds) ──

def test_v21_v57_only_for_methodology():
    specs = _specs()
    assert specs["V21"].kinds == ["methodology"] and specs["V57"].kinds == ["methodology"]
    assert specs["V2"].kinds == []
    sub = {g: specs[g] for g in ("V21", "V57")}
    cards = {"1.1": _card("본문 3건."), "1.2": _card("본문.")}
    tech = sample_model(kind="tech_report", cards=cards)
    rep = run_qc(tech, sub, dict(REGISTRY), default_config(Path(".")))
    for g in ("V21", "V57"):
        r = _res(rep, g)
        assert r["verdict"] == "skip" and r["reason"] == "문서 종류 밖(tech_report)", r
        assert r["count"] == 0
    assert rep["summary"]["blocking_total"] == 0 and exit_code(rep) == 0
    meth = sample_model(kind="methodology", cards=cards)
    rep = run_qc(meth, sub, dict(REGISTRY), default_config(Path(".")))
    assert all(_res(rep, g)["verdict"] == "fail" for g in ("V21", "V57"))
    assert exit_code(rep) == 1


# ── 2. 가독성 수준(E18 11번) ──

def test_readability_style_gates_warning_by_default():
    specs = _specs()
    for g in ("V24", "V31", "V39", "V44"):
        assert specs[g].level == "경고", g


def test_series_config_restores_blocking():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from regression.make_configs import SERIES_BLOCKING
    assert {"V24", "V31", "V39", "V44"} <= set(SERIES_BLOCKING)


# ── 3. F82 로마 숫자 별첨 캡션·카드 도표 캡션 ──

def test_roman_appendix_caption_recognized():
    roman = {"section": "roman", "appendix": "letter"}
    body = f"**표 A.1-1 제목**\n\n{TABLE}\n\n표 A.1-1은 값을 보인다."
    m = sample_model(numbering=roman, cards={"A-1.XL1": _card(body)})
    assert not [x for x in _msgs("V6", m) if "캡션 결손" in x]
    body_b = "그림 B.2-3 흐름\n\n```mermaid\ngraph LR\nA-->B\n```\n\n그림 B.2-3은 흐름이다."
    m = sample_model(numbering=roman, cards={"B-2.XL1": _card(body_b)})
    assert not [x for x in _msgs("V6", m) if "캡션 결손" in x]


def test_arabic_appendix_caption_unchanged():
    from techdoc_core.qc.numbering import normalize_captions
    s = "**표 A.1-1 제목**"
    assert normalize_captions(s, "arabic") == s
    assert normalize_captions(s, "roman") == "**표 A.1-1. 제목**"


def test_v2_takes_card_diagram_and_figure_captions():
    roman = {"section": "roman", "appendix": "letter"}
    m = sample_model(numbering=roman, cards={"II.8": _card(
        "그림 II.8-1에 정리했다.", diagrams=[{"mermaid": "graph LR\nA-->B", "caption": "그림 II.8-1 흐름"}])})
    assert not [x for x in _msgs("V2", m) if "정의 없음" in x]
    m = sample_model(cards={"3": _card(
        "그림 3-1에 정리했다.", figures=[{"path": "a.png", "caption": "그림 3-1. 사진"}])})
    assert not [x for x in _msgs("V2", m) if "정의 없음" in x]
    # 캡션이 없으면 여전히 잡는다
    m = sample_model(cards={"3": _card("그림 3-2에 정리했다.", figures=[{"path": "a.png"}])})
    assert [x for x in _msgs("V2", m) if "정의 없음" in x]


# ── 4. 사전 층 ──

def _mermaid(n):
    return f'```mermaid\nA["{"가" * n}"]\n```\n'


def test_series_layer_gate_limits_override(tmp_path):
    series = tmp_path / "series"
    (series / "dicts").mkdir(parents=True)
    (series / "dicts" / "gate_limits.json").write_text(json.dumps(
        {"V80": {"node_chars": 5, "edge_chars": 5, "axis_chars": 5, "category_chars": 5,
                 "ascii_weight": 0.5},
         "V78": {"max_subitems": 1, "summary_names": "^(?:종합)(?:\\s|$)"}}), encoding="utf-8")
    layers = [("core", core_bundle_dir()), ("series", series)]
    tree = {"a.md": _mermaid(10)}
    assert _msgs("V80", sample_model(tree=tree)) == []
    m = sample_model(tree=tree)
    m.layers = layers
    assert len(_msgs("V80", m)) == 1
    # V78 소항 한계
    text = "## 1. 항\n\n### 1) 가\n\n본문.\n\n### 2) 나\n\n본문.\n"
    base = len(_msgs("V78", sample_model(tree={"3장/3.1. 가.md": text})))
    m = sample_model(tree={"3장/3.1. 가.md": text})
    m.layers = layers
    assert len(_msgs("V78", m)) > base


def test_series_layer_v81_limit(tmp_path):
    series = tmp_path / "series"
    (series / "dicts").mkdir(parents=True)
    (series / "dicts" / "gate_limits.json").write_text(json.dumps(
        {"V81": {"repeat_max_chars": 2}}), encoding="utf-8")
    text = "값은 **관측 기록** 이다.\n\n다시 **관측 기록** 이다.\n"
    base = _msgs("V81", sample_model(tree={"a.md": text}))
    m = sample_model(tree={"a.md": text})
    m.layers = [("core", core_bundle_dir()), ("series", series)]
    assert _msgs("V81", m) != base


def test_spacing_list_extend(tmp_path):
    proj = tmp_path / "proj"
    (proj / "dicts").mkdir(parents=True)
    (proj / "dicts" / "spacing_list.json").write_text(json.dumps({"extend": True, "items": [
        {"id": "X01", "wrong": "가나다라", "right": "가나 다라", "re": "가나다라", "except": [],
         "basis": "시험"}]}), encoding="utf-8")
    tree = {"a.md": "가나다라 측정할수 있다\n"}
    assert len(_msgs("V76", sample_model(tree=tree))) == 1
    m = sample_model(tree=tree)
    m.layers = [("core", core_bundle_dir()), ("project", proj)]
    assert len(_msgs("V76", m)) == 2


def test_adapter_fills_layers(tmp_path):
    (tmp_path / "ser").mkdir()
    (tmp_path / "techdoc.project.yaml").write_text("kind: methodology\nseries: ser\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    model = build_model(tmp_path, cfg)
    assert model.layers == layer_dirs(cfg)
    assert sample_model().layers == []


# ── 5. V88과 플러그인 카드 블록 ──

def _tree_cards(n=5):
    secs = {k: {"title": "", "body": f"{v} 본문이다."} for k, v in DEFAULT_SECTION_TITLES.items()}
    text = "\n".join(render_card_md({"card_id": f"1.{i}", "title": f"카드 {i}", "sections": secs})
                     for i in range(1, n + 1))
    return {"1장/1.1. 가.md": text}


def test_v88_allows_plugin_card_blocks_for_tech_report():
    assert _msgs("V88", sample_model(kind="tech_report", tree=_tree_cards())) == []
    assert _msgs("V88", sample_model(kind="methodology", tree=_tree_cards()))


# ── 6. 카드 하나의 타입 오류 ──

def test_malformed_card_does_not_disable_gates():
    cards = {"1.1": {"sections": {"s": {"body": 123, "title": 7}}},
             "1.2": _card("1.5절에서 다룬다.")}
    m = sample_model(cards=cards)
    rep = run_qc(m, _specs(), dict(REGISTRY), default_config(Path(".")))
    assert rep["gate_errors"] == []
    assert exit_code(rep) != 3
    assert any("1.5절 없음" in it["msg"] for it in _res(rep, "V2")["items"])
