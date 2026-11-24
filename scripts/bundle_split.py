"""규칙 대장 → 층별 묶음 (v1.11-a, 설계 D2). LLM 호출 0회.

시리즈 규칙 대장(rules.yaml, 평면 리스트)을 layer로 나눠 core·kind·domain·series 묶음을 만들고,
규칙↔게이트 연결을 점검한 보고서를 낸다.
- 정본 연결은 규칙 쪽 `enforce[].gate` 하나다(게이트 쪽 rule_ref는 옛 번호라 쓰지 않음).
- `status: 대체됨` 규칙은 묶음에서 빼고 목록으로만 남긴다.
- 본체 규칙 본문에 분야 낱말이 남았는지 찾는다(본체는 분야를 가정하지 않는다 — E12).
- 본체 규칙 가운데 수치·관례가 든 것(숫자+단위·개수 범위·특정 표식)을 목록으로 낸다(E18 9).
- 판정 매핑(`--public-map`)을 주면 본체 규칙을 판정대로 옮기거나 문구를 바꿔 공개판을 만든다(E15).

산출 위치는 호출자가 정한다. 묶음(`--out`)은 private 쪽, 공개판(`--public-out`)만 플러그인으로.

사용법:
    python -m scripts.bundle_split <rules.yaml> --gates <gates.yaml> --out <dir> \
        [--domain-words <txt> ...] [--public-map <map.yaml> --public-out <rules.yaml>]
    python -m scripts.bundle_split <rules.yaml> --out <dir> --public-map <map.yaml> --fill-hashes
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
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


def _word_found(word: str, text: str) -> bool:
    """낱말이 글에 있나 — `re:` 접두는 정규식(「재배」는 잡되 「재배치」는 빼는 식)."""
    if word.startswith("re:"):
        return re.search(word[3:], text) is not None
    return word in text


def domain_word_hits(rules: list[dict], words: list[str]) -> list[tuple[str, str]]:
    """본체 규칙의 제목·본문에 든 분야 낱말 (id, 낱말). 낱말 앞에 `re:`를 붙이면 정규식."""
    hits: list[tuple[str, str]] = []
    for r in _live(rules):
        if r.get("layer") != "본체":
            continue
        text = f"{r.get('title', '')}\n{r.get('rule', '')}"
        hits += [(r["id"], w) for w in words if w and _word_found(w, text)]
    return hits


# 「수치·관례가 든 본체 규칙」 표식 (E18 9). 규칙 id·게이트 id·단계 이름(Q4-026·V71·S2·R²) 속
# 숫자는 앞 글자 검사로 뺀다. 표식이 든 규칙은 본체인지 문서 종류·분야·시리즈 관례인지 사람이 가른다.
_NUM = r"(?<![A-Za-z\d.\-_²])\d+(?:[.,]\d+)?"
CONVENTION_PATTERNS: dict[str, re.Pattern] = {
    # 숫자 + 단위 — 「36자」「3개」「2쪽」「10%」 (자료·분석·장점처럼 낱말 머리인 경우는 뺀다)
    "num_unit": re.compile(
        _NUM + r"\s*(?:글자|자(?![료리동체연])|줄|쪽|개(?![념발선요])|장(?![점기])|건(?![강물])|"
        r"문장|문단|단어|칸|행(?![정동])|열(?![람])|가지|단계|번째|회(?![의사])|번(?![역호])|배(?![포경치])|"
        r"초(?![안기과])|분(?![석야류량포리])|시간|개월|년|주(?![의제석요])|일(?![반관부치])|"
        r"편(?![집지])|권(?![한장리])|%|\N{FULLWIDTH PERCENT SIGN}|px|pt|mm|cm|dpi|KB|MB)"),
    # 고유어 수 + 단위 — 「일곱 가지」「두 벌」「세 줄」 (「한 ~」은 너무 흔해 뺀다)
    "num_word": re.compile(
        r"(?<![가-힣])(?:두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s?"
        r"(?:가지|개|줄|문장|문단|단계|쪽|칸|번|벌|장|갈래|단|층)"
        r"(?:(?![가-힣])|(?=[은는이가을를의에로와과도만씩]))"),
    # 개수 범위·한계 — 「3~5」「40자 이하」「120 안팎」
    "range": re.compile(
        _NUM + r"\s*[~\N{TILDE OPERATOR}]\s*\d+|" + _NUM +
        r"\s*[가-힣%]{0,2}\s*(?:이상|이하|안팎|미만|초과|내외|남짓|넘지|넘게|까지)"),
    # 특정 표식 — 시리즈 설계 토큰(tok.*)·파일·스크립트 이름·고정 기호
    "marker": re.compile(
        r"\btok\.[A-Za-z_][\w.]*|[\w-]+\.(?:py|ya?ml|json|md|css|js)\b|[※★☆■□▶◆●○◎①-⑳]"),
}


def convention_hits(rules: list[dict]) -> list[dict]:
    """본체 규칙의 제목·본문에서 수치·관례 표식을 찾는다 → [{"id", "kinds", "matches"}].

    kinds는 CONVENTION_PATTERNS 키(num_unit·num_word·range·marker) 가운데 걸린 것,
    matches는 걸린 글자 그대로(중복 제거, 나온 순서). 판정은 하지 않는다 — 목록만 낸다.
    """
    out: list[dict] = []
    for r in _live(rules):
        if r.get("layer") != "본체":
            continue
        texts = (str(r.get("title", "")), str(r.get("rule", "")))  # 제목·본문을 잇지 않는다(줄 넘어 걸림 방지)
        kinds: list[str] = []
        matches: list[str] = []
        for kind, pat in CONVENTION_PATTERNS.items():
            found = [m.group(0).strip() for t in texts for m in pat.finditer(t)]
            if found:
                kinds.append(kind)
                matches += [f for f in found if f not in matches]
        if kinds:
            out.append({"id": r["id"], "kinds": kinds, "matches": matches})
    return out


# ── 본체 규칙 공개판 (v1.11-c, E15·E18 9) ────────────────────────────────────────
# 판정 매핑(private, `regression/bundles/core_public_map.yaml`)을 대장 본체 규칙에 적용해
# 플러그인 `bundles/core/rules.yaml`(public)을 만든다. 대장 원문은 바꾸지 않는다.
#   keep    — 그대로 공개(수치가 예시·토큰 참조·외부 표준 이름일 뿐인 경우)
#   reword  — 플러그인 판 문구로 공개(`rule`, 필요하면 `title`) — 분야 낱말·시리즈 흔적만 걷음
#   kind / domain / series — 아래 층으로 옮김(공개하지 않음, private 묶음에 붙음)
MAP_SCHEMA = "techdoc-core-public-map/1"
MOVE_LAYER = {"kind": "문서종류", "domain": "분야", "series": "시리즈"}
ACTIONS = {"keep", "reword", *MOVE_LAYER}
# 공개판에 싣는 필드 — 별칭·출처·결정자·메모·예외·관계(옛 번호)는 시리즈 대장 내부 기록이라 뺀다
PUBLIC_FIELDS = ("id", "title", "rule", "core", "area", "layer", "status", "enforce")


class PublicMapError(ValueError):
    """공개 매핑이 대장과 맞지 않음(판정 누락·원문 바뀜·모르는 id·모르는 action)."""


def wording_hash(rule: dict) -> str:
    """원문 지문 — 제목·본문 sha256 앞 16자. 대장 원문이 바뀌면 판정을 다시 해야 한다."""
    text = f"{rule.get('title', '')}\n{rule.get('rule', '')}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def public_rule(rule: dict) -> dict:
    """대장 행 → 공개 행. status 괄호 메모를 떼고, enforce는 게이트 연결({gate, level})만 남긴다."""
    out = {k: rule[k] for k in PUBLIC_FIELDS if k in rule}
    out["status"] = str(rule.get("status", "")).split("(")[0].strip()
    out["enforce"] = [{"gate": e["gate"], "level": e.get("level", "")}
                      for e in rule.get("enforce") or [] if isinstance(e, dict) and e.get("gate")]
    return out


def read_public_map(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("schema") != MAP_SCHEMA:
        raise PublicMapError(f"{path}: schema는 {MAP_SCHEMA!r}여야 함")
    return data


def fill_map_hashes(mapping: dict, rules: list[dict]) -> int:
    """hash가 빈 매핑 항목에 지금 원문 지문을 채운다 → 채운 수. 이미 있는 hash는 건드리지 않는다."""
    by_id = {r["id"]: r for r in rules}
    n = 0
    for rid, entry in (mapping.get("rules") or {}).items():
        if rid in by_id and not entry.get("hash"):
            entry["hash"] = wording_hash(by_id[rid])
            n += 1
    return n


def apply_public_map(core: list[dict], mapping: dict, must_judge: set[str]) -> dict:
    """본체 규칙 + 판정 매핑 → {"public", "moved": {kind·domain·series: [행]}, "reworded", "kept"}.

    must_judge(수치·관례 표식·분야 낱말이 걸린 id)는 모두 판정이 있어야 한다. 매핑의 hash가
    지금 원문과 다르면 판정이 낡은 것이라 멈춘다. 옮긴 행은 layer를 바꾸고 `moved_from: 본체`를 단다.
    """
    entries = mapping.get("rules") or {}
    by_id = {r["id"]: r for r in core}
    errors: list[str] = []
    errors += [f"{rid}: 판정 없음" for rid in sorted(must_judge - set(entries)) if rid in by_id]
    errors += [f"{rid}: 본체 규칙에 없음" for rid in sorted(set(entries) - set(by_id))]
    for rid, e in sorted(entries.items()):
        if rid not in by_id:
            continue
        if e.get("action") not in ACTIONS:
            errors.append(f"{rid}: 모르는 action {e.get('action')!r}")
        elif e.get("hash") != wording_hash(by_id[rid]):
            errors.append(f"{rid}: 원문이 바뀜(hash {e.get('hash')} ≠ {wording_hash(by_id[rid])})"
                          " — 다시 판정")
        elif e["action"] == "reword" and not e.get("rule"):
            errors.append(f"{rid}: reword에는 rule(플러그인 판 문구)이 필요")
        elif not e.get("reason"):
            errors.append(f"{rid}: reason 없음")
    if errors:
        raise PublicMapError("공개 매핑 오류:\n  " + "\n  ".join(errors))
    out: dict = {"public": [], "moved": {k: [] for k in MOVE_LAYER}, "reworded": [], "kept": []}
    for r in core:
        e = entries.get(r["id"]) or {"action": "keep"}
        act = e["action"]
        if act in MOVE_LAYER:
            moved = {**r, "layer": MOVE_LAYER[act], "moved_from": "본체", "move_reason": e["reason"]}
            if e.get("to"):
                moved["moved_kind"] = e["to"]
            out["moved"][act].append(moved)
            continue
        row = public_rule(r)
        if act == "reword":
            row["title"] = e.get("title") or row["title"]
            row["rule"] = e["rule"]
            row["edition"] = "플러그인 판 문구"  # 시리즈 대장 원문과 다름 — 차이는 매핑 파일에
            out["reworded"].append(r["id"])
        elif r["id"] in entries:
            out["kept"].append(r["id"])
        out["public"].append(row)
    return out


def gate_rules_not_public(gates: list[dict], public_ids: set[str]) -> dict[str, list[str]]:
    """게이트 `rules:`에 있으나 공개 본체 규칙에 없는 id — 아래 층 규칙은 `lower_rules:`로 옮겨야 한다."""
    out: dict[str, list[str]] = {}
    for g in gates:
        bad = [rid for rid in g.get("rules") or [] if rid not in public_ids]
        if bad:
            out[str(g["id"])] = bad
    return out


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
    ap.add_argument("--domain-words", action="append", default=[],
                    help="분야 낱말 목록(여러 번 줄 수 있음, `re:` 접두는 정규식)")
    ap.add_argument("--public-map", help="본체 공개 판정 매핑 yaml(private)")
    ap.add_argument("--public-out", help="공개 본체 규칙 yaml 경로(플러그인 bundles/core/rules.yaml)")
    ap.add_argument("--core-gates", help="플러그인 본체 gates.yaml — rules: id가 공개판에 있는지 대조")
    ap.add_argument("--fill-hashes", action="store_true",
                    help="매핑에서 hash가 빈 항목을 지금 원문 지문으로 채워 저장하고 끝냄")
    args = ap.parse_args()

    rules = yaml.safe_load(Path(args.rules).read_text(encoding="utf-8")) or []
    gates: list[dict] = []
    if args.gates:
        gates = [g for g in yaml.safe_load(Path(args.gates).read_text(encoding="utf-8")) or []
                 if isinstance(g, dict)]
    gate_ids = {str(g["id"]) for g in gates}
    if args.fill_hashes:
        if not args.public_map:
            ap.error("--fill-hashes에는 --public-map이 필요")
        mp = Path(args.public_map)
        mapping = read_public_map(mp)
        n = fill_map_hashes(mapping, rules)
        mp.write_text(yaml.safe_dump(mapping, allow_unicode=True, sort_keys=False, width=1000),
                      encoding="utf-8")
        print(f"hash {n}건 채움 → {mp}")
        return 0
    out = Path(args.out)
    parts = split_rules(rules)
    words: list[str] = []
    for w in args.domain_words:
        words += _read_words(Path(w))
    report = split_report(rules, gate_ids)
    report["domain_word_hits"] = [list(h) for h in domain_word_hits(rules, words)]
    report["convention_rules"] = convention_hits(rules)
    report["gate_rule_index"] = gate_rule_index(rules)
    if args.public_map:
        must = {h[0] for h in report["domain_word_hits"]} | \
            {h["id"] for h in report["convention_rules"]}
        try:
            pub = apply_public_map(parts["core"], read_public_map(Path(args.public_map)), must)
        except PublicMapError as e:
            print(e, file=sys.stderr)
            return 1
        core_gates = [g for g in yaml.safe_load(Path(args.core_gates).read_text(
            encoding="utf-8")) or [] if isinstance(g, dict)] if args.core_gates else []
        moved_ids = {r["id"] for rows in pub["moved"].values() for r in rows}
        parts["core"] = [r for r in parts["core"] if r["id"] not in moved_ids]
        for key, rows in pub["moved"].items():
            parts[key] = parts[key] + rows
        report["public"] = {
            "public": len(pub["public"]), "reworded": pub["reworded"],
            "kept_after_review": pub["kept"],
            "moved": {k: [r["id"] for r in v] for k, v in pub["moved"].items()},
            "gate_rules_not_public": gate_rules_not_public(
                core_gates, {r["id"] for r in pub["public"]})}
        if args.public_out:
            po = Path(args.public_out)
            po.parent.mkdir(parents=True, exist_ok=True)
            po.write_text(
                "# 본체 규칙 묶음(공개판) — 생성물, 손으로 고치지 않는다 (v1.11-c, E15).\n"
                "# 시리즈 규칙 대장의 본체 규칙에서 문서 종류·분야·시리즈 관례를 아래 층으로 옮기고\n"
                "# 분야 낱말을 걷은 플러그인 판 문구(edition)로 냈다. 생성: scripts.bundle_split --public-map\n"
                + yaml.safe_dump(pub["public"], allow_unicode=True, sort_keys=False, width=1000),
                encoding="utf-8")
    for key in LAYER_KEY.values():
        (out / key).mkdir(parents=True, exist_ok=True)
        (out / key / "rules.yaml").write_text(
            yaml.safe_dump(parts[key], allow_unicode=True, sort_keys=False), encoding="utf-8")
    (out / "split_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {out} — {report['counts']}")
    print(f"  규칙이 부르지 않는 게이트 {len(report['unreferenced_gates'])} · "
          f"막음인데 게이트 없는 규칙 {len(report['blocking_rules_without_gate'])} · "
          f"집행 없음 {len(report['no_enforce'])} · 본체 분야 낱말 {len(report['domain_word_hits'])} · "
          f"수치·관례 표식 {len(report['convention_rules'])}")
    if "public" in report:
        p = report["public"]
        print(f"  공개 본체 {p['public']} · 문구 바꿈 {len(p['reworded'])} · 옮김 "
              + " · ".join(f"{k} {len(v)}" for k, v in p["moved"].items())
              + f" · 게이트 rules 중 공개판 밖 {sum(map(len, p['gate_rules_not_public'].values()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
