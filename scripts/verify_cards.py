"""카드 완결성 일괄 점검 — 분량·종결부·인용 수 (v1.10.2에서 자식 도구를 플러그인으로 승격, F101).

사용법:

    python -m scripts.verify_cards <cards_dir>
    python -m scripts.verify_cards output/cards

검증 기준 A~E(JSON 읽기·schema_version·사이즈별 분량·종결부·citation_count)의 판정 코드는
v1.11-c에서 `techdoc_core.qc.legacy.card_checks`로 옮겼다 — qc 게이트 VC-A~VC-E가 같은 함수를
쓴다. 이 모듈은 기존 공개 이름을 다시 내보내고 표 출력·종료 코드만 맡는 래퍼다.

산출: 카드별 PASS/WARN/FAIL 표 + 의심 카드 상세.
종료 코드: 0 (FAIL=0) / 2 (FAIL>0).
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from pathlib import Path

from techdoc_core.qc.legacy.card_checks import (
    _EMPHASIS_TAIL_RE,
    _TAIL_BODY_KEYS,
    BODY_KEYS,
    META_KEYS,
    TAIL_OK,
    THRESHOLDS,
    _text_of,
    check_card,
    check_card_data,
    collect_body_chars,
    last_body_tail,
    load_threshold_overrides,
    parse_call_id,
)

__all__ = [
    "BODY_KEYS", "META_KEYS", "TAIL_OK", "THRESHOLDS", "_EMPHASIS_TAIL_RE", "_TAIL_BODY_KEYS",
    "_text_of", "check_card", "check_card_data", "collect_body_chars", "last_body_tail",
    "load_threshold_overrides", "main", "natural_key", "parse_call_id",
]


def natural_key(s: str) -> tuple:
    s = s.replace("_card", "")
    parts: list = []
    for tok in re.split(r"[.]", s):
        m = re.match(r"^([A-Z]*)(\d*)$", tok)
        if m:
            parts.extend([m.group(1) or "", int(m.group(2)) if m.group(2) else 0])
        else:
            parts.append(tok)
    return tuple(parts)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # F53 계열: 경고(stderr)도 cp949 콘솔에서 안전하게
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description="techdoc-plugin 카드 완결성 일괄 점검"
    )
    ap.add_argument(
        "cards_dir", nargs="?", default="output/cards",
        help="카드 디렉토리 (기본: output/cards). 자식 프로젝트 디렉토리 기준 상대 경로."
    )
    ns = ap.parse_args()
    cards_dir = Path(ns.cards_dir).resolve()

    if not cards_dir.is_dir():
        print(f"카드 디렉토리 없음: {cards_dir}", file=sys.stderr)
        return 1

    ov = load_threshold_overrides(cards_dir)
    if ov:
        pairs = " / ".join(f"{k}={v}" for k, v in sorted(ov["applied"].items()))
        print(f"[임계 재정의] {ov['path'].name} -> {pairs}")
    cards = sorted(cards_dir.glob("*_card.json"), key=lambda p: natural_key(p.stem))
    if not cards:
        print(f"카드 파일 없음: {cards_dir}")
        return 1

    print(f"검증 대상: {cards_dir} ({len(cards)} 카드)")
    results = [check_card(p) for p in cards]

    print(f"{'='*92}")
    print(f"{'ID':<10} {'Size':<5} {'Form':<10} {'chars':<8} {'Status':<6}  Notes")
    print(f"{'-'*92}")
    cnt = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in results:
        cnt[r["status"]] += 1
        notes_parts = []
        if r["issues"]:
            notes_parts.append("FAIL: " + "; ".join(r["issues"]))
        if r["warns"]:
            notes_parts.append("WARN: " + "; ".join(r["warns"]))
        notes = " | ".join(notes_parts)
        if len(notes) > 55:
            notes = notes[:52] + "..."
        print(f"{r['id']:<10} {r['size_id']:<5} {r['schema_form']:<10} "
              f"{r['chars']:<8} {r['status']:<6}  {notes}")
    print(f"{'-'*92}")
    print(f"  TOTAL: {len(results)}  PASS: {cnt['PASS']}  WARN: {cnt['WARN']}  FAIL: {cnt['FAIL']}")
    print(f"{'='*92}")

    suspect = [r for r in results if r["status"] != "PASS"]
    if suspect:
        print("\n=== 의심 카드 상세 ===\n")
        for r in suspect:
            print(f"[{r['status']}] {r['id']}  size_id={r['size_id']}  form={r['schema_form']}  chars={r['chars']}")
            for it in r["issues"]:
                print(f"  FAIL  {it}")
            for w in r["warns"]:
                print(f"  WARN  {w}")
            if r["tail"]:
                print(f"  tail: ...{r['tail']!r}")
            print()
    return 0 if cnt["FAIL"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
