"""문서 종류 묶음 — 기본 설정·분량 프로필을 kind가 실어 나름 (v1.11-c Task 4, E18 1·2·12).

겹침 규칙(본체 → 문서 종류 → 프로젝트, 표는 재귀·값과 목록은 교체), 묶음 없는 kind의 경고,
v1.11-b에서 미룬 지적(extra 형식 검증·면제 불가 게이트 경고·로마 숫자 통일·전문어 사전 층·
산문 캡션 정규화)을 시험한다.
"""
import json
import re
from pathlib import Path

import pytest

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import (
    BundleError,
    core_bundle_dir,
    kinds_bundle_dir,
    load_gate_specs,
    read_kind_bundle,
)
from techdoc_core.card_id import _ROMAN_RE
from techdoc_core.constants import CARD_LENGTH_BY_IMPORTANCE, DEFAULT_SECTION_TITLES
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.config import layer_dirs, load_config, validate_gate_ids
from techdoc_core.qc.engine import _exempted, run_qc
from techdoc_core.qc.numbering import ROMAN, head_re, section_file_re
from techdoc_core.qc.prose import is_cap_line, paragraphs, prose_lines
from techdoc_core.qc.registry import REGISTRY, GateOutput, sample_model

CARD_FLOOR = CARD_LENGTH_BY_IMPORTANCE["low"]["tech"][0]  # card_length_rules.md 기술 카드 low 하한


def _write(root: Path, text: str) -> Path:
    (root / "techdoc.project.yaml").write_text(text, encoding="utf-8")
    return root


def _msgs(gid, model):
    return [f.msg for f in REGISTRY[gid](model).findings]


def _specs():
    return load_gate_specs([("core", core_bundle_dir())])


# ── 1. 플러그인이 싣는 묶음 ──

def test_tech_report_bundle_block_heads_equal_card_titles():
    """V88 블록 표제 목록이 렌더러의 카드 블록 표제와 어긋나지 않게 고정."""
    b = read_kind_bundle(kinds_bundle_dir() / "tech_report")
    assert b["extra"]["repeat"]["block_heads"] == list(DEFAULT_SECTION_TITLES.values())


def test_tech_report_bundle_length_floor_matches_card_rules():
    b = read_kind_bundle(kinds_bundle_dir() / "tech_report")
    for key in ("check_quality", "verify_cards"):
        table = next(iter(b["extra"][key].values()))
        assert set(table.values()) == {CARD_FLOOR}, key


def test_methodology_bundle_has_no_series_lengths():
    """methodology는 범용 하한(경고)만 — 시리즈 편 분량(14,000 등)은 시리즈 층 설정이 싣는다."""
    b = read_kind_bundle(kinds_bundle_dir() / "methodology")
    for key in ("check_quality", "verify_cards"):
        table = next(iter(b["extra"][key].values()))
        assert max(table.values()) <= CARD_FLOOR, key
    assert "repeat" not in b["extra"]


def test_length_floor_gates_stay_warning_level():
    specs = _specs()
    for gid in ("PLG-CQ-self_model_length", "VC-C"):
        assert specs[gid].level == "경고"


# ── 2. 겹침 규칙 ──

def _private_kind(tmp_path: Path) -> Path:
    d = tmp_path / "kinds" / "mine"
    d.mkdir(parents=True)
    (d / "kind.yaml").write_text(
        "schema: techdoc-kind/1\n"
        "gates: {level: {V27: 막음, V18: 경고}, off: [V45, V46]}\n"
        "extra:\n"
        "  check_quality: {size_thresholds: {S: 2000, L1: 1000}}\n"
        "  repeat: {block_heads: [가, 나], max_repeats: 4}\n"
        "expects: {V57: '>=1'}\n", encoding="utf-8")
    return d


