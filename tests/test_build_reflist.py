"""build_reflist — 정규화 보존·skip 종료 코드 (v1.10.2 — F61·F78)."""
import sys

from scripts.build_reflist import build_reflist
from scripts.build_reflist import main as reflist_main

_FM = ("---\nid: {id}\ncategory: 학술\nsource: 출처\nyear: 2020\ntitle: 제목 {id}\n"
       "reliability: {rel}\nkey_numbers: {kn}\n---\n본문\n")


def _ref(d, rid, rel="확인됨", kn="[]"):
    (d / f"{rid}.md").write_text(_FM.format(id=rid, rel=rel, kn=kn), encoding="utf-8")


def test_build_reflist_keeps_normalized_refs(tmp_path):
    _ref(tmp_path, "REF-001")
    _ref(tmp_path, "REF-002", rel="교차확인필요")
    _ref(tmp_path, "REF-003", kn="[{'ISO': 'TC23'}]")
    r = build_reflist(tmp_path)
    assert r["total_refs"] == 3
    assert r["_meta"]["skipped"] == 0
    assert r["_meta"]["normalized"] == 2


def test_broken_frontmatter_counts_as_skipped(tmp_path, monkeypatch):
    _ref(tmp_path, "REF-001")
    (tmp_path / "REF-002.md").write_text("---\nid: [깨짐\n---\n", encoding="utf-8")
    r = build_reflist(tmp_path)
    assert r["total_refs"] == 1
    assert r["_meta"]["skipped_files"] == ["REF-002.md"]
    monkeypatch.setattr(sys, "argv", ["build_reflist", "--keyref", str(tmp_path),
                                      "-o", str(tmp_path / "out")])
    assert reflist_main() == 2


def test_allow_skip_flag_returns_0(tmp_path, monkeypatch):
    _ref(tmp_path, "REF-001")
    (tmp_path / "REF-002.md").write_text("---\nid: [깨짐\n---\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["build_reflist", "--keyref", str(tmp_path),
                                      "-o", str(tmp_path / "out"), "--allow-skip"])
    assert reflist_main() == 0
