"""merge_research 계약 방어 테스트 (v1.9.0 워크스트림 G — F34·F44).

researcher round JSON의 refs_found는 스키마상 list[str](REF id)이나,
기존 dedupe_refs는 dict(url·title)를 가정해 str 원소에서 .get() 크래시했다.
"""
import json as _json
import sys as _sys

from scripts.merge_research import dedupe_refs, merge_research
from scripts.merge_research import main as _merge_main


def test_dedupe_handles_str_id_list():
    """F34/F44 — str REF id 리스트에서 크래시하지 않고 정규화 처리."""
    kept, removed = dedupe_refs(["REF-001", "REF-002"])
    assert len(kept) == 2
    assert {r.get("id") for r in kept} == {"REF-001", "REF-002"}


def test_dedupe_str_ids_deduplicated_by_id():
    """F34/F44 — 동일 REF id는 id 기준으로 중복 제거."""
    kept, removed = dedupe_refs(["REF-001", "REF-001", "REF-002"])
    assert len(kept) == 2
    assert removed == 1


def test_dedupe_mixed_str_and_dict():
    """F34/F44 — str·dict 혼재 입력도 안전 처리."""
    kept, removed = dedupe_refs(["REF-001", {"id": "REF-002", "url": "http://x", "title": "t"}])
    assert len(kept) == 2


def test_dedupe_dict_url_still_works():
    """회귀 — 기존 dict(url) 기반 중복 제거 동작 유지."""
    kept, removed = dedupe_refs([
        {"url": "http://x/a", "title": "title one here long"},
        {"url": "http://x/a", "title": "title one here long"},
    ])
    assert len(kept) == 1
    assert removed == 1


# ── F54·F57·F60·F77: 라운드 산출 꼴 정규화 · 무음 손실 금지 ──


def _w(d, name, obj):
    (d / name).write_text(_json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_ref_ids_used_schema_is_merged(tmp_path):
    _w(tmp_path, "research_round_A.json", {"refs_found": ["REF-001", "REF-002"]})
    _w(tmp_path, "research_round_B.json", {"ref_ids_used": ["REF-003"], "total_refs": 1})
    r = merge_research(tmp_path)
    assert r["total_after_dedup"] == 3
    assert r["warnings"] == []


def test_nested_rounds_are_flattened(tmp_path):
    _w(tmp_path, "research_round_A.json",
       {"rounds": [{"refs_found": ["REF-001"]}, {"refs_found": ["REF-002"]}]})
    assert merge_research(tmp_path)["total_after_dedup"] == 2


def test_refs_found_int_is_count_not_list(tmp_path):
    _w(tmp_path, "research_round_A.json", {"refs_found": 45, "new_refs": 12})
    _w(tmp_path, "research_round_B.json", {"refs_found": ["REF-010"]})
    r = merge_research(tmp_path)
    assert r["empty_files"] == ["research_round_A.json"]
    assert r["total_after_dedup"] == 1


def test_main_exit_3_when_a_file_is_empty(tmp_path, monkeypatch):
    _w(tmp_path, "research_round_A.json", {"refs_found": 45})
    _w(tmp_path, "research_round_B.json", {"refs_found": ["REF-010"]})
    out = tmp_path / "merged.json"
    monkeypatch.setattr(_sys, "argv", ["merge_research", "-i", str(tmp_path), "-o", str(out)])
    assert _merge_main() == 3
    assert out.exists()


def test_keyref_crosscheck_reports_missing(tmp_path):
    kr = tmp_path / "KeyRef"
    kr.mkdir()
    for i in (1, 2, 3):
        (kr / f"REF-00{i}.md").write_text(f"---\nid: REF-00{i}\n---\n본문\n", encoding="utf-8")
    _w(tmp_path, "research_round_A.json", {"refs_found": ["REF-001", "REF-002"]})
    r = merge_research(tmp_path, keyref_dir=kr)
    assert r["keyref_crosscheck"]["missing_in_merge"] == ["REF-003"]
    assert r["warnings"]


def test_ref_ids_key_is_read(tmp_path):                       # 실데이터 회귀: 실제 라운드 파일의 ref_ids 키
    _w(tmp_path, "research_round_A.json", {"ref_ids": ["REF-001", "REF-002"]})
    r = merge_research(tmp_path)
    assert r["total_after_dedup"] == 2 and r["warnings"] == []


def test_main_warning_survives_cp949_stderr(tmp_path, monkeypatch):
    # F53 계열: WARN이 stderr로 나갈 때 cp949 콘솔에서 UnicodeEncodeError가 나면 안 된다
    import io
    _w(tmp_path, "research_round_A.json", {"refs_found": 45})
    raw = io.BytesIO()
    monkeypatch.setattr(_sys, "stderr", io.TextIOWrapper(raw, encoding="cp949"))
    monkeypatch.setattr(_sys, "argv", ["merge_research", "-i", str(tmp_path),
                                       "-o", str(tmp_path / "m.json")])
    assert _merge_main() == 3
