"""규칙 대장 → 층별 묶음 (v1.11-a, 설계 D2). LLM 호출 0회.

시리즈 규칙 대장(rules.yaml, 평면 리스트)을 layer로 나눠 core·kind·domain·series 묶음을 만들고,
규칙↔게이트 연결을 점검한 보고서를 낸다.
- 정본 연결은 규칙 쪽 `enforce[].gate` 하나다(게이트 쪽 rule_ref는 옛 번호라 쓰지 않음).
- `status: 대체됨` 규칙은 묶음에서 빼고 목록으로만 남긴다.
- 본체 규칙 본문에 분야 낱말이 남았는지 찾는다(본체는 분야를 가정하지 않는다 — E12).

산출 위치는 호출자가 정한다. 본체 규칙 본문은 문구 검토 전까지 private 쪽에 둔다(E15).

사용법:
    python -m scripts.bundle_split <rules.yaml> --gates <gates.yaml> --out <dir> \
        [--domain-words <txt>]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from pathlib import Path

import yaml

LAYER_KEY = {"본체": "core", "문서종류": "kind", "분야": "domain", "시리즈": "series"}
SUPERSEDED = "대체됨"
_RANGE = re.compile(r"^([A-Z]+)(\d+)~[A-Z]*(\d+)$")


def _live(rules: list[dict]) -> list[dict]:
    return [r for r in rules if r.get("status") != SUPERSEDED]


def split_rules(rules: list[dict]) -> dict[str, list]:
    out: dict[str, list] = {k: [] for k in LAYER_KEY.values()}
    out["superseded"] = sorted(r["id"] for r in rules if r.get("status") == SUPERSEDED)
    for r in _live(rules):
        key = LAYER_KEY.get(r.get("layer", ""))
        if key:
            out[key].append(r)
    return out


def _expand(gate: str) -> list[str]:
    m = _RANGE.match(gate.strip())
    if not m:
        return [gate.strip()]
    prefix, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    return [f"{prefix}{i}" for i in range(a, b + 1)]


def gate_rule_index(rules: list[dict]) -> dict[str, list[str]]:
    """게이트 id → 그 게이트로 집행되는 규칙 id 목록(대체된 규칙 제외)."""
    idx: dict[str, list[str]] = {}
    for r in _live(rules):
        for e in r.get("enforce") or []:
            if isinstance(e, dict) and e.get("gate"):
                for g in _expand(str(e["gate"])):
                    idx.setdefault(g, [])
                    if r["id"] not in idx[g]:
                        idx[g].append(r["id"])
    return idx


def split_report(rules: list[dict], gate_ids: set[str]) -> dict:
    live = _live(rules)
    idx = gate_rule_index(rules)
    parts = split_rules(rules)
    blocking_wo_gate = sorted(
        r["id"] for r in live
        if any(isinstance(e, dict) and e.get("level") == "막음" for e in r.get("enforce") or [])
        and not any(isinstance(e, dict) and e.get("gate") for e in r.get("enforce") or []))
    return {
        "unreferenced_gates": sorted(g for g in gate_ids if g not in idx),
        "unknown_gates_in_rules": sorted(g for g in idx if gate_ids and g not in gate_ids),
        "blocking_rules_without_gate": blocking_wo_gate,
        "no_enforce": sorted(r["id"] for r in live if not r.get("enforce")),
        "counts": {k: len(v) for k, v in parts.items()},
    }


def domain_word_hits(rules: list[dict], words: list[str]) -> list[tuple[str, str]]:
    """본체 규칙의 제목·본문에 든 분야 낱말 (id, 낱말)."""
    hits: list[tuple[str, str]] = []
    for r in _live(rules):
        if r.get("layer") != "본체":
            continue
        text = f"{r.get('title', '')}\n{r.get('rule', '')}"
        hits += [(r["id"], w) for w in words if w and w in text]
    return hits


def _read_words(path: Path | None) -> list[str]:
    if not path or not path.is_file():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="규칙 대장 → 층별 묶음")
    ap.add_argument("rules")
    ap.add_argument("--gates", help="게이트 정의 yaml(id 목록만 씀)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--domain-words")
    args = ap.parse_args()

    rules = yaml.safe_load(Path(args.rules).read_text(encoding="utf-8")) or []
    gate_ids: set[str] = set()
    if args.gates:
        gate_ids = {str(g["id"]) for g in yaml.safe_load(
            Path(args.gates).read_text(encoding="utf-8")) or [] if isinstance(g, dict)}
    out = Path(args.out)
    parts = split_rules(rules)
    for key in LAYER_KEY.values():
        (out / key).mkdir(parents=True, exist_ok=True)
        (out / key / "rules.yaml").write_text(
            yaml.safe_dump(parts[key], allow_unicode=True, sort_keys=False), encoding="utf-8")
    report = split_report(rules, gate_ids)
    words = _read_words(Path(args.domain_words) if args.domain_words else None)
    report["domain_word_hits"] = [list(h) for h in domain_word_hits(rules, words)]
    report["gate_rule_index"] = gate_rule_index(rules)
    (out / "split_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {out} — {report['counts']}")
    print(f"  규칙이 부르지 않는 게이트 {len(report['unreferenced_gates'])} · "
          f"막음인데 게이트 없는 규칙 {len(report['blocking_rules_without_gate'])} · "
          f"집행 없음 {len(report['no_enforce'])} · 본체 분야 낱말 {len(report['domain_word_hits'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
