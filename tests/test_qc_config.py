"""프로젝트 설정 techdoc.project.yaml (v1.11-a — 설계 D1·D3.2)."""
import pytest

from techdoc_core.bundles.loader import core_bundle_dir
from techdoc_core.qc.config import default_config, layer_dirs, load_config, validate_gate_ids


def test_defaults_without_config(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.kind == "tech_report"
    assert cfg.paths.cards == tmp_path / "output" / "cards"
    assert cfg.paths.render_tree == tmp_path / "output" / "render" / "tree"
    assert cfg.paths.references == tmp_path / "output" / "reference_list.json"
    assert cfg.numbering == {"section": "arabic", "appendix": "letter"}
    assert cfg.extra == {} and cfg.gates_off == []


def test_series_style_paths_and_numbering(tmp_path):
    (tmp_path / "techdoc.project.yaml").write_text(
        "schema: techdoc-project/1\nkind: methodology\nnumbering: {section: roman}\n"
        "paths: {cards: output_v2/cards, render_tree: output_v2/render/tree,"
        " references: output_v2/reference_list.json}\n"
        "gates: {off: [V8], exempt: {'1.1': [V13]}, level: {V45: 경고}}\n"
        "extra: {citation: {internal_files: [PLAN.md]}}\n",
        encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.kind == "methodology"
    assert cfg.numbering["section"] == "roman"
    assert cfg.paths.render_tree.parts[-3:] == ("output_v2", "render", "tree")
    assert cfg.gates_off == ["V8"] and cfg.exempt == {"1.1": ["V13"]}
    assert cfg.level_overrides == {"V45": "경고"}
    assert cfg.extra["citation"]["internal_files"] == ["PLAN.md"]


def test_explicit_config_path(tmp_path):
    other = tmp_path / "cfg" / "x.yaml"
    other.parent.mkdir()
    other.write_text("kind: methodology\n", encoding="utf-8")
    assert load_config(tmp_path, other).kind == "methodology"


def test_invalid_numbering_rejected(tmp_path):
    (tmp_path / "techdoc.project.yaml").write_text("numbering: {section: hex}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="numbering"):
        load_config(tmp_path)


def test_invalid_level_override_rejected(tmp_path):
    (tmp_path / "techdoc.project.yaml").write_text("gates: {level: {V8: 엄격}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="level"):
        load_config(tmp_path)


def test_unknown_gate_id_in_off_warns(tmp_path):
    (tmp_path / "techdoc.project.yaml").write_text(
        "gates: {off: [v8, V99, V8]}\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    validate_gate_ids(cfg, {"V8"})
    assert cfg.warnings == ["모르는 게이트 id: v8", "모르는 게이트 id: V99"]


def test_layer_dirs_order(tmp_path):
    cfg = default_config(tmp_path)
    names = [n for n, _ in layer_dirs(cfg)]
    assert names == ["core", "kind", "domain", "series", "project"]
    assert layer_dirs(cfg)[0][1] == core_bundle_dir()
