"""qc 엔진 — 판정 4값과 집행 수준 5종, 대상 0 판정, 결과 JSON (v1.11 — F85·F86·F104).

- 판정: 끔·구현 없음 → skip / 대상 0 → no-target(문서 종류가 「있어야 함」이면 fail) /
  지적 있음 → fail / 없음 → pass.
- 수준: 막음(fail이면 종료 코드 1) · 경고 · 기록만 · 시범(합계 밖) · 구조.
- 입력이 비면 게이트를 돌리지 않고 종료 코드 2 — 「대상 없음은 통과가 아니다」.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable

from techdoc_core import __version__
from techdoc_core.bundles.schema import GateSpec
from techdoc_core.qc.config import ProjectConfig
from techdoc_core.qc.model import DocModel

_TOTAL_KEY = {"막음": "blocking_total", "구조": "blocking_total", "경고": "warning_total",
              "기록만": "record_total", "시범": "pilot_total"}
_MARK = {"pass": "✓ 통과", "no-target": "— 대상 없음", "skip": "끔"}
_FAIL_MARK = {"막음": "✗ 막음", "구조": "✗ 막음", "경고": "! 경고", "기록만": "○ 기록만",
              "시범": "△ 시범"}


def _natural(gid: str) -> tuple:
    return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", gid))


def run_selftests(funcs: dict[str, Callable]) -> list[str]:
    """게이트마다 표본의 지적 수가 기대와 같은지. 어긋난 것을 문장으로."""
    errs: list[str] = []
    for gid in sorted(funcs, key=_natural):
        for i, s in enumerate(getattr(funcs[gid], "samples", []), 1):
            got = len(funcs[gid](s.model).findings)
            if got != s.expect:
                errs.append(f"{gid}: 표본 {i} 기대 {s.expect} 실제 {got}")
    return errs


def _config_hash(cfg: ProjectConfig) -> str:
    payload = json.dumps({"kind": cfg.kind, "numbering": cfg.numbering, "off": cfg.gates_off,
                          "exempt": cfg.exempt, "level": cfg.level_overrides, "extra": cfg.extra},
                         ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _expected(spec: GateSpec, kind: str) -> bool:
    return spec.expects.get(kind, "").replace(" ", "") == ">=1"


def _exempted(gid: str, loc: str, exempt: dict[str, list[str]]) -> bool:
    return any(gid in gates and loc.startswith(f"{cid}:") for cid, gates in exempt.items())


def run_qc(model: DocModel, specs: dict[str, GateSpec], funcs: dict[str, Callable],
           cfg: ProjectConfig) -> dict:
    summary = {"pass": 0, "fail": 0, "no-target": 0, "skip": 0, "blocking_total": 0,
               "warning_total": 0, "record_total": 0, "pilot_total": 0}
    report = {"schema": "techdoc-qc/1", "plugin": __version__, "root": str(model.root),
              "kind": model.kind, "config_hash": _config_hash(cfg),
              "warnings": list(cfg.warnings) + list(model.load_errors),
              "selftest_errors": [], "gate_errors": [], "input_empty": False,
              "summary": summary, "results": []}
    if model.is_empty():
        report["input_empty"] = True
        report["warnings"].insert(0, "입력 없음 — 카드·렌더 트리를 찾지 못함: "
                                     f"{cfg.paths.cards} · {cfg.paths.render_tree}")
        if (cfg.paths.cards.parent / "writer_state.json").exists():
            report["warnings"].insert(1, "이 폴더는 standard 모드 산출물(writer_state.json)이다 — "
                                         "v1.11-a qc는 self-model 카드(cards/*_card.json)·렌더 트리만 "
                                         "읽는다. standard 모드 어댑터는 v1.11-c에서 들어온다")
        return report

    for gid in sorted(specs, key=_natural):
        spec = specs[gid]
        level = cfg.level_overrides.get(gid, spec.level)
        row = {"gate": gid, "title": spec.title, "rules": list(spec.rules), "layer": spec.layer,
               "core": list(spec.core), "level": level, "verdict": "", "reason": "",
               "targets_read": 0, "count": 0, "items": []}
        fn = funcs.get(gid)
        if gid in cfg.gates_off:
            row.update(verdict="skip", reason="설정으로 끔")
        elif fn is None:
            row.update(verdict="skip", reason="구현 없음")
        else:
            try:
                out = fn(model)
            except Exception as e:  # 게이트 하나의 결함이 실행 전체를 죽이지 않게
                msg = f"{gid}: {type(e).__name__}: {e}"
                report["gate_errors"].append(msg)
                row.update(verdict="skip", reason=f"게이트 오류 — {type(e).__name__}")
                summary["skip"] += 1
                report["results"].append(row)
                continue
            items = [f for f in out.findings if not _exempted(gid, f.loc, model.exempt)]
            row["targets_read"] = out.targets_read
            row["count"] = len(items)
            row["items"] = [{"loc": f.loc, "msg": f.msg} for f in items]
            if out.targets_read == 0 and not items:
                if _expected(spec, model.kind):
                    row.update(verdict="fail", count=1,
                               reason=f"있어야 할 대상이 없음({model.kind})")
                else:
                    row["verdict"] = "no-target"
            else:
                row["verdict"] = "fail" if items else "pass"
        summary[row["verdict"]] += 1
        if row["verdict"] == "fail":
            summary[_TOTAL_KEY[level]] += row["count"]
        report["results"].append(row)
    return report


def exit_code(report: dict) -> int:
    """0 통과 · 1 막음 수준 fail · 2 입력 없음 · 3 자기검사 실패·게이트 오류."""
    if report.get("selftest_errors") or report.get("gate_errors"):
        return 3
    if report.get("input_empty"):
        return 2
    return 1 if report["summary"]["blocking_total"] > 0 else 0


def format_report(report: dict, top: int = 8) -> str:
    """사람이 읽는 표 — 시리즈 check_v2와 같은 열(ID·검사·대상·건수·상태)."""
    lines = [f"[qc] {report['root']} · kind={report['kind']} · plugin {report['plugin']}"]
    lines += [f"  [WARN] {w}" for w in report["warnings"]]
    lines += [f"  [SELFTEST] {e}" for e in report.get("selftest_errors", [])]
    lines += [f"  [GATE ERROR] {e}" for e in report.get("gate_errors", [])]
    lines.append(f"{'ID':<8}{'검사':<34}{'대상':>6}{'건수':>7}  상태")
    for r in report["results"]:
        mark = _FAIL_MARK[r["level"]] if r["verdict"] == "fail" else _MARK[r["verdict"]]
        if r["reason"]:
            mark += f" ({r['reason']})"
        lines.append(f"{r['gate']:<8}{r['title'][:32]:<34}{r['targets_read']:>6}"
                     f"{r['count']:>7}  {mark}")
    s = report["summary"]
    lines.append(f"막음 {s['blocking_total']} · 경고 {s['warning_total']} · "
                 f"기록만 {s['record_total']} · 시범 {s['pilot_total']} "
                 f"(pass {s['pass']} / fail {s['fail']} / 대상 없음 {s['no-target']} / "
                 f"skip {s['skip']})")
    for r in report["results"]:
        if r["verdict"] == "fail":
            lines += [f"  {r['gate']}  {it['loc']}  {it['msg']}" for it in r["items"][:top]]
    return "\n".join(lines)
