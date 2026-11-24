"""dedupe_keyref — KeyRef 중복 후보·필드 단위 병합·안전 재번호 (v1.10.2 — F63·F72)."""
import json
import sys

import yaml

from scripts.dedupe_keyref import (
    apply_pairs,
    check_aliases,
    find_candidates,
    merge_pair,
    rewrite_ref_ids,
)
from scripts.dedupe_keyref import main as dedupe_main


def _ref(d, rid, url="", title="제목", key_numbers=(), related_sections=(), fname=None):
    fm = {"id": rid, "category": "학술", "source": "출처", "year": 2020, "title": title,
          "url": url, "reliability": "확인됨", "key_numbers": list(key_numbers),
          "related_sections": list(related_sections)}
    p = d / (fname or f"{rid}.md")
    p.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
                 + "---\n원문 발췌\n", encoding="utf-8")
    return p


def _fm(p):
    text = p.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---\n")[1])


def test_same_url_is_candidate_not_merged(tmp_path):
    _ref(tmp_path, "REF-012", url="https://www.rda.go.kr/x/", title="노지 관수 지침")
    _ref(tmp_path, "REF-207", url="http://rda.go.kr/x", title="Field irrigation guideline")
    cands = find_candidates(tmp_path)
    assert cands == [{"canonical": "REF-012", "alias": "REF-207", "reason": "url", "score": 100}]
    assert (tmp_path / "REF-207.md").exists()


def test_similar_title_is_candidate(tmp_path):
    _ref(tmp_path, "REF-003", title="Soil moisture sensing for irrigation scheduling")
    _ref(tmp_path, "REF-090", title="Soil moisture sensing for irrigation scheduling.")
    assert find_candidates(tmp_path)[0]["reason"] == "title"


def test_merge_unions_key_numbers_and_keeps_canonical_title():
    c = {"id": "REF-012", "title": "Original English Title", "key_numbers": ["a"],
         "related_sections": ["1.1"]}
    a = {"id": "REF-207", "title": "한국어 의역 제목", "key_numbers": ["a", "b"],
         "related_sections": ["2.3"]}
    m, rep = merge_pair(c, a)
    assert m["title"] == "Original English Title"
    assert m["key_numbers"] == ["a", "b"]
    assert m["related_sections"] == ["1.1", "2.3"]
    assert rep["key_numbers"] == 1


def test_merge_fills_only_empty_canonical_fields():
    c = {"id": "REF-012", "url": "", "excerpt": ""}
    a = {"id": "REF-207", "url": "https://x", "excerpt": "발췌"}
    m, rep = merge_pair(c, a)
    assert m["url"] == "https://x" and m["excerpt"] == "발췌" and rep["excerpt"] is True


def test_rewrite_plain_tokens():
    out, manual = rewrite_ref_ids("근거다[REF-207].", {"REF-207": "REF-012"})
    assert out == "근거다[REF-012]." and manual == []


def test_rewrite_does_not_touch_longer_number():
    out, _ = rewrite_ref_ids("REF-2070 과 REF-207", {"REF-207": "REF-012"})
    assert out == "REF-2070 과 REF-012"


def test_rewrite_refuses_range_notation():
    text = "여러 연구(REF-205~208)와 REF-136~144·207이 있다."
    out, manual = rewrite_ref_ids(text, {"REF-207": "REF-012"})
    assert out == text
    assert len(manual) == 2


def test_apply_moves_alias_and_writes_map(tmp_path):
    kr = tmp_path / "KeyRef"
    kr.mkdir()
    _ref(kr, "REF-012", url="https://a", key_numbers=["x"], fname="012_a.md")
    _ref(kr, "REF-207", url="https://a", key_numbers=["y"], fname="207_b.md")
    reports = apply_pairs(kr, [{"canonical": "REF-012", "alias": "REF-207"}])
    assert (tmp_path / "KeyRef_dup" / "207_b.md").exists()
    assert not (kr / "207_b.md").exists()
    assert _fm(kr / "012_a.md")["key_numbers"] == ["x", "y"]
    assert "alias: REF-207" in (kr / "012_a.md").read_text(encoding="utf-8")
    amap = json.loads((tmp_path / "ref_alias_map.json").read_text(encoding="utf-8"))
    assert amap == {"REF-207": "REF-012"}
    assert reports[0]["key_numbers"] == 1


def test_check_flags_orphan_key_numbers(tmp_path, monkeypatch):
    kr = tmp_path / "KeyRef"
    kr.mkdir()
    dup = tmp_path / "KeyRef_dup"
    dup.mkdir()
    _ref(kr, "REF-012", key_numbers=["x"])
    _ref(dup, "REF-207", key_numbers=["x", "고아 수치"])
    (tmp_path / "ref_alias_map.json").write_text(json.dumps({"REF-207": "REF-012"}),
                                                 encoding="utf-8")
    warns = check_aliases(kr)
    assert len(warns) == 1 and "고아 수치" in warns[0]
    monkeypatch.setattr(sys, "argv", ["dedupe_keyref", str(kr), "--check"])
    assert dedupe_main() == 3
