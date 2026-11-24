"""KeyRef 중복 정리 — 후보 보고·필드 단위 병합·이월 보고·안전 재번호 (v1.10.2 — F63·F72).

병렬 researcher가 같은 출처를 서로 다른 REF로 만든다. 이 도구는:
- `--report`(기본): 중복 **후보만** 표로 낸다. URL이 같아도 다른 문헌(기관 랜딩 페이지)일
  수 있어 자동 병합하지 않는다.
- `--apply --pairs <pairs.json>`: 사람이 확정한 쌍만 병합한다. `key_numbers`·
  `related_sections`는 합집합, 제목·저자·연도·URL은 정본(번호가 작은 쪽) 값을 지킨다.
  별칭 파일은 `KeyRef_dup/`로 옮기고 `ref_alias_map.json`을 갱신한다.
- `--cards <dir>`(apply와 함께): 카드 문자열의 단독 `REF-NNN`만 정본 번호로 바꾼다.
  범위·목록 꼴(`REF-205~208`, `REF-136~144·207`)에 걸린 별칭은 바꾸지 않고 수동 목록으로.
- `--check`: 별칭의 `key_numbers`가 정본에 모두 있는지 본다(고아 수치).

종료 코드: 0 · 1 입력 없음 · 3 경고(수동 목록·고아 수치). LLM 호출 0회.

사용법:
    python -m scripts.dedupe_keyref ./output/KeyRef --report
    python -m scripts.dedupe_keyref ./output/KeyRef --apply --pairs pairs.json --cards ./output/cards
    python -m scripts.dedupe_keyref ./output/KeyRef --check
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import shutil
import sys
from pathlib import Path

import yaml
from rapidfuzz import fuzz

from scripts.merge_research import url_canonical

TITLE_SIMILARITY_THRESHOLD = 90
_MIN_TITLE_LEN = 10
_FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
# 범위·목록 꼴: REF-205~208 · REF-136~144·194·104 · REF-1, 2
_GROUP_RE = re.compile(r"REF-(\d+)((?:\s*[~·]\s*\d+|\s*,\s*(?!\d{4}(?!\d))\d+)+)")
_TOKEN_RE = re.compile(r"REF-(\d+)(?!\d)")
_UNION_FIELDS = ("key_numbers", "related_sections")
_FILL_FIELDS = ("url", "excerpt", "authors", "institution", "venue")


def _read(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}, text  # 깨진 frontmatter는 건너뜀 — build_reflist와 같은 처리
    return (fm if isinstance(fm, dict) else {}), text[m.end():]


def _write(path: Path, fm: dict, body: str) -> None:
    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
    path.write_text("---\n" + dumped + "---\n" + body, encoding="utf-8")


def _index(keyref_dir: Path) -> dict[str, tuple[Path, dict]]:
    """REF id → (파일, frontmatter). 파일 이름이 아니라 frontmatter id로 찾는다."""
    out: dict[str, tuple[Path, dict]] = {}
    for p in sorted(keyref_dir.glob("*.md")):
        fm, _ = _read(p)
        rid = str(fm.get("id") or "").strip()
        if rid:
            out[rid] = (p, fm)
    return out


def _num(rid: str) -> int:
    m = re.search(r"\d+", rid)
    return int(m.group(0)) if m else 0


def find_candidates(keyref_dir: Path) -> list[dict]:
    """중복 후보 쌍. canonical = 번호가 작은 쪽. 자동 병합하지 않는다."""
    refs = sorted(_index(keyref_dir).items(), key=lambda kv: _num(kv[0]))
    out: list[dict] = []
    for i, (rid_a, (_, fa)) in enumerate(refs):
        for rid_b, (_, fb) in refs[i + 1:]:
            ua, ub = url_canonical(fa.get("url", "")), url_canonical(fb.get("url", ""))
            if ua and ua == ub:
                out.append({"canonical": rid_a, "alias": rid_b, "reason": "url", "score": 100})
                continue
            ta, tb = str(fa.get("title") or ""), str(fb.get("title") or "")
            if len(ta) >= _MIN_TITLE_LEN and len(tb) >= _MIN_TITLE_LEN:
                score = int(fuzz.ratio(ta, tb))
                if score >= TITLE_SIMILARITY_THRESHOLD:
                    out.append({"canonical": rid_a, "alias": rid_b, "reason": "title",
                                "score": score})
    return out


def merge_pair(canonical: dict, alias: dict) -> tuple[dict, dict]:
    """필드 단위 병합 → (병합된 canonical, 이월 보고). 정본의 서지 값은 지킨다(F63 ③)."""
    merged = dict(canonical)
    report: dict = {"canonical": canonical.get("id"), "alias": alias.get("id")}
    for f in _UNION_FIELDS:
        base = list(canonical.get(f) or [])
        added = [x for x in (alias.get(f) or []) if x not in base]
        merged[f] = base + added
        report[f] = len(added)
    filled = False
    for f in _FILL_FIELDS:
        if not canonical.get(f) and alias.get(f):
            merged[f] = alias[f]
            filled = filled or f == "excerpt"
    report["excerpt"] = filled
    return merged, report


def resolve_alias(rid: str, alias_map: dict[str, str]) -> str:
    """별칭 사슬(003→002→001)을 끝점까지 따라간다. 순환이면 멈춘 자리."""
    seen = {rid}
    while rid in alias_map and alias_map[rid] not in seen:
        rid = alias_map[rid]
        seen.add(rid)
    return rid


def rewrite_ref_ids(text: str, alias_map: dict[str, str]) -> tuple[str, list[str]]:
    """단독 REF 토큰만 정본으로 바꾼다. 범위·목록 꼴에 걸린 별칭은 그대로 두고 보고(F63 ⑤)."""
    alias_nums = {_num(a): resolve_alias(a, alias_map) for a in alias_map}
    manual: list[str] = []
    protected: list[tuple[int, int]] = []
    for g in _GROUP_RE.finditer(text):
        nums = {int(g.group(1))}
        prev = int(g.group(1))
        for sep, n in re.findall(r"\s*([~·,])\s*(\d+)", g.group(2)):
            n = int(n)
            nums |= set(range(prev, n + 1)) if sep == "~" else {n}
            prev = n
        protected.append(g.span())
        if nums & alias_nums.keys():
            manual.append(g.group(0))

    def _sub(m: re.Match) -> str:
        if any(s <= m.start() < e for s, e in protected):
            return m.group(0)
        return alias_nums.get(int(m.group(1)), m.group(0))

    return _TOKEN_RE.sub(_sub, text), manual


def _alias_map_path(keyref_dir: Path) -> Path:
    return keyref_dir.parent / "ref_alias_map.json"


def apply_pairs(keyref_dir: Path, pairs: list[dict]) -> list[dict]:
    """확정 쌍 병합 → 이월 보고 목록. 별칭은 KeyRef_dup/로 이동, alias map은 쌍마다 기록.

    후보 표를 그대로 옮긴 경우(001·002·003이 서로 짝지어짐)도 견딘다: 정본은 별칭 사슬의
    끝점으로 풀고, 이미 옮긴 별칭은 건너뛴다. 정본과 별칭이 같으면 거부한다.
    """
    idx = _index(keyref_dir)
    dup_dir = keyref_dir.parent / "KeyRef_dup"
    map_path = _alias_map_path(keyref_dir)
    amap = json.loads(map_path.read_text(encoding="utf-8")) if map_path.exists() else {}
    reports: list[dict] = []
    for pair in pairs:
        a_id = pair["alias"]
        c_id = resolve_alias(pair["canonical"], amap)
        if a_id in amap:
            reports.append({"canonical": c_id, "alias": a_id,
                            "skipped": f"이미 {amap[a_id]}로 병합됨"})
            continue
        if c_id == a_id:
            reports.append({"canonical": c_id, "alias": a_id, "error": "정본과 별칭이 같음"})
            continue
        if c_id not in idx or a_id not in idx:
            reports.append({"canonical": c_id, "alias": a_id, "error": "KeyRef 없음"})
            continue
        c_path, c_fm = idx[c_id]
        a_path, a_fm = idx.pop(a_id)
        merged, rep = merge_pair(c_fm, a_fm)
        _, body = _read(c_path)
        _write(c_path, merged, body.rstrip("\n") + f"\n\n<!-- alias: {a_id} 이월 -->\n")
        dup_dir.mkdir(exist_ok=True)
        shutil.move(str(a_path), str(dup_dir / a_path.name))
        amap[a_id] = c_id
        idx[c_id] = (c_path, merged)
        # 쌍마다 기록 — 중간에 멈춰도 옮긴 별칭의 행방이 남는다
        map_path.write_text(json.dumps(amap, ensure_ascii=False, indent=2), encoding="utf-8")
        reports.append(rep)
    return reports


def _rewrite_node(node, amap: dict[str, str], manual: list[str]):
    if isinstance(node, str):
        out, man = rewrite_ref_ids(node, amap)
        manual.extend(man)
        return out
    if isinstance(node, list):
        return [_rewrite_node(x, amap, manual) for x in node]
    if isinstance(node, dict):
        return {k: _rewrite_node(v, amap, manual) for k, v in node.items()}
    return node


def rewrite_cards(cards_dir: Path, amap: dict[str, str]) -> list[str]:
    """카드 JSON 문자열의 별칭 REF를 정본으로. 수동 목록(파일: 꼴)을 돌려준다."""
    manual_all: list[str] = []
    for p in sorted(cards_dir.glob("*_card.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        manual: list[str] = []
        new = _rewrite_node(data, amap, manual)
        if new != data:
            p.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
        manual_all.extend(f"{p.name}: {m}" for m in manual)
    return manual_all


def check_aliases(keyref_dir: Path) -> list[str]:
    """별칭의 key_numbers가 정본에 모두 있는지(F72 ④). 경고 목록."""
    map_path = _alias_map_path(keyref_dir)
    if not map_path.exists():
        return []
    amap = json.loads(map_path.read_text(encoding="utf-8"))
    canon = _index(keyref_dir)
    dup_dir = keyref_dir.parent / "KeyRef_dup"
    dups = _index(dup_dir) if dup_dir.exists() else {}
    warns: list[str] = []
    for a_id, c_id in sorted(amap.items()):
        if a_id not in dups or c_id not in canon:
            warns.append(f"{a_id}→{c_id}: 별칭 또는 정본 KeyRef를 찾지 못함")
            continue
        have = set(canon[c_id][1].get("key_numbers") or [])
        orphan = [x for x in (dups[a_id][1].get("key_numbers") or []) if x not in have]
        if orphan:
            warns.append(f"{a_id}→{c_id}: 정본에 없는 key_numbers {len(orphan)}건 — {orphan[:3]}")
    return warns


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # F53 계열: 경고(stderr)도 cp949 콘솔에서 안전하게
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="KeyRef 중복 후보·병합·이월 보고")
    ap.add_argument("keyref", help="KeyRef 디렉토리")
    ap.add_argument("--report", action="store_true", help="중복 후보 표 (기본)")
    ap.add_argument("--apply", action="store_true", help="확정 쌍 병합 (--pairs 필요)")
    ap.add_argument("--pairs", help="확정 쌍 JSON [{canonical, alias}, ...]")
    ap.add_argument("--cards", help="카드 디렉토리 — apply 뒤 별칭 REF를 정본으로 바꿈")
    ap.add_argument("--check", action="store_true", help="별칭의 고아 key_numbers 검사")
    args = ap.parse_args()

    kr = Path(args.keyref)
    if not kr.is_dir():
        print(f"KeyRef 디렉토리 없음: {kr}", file=sys.stderr)
        return 1

    if args.check:
        warns = check_aliases(kr)
        for w in warns:
            print(f"[WARN] {w}")
        print(f"check: 경고 {len(warns)}건")
        return 3 if warns else 0

    if args.apply:
        if not args.pairs:
            print("--apply에는 --pairs가 필요합니다", file=sys.stderr)
            return 1
        pairs = json.loads(Path(args.pairs).read_text(encoding="utf-8"))
        reports = apply_pairs(kr, pairs)
        for r in reports:
            if "skipped" in r:
                print(f"[SKIP] {r['alias']}→{r['canonical']}: {r['skipped']}")
            elif "error" in r:
                print(f"[WARN] {r['alias']}→{r['canonical']}: {r['error']}")
            else:
                print(f"{r['alias']}→{r['canonical']}: key_numbers +{r['key_numbers']}, "
                      f"related_sections +{r['related_sections']}, excerpt {r['excerpt']}")
        manual: list[str] = []
        if args.cards:
            amap = json.loads(_alias_map_path(kr).read_text(encoding="utf-8"))
            manual = rewrite_cards(Path(args.cards), amap)
            for m in manual:
                print(f"[MANUAL] {m}")
        bad = [r for r in reports if "error" in r]
        return 3 if (manual or bad) else 0

    cands = find_candidates(kr)
    print(f"{'정본':<10} {'별칭':<10} {'근거':<6} 점수")
    for c in cands:
        print(f"{c['canonical']:<10} {c['alias']:<10} {c['reason']:<6} {c['score']}")
    print(f"후보 {len(cands)}쌍 — 확인한 쌍만 pairs.json으로 --apply (자동 병합 안 함)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
