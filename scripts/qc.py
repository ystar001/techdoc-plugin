"""`/techdoc-qc` — 렌더 트리·카드 경로만 받아 게이트를 돌린다 (v1.11 — F85·F86·F104).

결과마다 규칙 번호·층·핵심 규칙·대상 수·판정(pass·fail·no-target·skip)·집행 수준을 단다.
설정은 `<project>/techdoc.project.yaml`(없으면 기본값). LLM 호출 0회.

사용법:
    python -m scripts.qc <project_root> [--config <yaml>] [--json <out.json>]
                         [--gates V8,V13] [--selftest] [--all]

종료 코드: 0 통과 · 1 막음 수준 실패 · 2 입력 없음 · 3 자기검사 실패.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.bundles.loader import load_gate_specs
from techdoc_core.qc.adapters import build_model
from techdoc_core.qc.config import layer_dirs, load_config, validate_gate_ids
from techdoc_core.qc.engine import exit_code, format_report, run_qc, run_selftests
from techdoc_core.qc.registry import REGISTRY


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="TechDoc 품질 게이트 (/techdoc-qc)")
    ap.add_argument("root", help="프로젝트 루트")
    ap.add_argument("--config", help="techdoc.project.yaml 경로 (기본: <root>/techdoc.project.yaml)")
    ap.add_argument("--json", help="결과 JSON 경로 (기본: 카드 폴더의 부모/qc_report.json)")
    ap.add_argument("--gates", help="이 게이트만 (쉼표 구분)")
    ap.add_argument("--selftest", action="store_true", help="게이트 자기검사만")
    ap.add_argument("--all", action="store_true", help="지적을 게이트마다 전부 출력")
    args = ap.parse_args(argv)

    funcs = dict(REGISTRY)
    errors = run_selftests(funcs)
    if args.selftest:
        for e in errors:
            print(f"[SELFTEST] {e}")
        print(f"자기검사 {'실패 ' + str(len(errors)) + '건' if errors else '통과'} — 게이트 {len(funcs)}개")
        return 3 if errors else 0

    root = Path(args.root)
    cfg = load_config(root, Path(args.config) if args.config else None)
    specs = load_gate_specs(layer_dirs(cfg))
    validate_gate_ids(cfg, set(specs))
    if args.gates:
        wanted = [g.strip() for g in args.gates.split(",") if g.strip()]
        unknown = [g for g in wanted if g not in specs]
        cfg.warnings += [f"모르는 게이트 id: {g}" for g in unknown]
        specs = {g: specs[g] for g in wanted if g in specs}
    report = run_qc(build_model(root, cfg), specs, funcs, cfg)
    report["selftest_errors"] = errors

    out = Path(args.json) if args.json else cfg.paths.cards.parent / "qc_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(format_report(report, top=10**9 if args.all else 8))
    print(f"→ {out}")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