def test_merge_kind_then_project_dicts_deep_lists_replace(tmp_path):
    _private_kind(tmp_path)
    _write(tmp_path, "kind: methodology\nkind_dir: kinds/mine\n"
                     "gates: {off: [V8], level: {V18: 막음}}\n"
                     "extra:\n"
                     "  check_quality: {size_thresholds: {S: 3000}}\n"
                     "  repeat: {block_heads: [다]}\n")
    cfg = load_config(tmp_path)
    # 표는 재귀로 겹친다 — 프로젝트가 적은 키만 바뀜
    assert cfg.extra["check_quality"]["size_thresholds"] == {"S": 3000, "L1": 1000}
    assert cfg.level_overrides == {"V27": "막음", "V18": "막음"}
    assert cfg.extra["repeat"]["max_repeats"] == 4
    # 목록은 통째로 교체
    assert cfg.extra["repeat"]["block_heads"] == ["다"]
    assert cfg.gates_off == ["V8"]
    assert cfg.expects == {"V57": ">=1"}
    assert cfg.warnings == []


def test_kind_off_used_when_project_silent(tmp_path):
    _private_kind(tmp_path)
    _write(tmp_path, "kind: methodology\nkind_dir: kinds/mine\n")
    assert load_config(tmp_path).gates_off == ["V45", "V46"]


def test_private_kind_dir_is_kind_layer(tmp_path):
    d = _private_kind(tmp_path)
    _write(tmp_path, "kind: methodology\nkind_dir: kinds/mine\n")
    cfg = load_config(tmp_path)
    assert dict(layer_dirs(cfg))["kind"] == d


def test_public_kind_layer_is_plugin_bundle(tmp_path):
    cfg = load_config(_write(tmp_path, "kind: methodology\n"))
    assert dict(layer_dirs(cfg))["kind"] == kinds_bundle_dir() / "methodology"


def test_kind_expects_makes_missing_target_fail(tmp_path):
    _private_kind(tmp_path)
    cfg = load_config(_write(tmp_path, "kind: methodology\nkind_dir: kinds/mine\n"))
    model = sample_model(kind="methodology", cards={"1.1": {"sections": {"s": {"body": "본문."}}}})
    spec = _specs()["V57"]
    rep = run_qc(model, {"V57": spec}, {"V57": lambda m: GateOutput(0)}, cfg)
    row = rep["results"][0]
    assert row["verdict"] == "fail" and "있어야 할 대상" in row["reason"]


# ── 3. 묶음이 없는 kind (Review Focus 3) ──

def test_policy_report_without_bundle_runs_core_defaults_and_warns(tmp_path):
    cfg = load_config(_write(tmp_path, "kind: policy_report\n"))
    assert cfg.extra == {} and cfg.gates_off == [] and cfg.level_overrides == {}
    assert len(cfg.warnings) == 1 and "문서 종류 묶음이 없음" in cfg.warnings[0]
    assert "policy_report" in cfg.warnings[0]
    out = tmp_path / "output" / "cards"
    out.mkdir(parents=True)
    (out / "1.1_card.json").write_text(json.dumps(
        {"card_id": "1.1", "sections": {"s1": {"title": "정의", "body": "본문이다."}}},
        ensure_ascii=False), encoding="utf-8")
    rep = run_qc(build_model(tmp_path, cfg), _specs(), dict(REGISTRY), cfg)
    assert rep["gate_errors"] == []
    assert any("문서 종류 묶음이 없음" in w for w in rep["warnings"])


def test_missing_private_kind_dir_warns(tmp_path):
    cfg = load_config(_write(tmp_path, "kind: methodology\nkind_dir: 없는/곳\n"))
    assert any("문서 종류 묶음이 없음" in w for w in cfg.warnings)


def test_unknown_kind_warns_once(tmp_path):
    cfg = load_config(_write(tmp_path, "kind: tech_reprot\n"))
    assert len(cfg.warnings) == 1 and "모르는 문서 종류" in cfg.warnings[0]


