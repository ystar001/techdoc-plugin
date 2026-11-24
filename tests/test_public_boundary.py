"""check_public_boundary — 공개 레포에 비공개 낱말이 새지 않게 (v1.11-a, 설계 D1·E12)."""
import sys

from scripts.check_public_boundary import main as boundary_main
from scripts.check_public_boundary import scan


def _tree(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n# 비공개낱말 언급\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.md").write_text("깨끗\n", encoding="utf-8")
    (tmp_path / "pkg" / "c.png").write_bytes(b"\x89PNG" + "비공개낱말".encode())
    return tmp_path / "pkg"


def test_boundary_scan_new_hit(tmp_path):
    root = _tree(tmp_path)
    assert scan(root, ["비공개낱말"], set()) == [("a.py: 비공개낱말: # 비공개낱말 언급", 2)]


def test_boundary_baseline_suppresses_known(tmp_path):
    root = _tree(tmp_path)
    assert scan(root, ["비공개낱말"], {"a.py: 비공개낱말: # 비공개낱말 언급"}) == []


def test_boundary_main_exit_codes(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    words = tmp_path / "words.txt"
    words.write_text("# 주석\n비공개낱말\n\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root), "--words", str(words)])
    assert boundary_main() == 1
    base = tmp_path / "base.txt"
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root), "--words", str(words),
                                      "--baseline", str(base), "--write-baseline"])
    assert boundary_main() == 0
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root), "--words", str(words),
                                      "--baseline", str(base)])
    assert boundary_main() == 0


def test_baseline_survives_line_shift(tmp_path):
    root = _tree(tmp_path)
    base = {k for k, _ in scan(root, ["비공개낱말"], set())}
    (root / "a.py").write_text("새 줄\n새 줄\nx = 1\n# 비공개낱말 언급\n", encoding="utf-8")
    assert scan(root, ["비공개낱말"], base) == []
    (root / "a.py").write_text("x = 1\n# 비공개낱말 언급\n# 비공개낱말 새 언급\n", encoding="utf-8")
    assert len(scan(root, ["비공개낱말"], base)) == 1


def test_boundary_missing_word_list_exit_2(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(root), "--words", str(tmp_path / "없음.txt")])
    assert boundary_main() == 2
