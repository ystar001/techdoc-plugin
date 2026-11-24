"""본체 규칙 묶음 공개판 `bundles/core/rules.yaml` (v1.11-c, E15·E18 9).

공개판은 시리즈 규칙 대장에서 `scripts.bundle_split --public-map`으로 만든 생성물이다.
여기서는 생성 결과가 지켜야 할 계약만 본다 — 스키마, 게이트 참조, 분야 낱말 없음, 비공개 필드 없음.
"""
import re

import pytest
import yaml

from techdoc_core.bundles.loader import (
    BundleError,
    core_bundle_dir,
    load_gate_specs,
    load_rule_specs,
)

# 공개판에 나오면 안 되는 분야(농업) 낱말 — 시험 안에 둔 작은 표본(비공개 낱말 목록은 쓰지 않음).
# 정규식: 「저작물」·「재배치」처럼 겉모양만 같은 낱말은 뺀다
DOMAIN_SAMPLE = re.compile(r"노지|관수|(?<!저)작물|필지|재배(?!치)|농업|농가|생육|병해충|시설원예|트랙터|영농")
# 대장 내부 기록 필드 — 공개판에서 뺀다
PRIVATE_FIELDS = {"alias", "source", "decided", "date", "note", "exceptions", "rel", "branch",
                  "target", "stage", "merged_from", "bundle"}


@pytest.fixture(scope="module")
def rules():
    return load_rule_specs([("core", core_bundle_dir())])


def test_public_core_rules_load_and_validate(rules):
    assert len(rules) > 300
    assert {r.layer for r in rules.values()} == {"본체"}


def test_every_core_gate_rule_is_public_and_lower_rules_are_not(rules):
    """gates.yaml `rules:` id는 모두 공개판에 있고, 아래 층으로 옮긴 규칙은 `lower_rules:`에만."""
    specs = load_gate_specs([("core", core_bundle_dir())])
    missing = {g: [r for r in s.rules if r not in rules] for g, s in specs.items()}
    assert {g: v for g, v in missing.items() if v} == {}
    claimed = {g: [r for r in s.lower_rules if r in rules] for g, s in specs.items()}
    assert {g: v for g, v in claimed.items() if v} == {}
    assert any(s.lower_rules for s in specs.values())


def test_public_core_rules_have_no_domain_words(rules):
    hits = [(r.id, m.group(0)) for r in rules.values()
            for m in DOMAIN_SAMPLE.finditer(f"{r.title}\n{r.rule}")]
    assert hits == []


def test_public_core_rules_have_no_private_fields():
    rows = yaml.safe_load((core_bundle_dir() / "rules.yaml").read_text(encoding="utf-8"))
    leaked = {r["id"]: sorted(PRIVATE_FIELDS & set(r)) for r in rows}
    assert {k: v for k, v in leaked.items() if v} == {}
    # enforce는 게이트 연결만
    assert all(set(e) <= {"gate", "level"} for r in rows for e in r["enforce"])


def test_reworded_rules_are_marked(rules):
    marked = [r for r in rules.values() if r.model_dump().get("edition")]
    assert marked and all(r.model_dump()["edition"] == "플러그인 판 문구" for r in marked)


def test_rule_specs_layer_duplicate_is_error(tmp_path):
    """규칙은 덮어쓰지 않는다 — 같은 id가 아래 층에도 있으면 오류(옮긴 규칙은 한 곳에만)."""
    (tmp_path / "rules.yaml").write_text(
        "- {id: P-002, title: x, rule: y, core: [품질], area: P, layer: 문서종류, status: 적용됨}\n",
        encoding="utf-8")
    with pytest.raises(BundleError, match="P-002"):
        load_rule_specs([("core", core_bundle_dir()), ("kind", tmp_path)])


def test_rule_specs_lower_layer_adds_and_missing_dir_skipped(tmp_path):
    (tmp_path / "rules.yaml").write_text(
        "- {id: Q6-999, title: x, rule: y, core: [품질], area: Q6, layer: 문서종류, status: 적용됨}\n",
        encoding="utf-8")
    specs = load_rule_specs([("core", core_bundle_dir()), ("kind", tmp_path), ("domain", None)])
    assert specs["Q6-999"].layer == "문서종류" and "P-002" in specs
