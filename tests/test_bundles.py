"""묶음 스키마·층 겹침 로더 (v1.11-a — F85)."""
import pytest

from techdoc_core.bundles.loader import BundleError, core_bundle_dir, load_gate_specs
from techdoc_core.bundles.schema import RuleSpec


def test_core_gate_specs_load():
    specs = load_gate_specs([("core", core_bundle_dir())])
    assert set(specs) == {"V8", "V13", "V45", "V68",  # v1.11-a
                          "V2", "V21", "V26", "V30", "V31", "V34", "V39", "V44",  # v1.11-b 구조
                          "V57", "V59", "V72", "V78",
                          "V23", "V24", "V25", "V27", "V28", "V29", "V35", "V36",  # v1.11-b 문장
                          "V41", "V41W", "V43", "V50", "V53", "V54", "V56", "V69", "V76", "V81",
                          "V6", "V12", "V15", "V17", "V18", "V40", "V62", "V63",  # v1.11-b 캡션
                          "V66", "V73", "V75", "V80",
                          "V22", "V37", "V42", "V46", "V47", "V48", "V49", "V51",  # v1.11-b 표기
                          "V64", "V7", "V14"}
    assert specs["V59"].exemptable is False and specs["V78"].level == "시범"
    assert specs["V57"].expects == {"methodology": ">=1"}
    assert specs["V8"].level == "막음"
    assert specs["V8"].rules == ["Q1-003"]
    assert specs["V13"].core == ["품질", "일관성"]


def test_lower_layer_override_requires_flag(tmp_path):
    (tmp_path / "gates.yaml").write_text(
        "- {id: V8, title: x, layer: 시리즈, level: 경고, inputs: [tree]}\n", encoding="utf-8")
    with pytest.raises(BundleError, match="override"):
        load_gate_specs([("core", core_bundle_dir()), ("series", tmp_path)])


def test_lower_layer_override_with_flag(tmp_path):
    (tmp_path / "gates.yaml").write_text(
        "- {id: V8, title: x, layer: 시리즈, level: 경고, inputs: [tree], override: true}\n",
        encoding="utf-8")
    specs = load_gate_specs([("core", core_bundle_dir()), ("series", tmp_path)])
    assert specs["V8"].level == "경고"


def test_new_gate_in_lower_layer_is_added(tmp_path):
    (tmp_path / "gates.yaml").write_text(
        "- {id: S1, title: 시리즈 게이트, layer: 시리즈, level: 경고, inputs: [tree]}\n",
        encoding="utf-8")
    assert "S1" in load_gate_specs([("core", core_bundle_dir()), ("series", tmp_path)])


def test_missing_layer_dir_is_skipped():
    assert "V8" in load_gate_specs([("core", core_bundle_dir()), ("domain", None)])


def test_invalid_level_rejected(tmp_path):
    (tmp_path / "gates.yaml").write_text(
        "- {id: X1, title: x, layer: 본체, level: 엄격, inputs: [tree]}\n", encoding="utf-8")
    with pytest.raises(BundleError):
        load_gate_specs([("core", tmp_path)])


def test_rule_spec_reads_series_ledger_row():
    row = {"id": "Q8-014", "alias": ["개정_룰 98-1"], "title": "참고문헌 APA 7판", "rule": "…",
           "core": ["품질"], "area": "Q8", "branch": "인용", "layer": "본체", "status": "일부",
           "enforce": [{"gate": "V68", "level": "막음"}]}
    assert RuleSpec(**row).enforce[0]["gate"] == "V68"


def test_release_zip_includes_bundles():
    from scripts.build_release import INCLUDE_ROOTS
    assert "bundles" in INCLUDE_ROOTS
