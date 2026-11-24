"""/techdoc-qc CLI (v1.11-a — F85)."""
import io
import json
import sys

from scripts.qc import main as qc_main


def _project(tmp_path, body="근거[REF-001]. 또[REF-002].", refs=("REF-001",)):
    cards = tmp_path / "output" / "cards"
    cards.mkdir(parents=True)
    (cards / "1.1_card.json").write_text(
        json.dumps({"sections": {"s": {"body": body}}}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "output" / "reference_list.json").write_text(
        json.dumps({"refs": [{"id": r, "authors": ["Kim, H."]} for r in refs]}),
        encoding="utf-8")
    return tmp_path


def test_cli_selftest_ok(tmp_path):
    assert qc_main(["--selftest", str(tmp_path)]) == 0


def test_cli_writes_json_and_exit_code(tmp_path):
    root = _project(tmp_path)
    assert qc_main([str(root)]) == 1
    rep = json.loads((root / "output" / "qc_report.json").read_text(encoding="utf-8"))
    assert rep["summary"]["blocking_total"] == 1
    assert {r["gate"] for r in rep["results"]} == {"V8", "V13", "V45", "V68"}


def test_cli_clean_project_exit_0(tmp_path):
    root = _project(tmp_path, body="근거[REF-001].")
    out = tmp_path / "x.json"
    assert qc_main([str(root), "--json", str(out)]) == 0 and out.exists()


def test_cli_gates_filter(tmp_path):
    root = _project(tmp_path)
    assert qc_main([str(root), "--gates", "V45"]) == 0
    rep = json.loads((root / "output" / "qc_report.json").read_text(encoding="utf-8"))
    assert [r["gate"] for r in rep["results"]] == ["V45"]


def test_cli_empty_project_exit_2(tmp_path):
    assert qc_main([str(tmp_path)]) == 2


def test_cli_cp949_stderr_and_stdout(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp949"))
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp949"))
    assert qc_main([str(root)]) == 1