@pytest.mark.parametrize("body, match", [
    ("schema: techdoc-kind/2\n", "schema"),
    ("schema: techdoc-kind/1\nlevels: {}\n", "모르는 키"),
    ("schema: techdoc-kind/1\ngates: {exempt: {}}\n", "gates의 모르는 키"),
    ("schema: techdoc-kind/1\ngates: {off: V8}\n", "gates.off"),
])
def test_bad_kind_bundle_rejected(tmp_path, body, match):
    d = tmp_path / "k"
    d.mkdir()
    (d / "kind.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(BundleError, match=match):
        read_kind_bundle(d)


# ── 4. tech_report 분량 프로필이 실제로 걸림 ──

def test_tech_report_floor_applies_in_qc(tmp_path):
    """플러그인 카드 하나 분량(1,000자)은 tech_report에서 분량 경고가 아니다(옛 본체 14,000자 기준이면 경고)."""
    cards = {"1.1": {"card_id": "1.1", "sections": {"s1": {"title": "정의", "body": "가" * 1000}}}}
    cfg = load_config(tmp_path)
    m = sample_model(cards=cards, extra=cfg.extra)
    assert _msgs("PLG-CQ-self_model_length", m) == []
    assert _msgs("PLG-CQ-self_model_length", sample_model(cards=cards))


# ── 5. extra 형식 검증 ──

@pytest.mark.parametrize("extra, key", [
    ("repeat: {allow_heads: 결론}", "extra.repeat.allow_heads"),
    ("repeat: {max_repeats: abc}", "extra.repeat.max_repeats"),
    ("repeat: {max_repeats: 0}", "extra.repeat.max_repeats"),
    ("repeat: {max_repeats: true}", "extra.repeat.max_repeats"),
    ("check_quality: {size_thresholds: {S: 많이}}", "extra.check_quality.size_thresholds"),
    ("structure: {appendix_letters: [A, B]}", "extra.structure.appendix_letters"),
    ("leak: [a.py]", "extra.leak"),
    ("citation: {internal_files: [1, 2]}", "extra.citation.internal_files"),
])
def test_extra_shape_errors_name_the_key(tmp_path, extra, key):
    _write(tmp_path, f"extra:\n  {extra}\n")
    with pytest.raises(ValueError, match=re.escape(key)):
        load_config(tmp_path)


def test_kind_bundle_extra_is_validated_too(tmp_path):
    d = tmp_path / "k"
    d.mkdir()
    (d / "kind.yaml").write_text("schema: techdoc-kind/1\nextra: {repeat: {max_repeats: 0}}\n",
                                 encoding="utf-8")
    _write(tmp_path, "kind: methodology\nkind_dir: k\n")
    with pytest.raises(ValueError, match="max_repeats"):
        load_config(tmp_path)


def test_max_repeats_one_is_honoured():
    tree = {"3장/3.1. 가.md": "## 1. 배경 — 가\n\n## 2. 배경 — 나\n\n## 3. 방법\n"}
    assert _msgs("V88", sample_model(tree=tree)) == []
    assert len(_msgs("V88", sample_model(tree=tree, extra={"repeat": {"max_repeats": 1}}))) == 1


def test_project_allow_heads_keep_kind_block_heads(tmp_path):
    cfg = load_config(_write(tmp_path, "extra: {repeat: {allow_heads: [사례]}}\n"))
    assert cfg.extra["repeat"]["allow_heads"] == ["사례"]
    assert cfg.extra["repeat"]["block_heads"] == list(DEFAULT_SECTION_TITLES.values())


# ── 6. 면제 ──

def test_exempt_on_non_exemptable_gate_warns(tmp_path):
    cfg = load_config(_write(tmp_path, "gates: {exempt: {'1.1': {gates: [V8, V27], why: 인용}}}\n"))
    validate_gate_ids(cfg, _specs())
    hits = [w for w in cfg.warnings if "exemptable: false" in w]
    assert len(hits) == 1 and "V8" in hits[0] and "1.1" in hits[0]


def test_exempt_id_set_does_not_check_exemptable(tmp_path):
    cfg = load_config(_write(tmp_path, "gates: {exempt: {'1.1': {gates: [V8], why: 인용}}}\n"))
    validate_gate_ids(cfg, set(_specs()))
    assert cfg.warnings == []


def test_exempt_key_without_pipe_covers_whole_card():
    ex = {"1.4": {"gates": ["V27"], "why": "법령 원문"}}
    assert _exempted("V27", "1.4|sec3:12", ex)
    assert _exempted("V27", "1.4: 카드", ex)
    assert not _exempted("V27", "1.41|sec3:1", ex)
    assert not _exempted("V18", "1.4|sec3:1", ex)


# ── 7. 로마 숫자 ──

def test_roman_class_matches_card_id():
    assert _ROMAN_RE.pattern == f"^{ROMAN}$"
    assert head_re("roman").match("## XL.2 제목")
    assert head_re("roman").match("## LC.1 제목")
    assert not head_re("roman").match("## Introduction 개요")
    assert section_file_re("roman").match("XL.3. 제목.md")


def test_v30_roman_skips_standard_numbers():
    text = ("## II.6.1 제목\n\nX.509 인증서와 V.92 모뎀, ITU-T I.430을 쓴다. II.6.1절을 본다.\n")
    m = sample_model(tree={"a.md": text}, numbering={"section": "roman"})
    assert _msgs("V30", m) == []
    m2 = sample_model(tree={"a.md": text + "II.6.2절도 본다.\n"}, numbering={"section": "roman"})
    assert _msgs("V30", m2) == ["죽은 참조 II.6.2"]


# ── 8. 분야 전문어 사전 층 ──

def test_qs_jargon_from_layer_dict(tmp_path):
    ser = tmp_path / "ser"
    (ser / "dicts").mkdir(parents=True)
    (ser / "dicts" / "qs_jargon.json").write_text(json.dumps({"items": ["칼만이득"]}),
                                                  encoding="utf-8")
    qs = {"goal": "칼만이득으로 값 하나를 판단에 쓸 수 있게 적을 수 있다.",
          "questions": ["기록의 요건은 무엇인가?", "여덟 항목은 어떤 차례로 채우나?"]}
    cards = {"1.1": {"sections": {"s1": {"title": "", "body": "x"}}, "quick_summary": qs}}
    plain = sample_model(kind="methodology", cards=cards)
    layered = sample_model(kind="methodology", cards=cards)
    layered.layers = [("core", core_bundle_dir()), ("series", ser)]
    assert len(_msgs("V21", layered)) == len(_msgs("V21", plain)) + 1
    by_extra = sample_model(kind="methodology", cards=cards,
                            extra={"structure": {"qs_jargon": ["칼만이득"]}})
    assert _msgs("V21", by_extra) == _msgs("V21", layered)


# ── 9. 산문 게이트의 캡션 정규화 (F82) ──

ROMAN_CAPS = ("**표 II.8-1 기준값**\n\n표 A.1-1 별첨 기준\n\n그림 IV.19-1 배치\n\n"
              "본문 문장이다.\n")


def test_prose_lines_treat_roman_captions_as_captions():
    lines = [ln for _i, ln in prose_lines(ROMAN_CAPS, "roman")]
    assert lines == ["본문 문장이다."]
    assert [ln for _i, ln in prose_lines(ROMAN_CAPS)] != lines  # arabic은 원본 그대로


def test_paragraphs_treat_roman_captions_as_captions():
    paras = [p for _s, p, _h in paragraphs(ROMAN_CAPS, "roman")]
    assert paras == ["본문 문장이다."]


def test_is_cap_line_roman():
    assert is_cap_line("표 A.1-1 별첨 기준", "roman")
    assert is_cap_line("그림 IV.19-1 배치", "roman")
    assert not is_cap_line("표 A.1-1 별첨 기준")
    assert is_cap_line("표 3-1. 기준")
