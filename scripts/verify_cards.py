"""카드 완결성 일괄 점검 — 분량·종결부·인용 수 (v1.10.2에서 자식 도구를 플러그인으로 승격, F101).

사용법:

    python -m scripts.verify_cards <cards_dir>
    python -m scripts.verify_cards output/cards

배경:
  techdoc-plugin v1.1.0의 카드는 호출별로 약간 다른 스키마로 산출된다 (F1).
  관찰된 본문 위치 변형:
    - sections.<key>.body            (1.x, 2.x 다수)
    - sections.<key>.narrative       (5.6.L2 등)
    - sections.<key>.content
    - blocks (배열)                  (4.4.L3 이후 L3 카드 다수, 6.2.L2)
  키 이름도 sec3_trends_domestic_global / sec3_trends_international /
  sec3_trend_analysis 등 변형. 따라서 키 매칭이 아닌
  **본문 글자 수 합계** 기반으로 완결성을 판정한다.

검증 기준:

A. JSON parse 성공
B. schema_version in ("0.1.0", "0.2.0")  (0.2.0 = self-model 엄격 표준)
C. 본문 글자 수 합계 (모든 str 값 재귀 합산) >= 사이즈별 임계
   - S  : 14,000자 (12p x ~1,200자/p의 안전 하한)
   - L1 :  7,000자 (6p)
   - L2 : 10,000자 (8p)
   - L3 :  5,000자 (4p)
   - XL : 미사용 (Cat 11에서 처음 등장 예정)
D. 본문 마지막 200자 종결부 패턴
   - 마지막 비공백 문자가 마침표/따옴표/괄호/한글 종결어미여야 함
   - 미달 시 컷오프 의심
E. citation_count > 0 (값이 있는 경우만)

산출: 카드별 PASS/WARN/FAIL 표 + 의심 카드 상세.
종료 코드: 0 (FAIL=0) / 2 (FAIL>0).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from pathlib import Path

from techdoc_core.card_id import parse_card_id_parts, size_id

# 사이즈별 본문 글자 임계 (한글 어절 기준 보수적 하한)
# P0 = Part-0 개요 카드 (8,000자 = 약 6p 안전 하한, 본문 S보다 작은 분량 의도)
# XL* = 본문 Cat 11 작물별 응용 + 별첨 C/E 5-sub 분할 공통 (8,000자 보수 하한)
#       별첨 C/E XL은 평균 25k~50k자라 사실상 항상 PASS, 본문 XL이 임계 정합 대상
THRESHOLDS = {"S": 14000, "L1": 7000, "L2": 10000, "L3": 5000,
              "P0": 8000, "XL1": 8000, "XL2": 8000,
              "XL3": 8000, "XL4": 8000, "XL5": 8000}

# -- 프로젝트별 임계 재정의 (선택) --------------------------------
# 문서 장르마다 카드 하나의 적정 분량이 다르다. 표준방법론(M계열)은 절당 1만자대이나,
# 현장 지침서(S계열)는 "절을 펼침면 2쪽 안에서 끝낸다"는 규정 때문에 3~5천자대다.
# 공유 기본값을 건드리지 않고, 프로젝트가 자기 임계를 선언할 수 있게 한다.
#
#   <project>/output/verify_thresholds.json   예: {"S": 3000, "_note": "..."}
#
# 파일이 없으면 동작은 종전과 완전히 같다(하위 호환).
def load_threshold_overrides(cards_dir: Path) -> dict:
    for cand in (cards_dir.parent / "verify_thresholds.json",
                 cards_dir / "verify_thresholds.json"):
        if cand.is_file():
            try:
                with open(cand, encoding="utf-8") as f:
                    d = json.load(f)
                ov = {k: v for k, v in d.items()
                      if not k.startswith("_") and isinstance(v, int)}
                if ov:
                    THRESHOLDS.update(ov)
                    return {"path": cand, "applied": ov}
            except Exception as e:
                print(f"[warn] threshold override read failed: {cand} - {e}",
                      file=sys.stderr)
    return {}


# 종결 허용 패턴 (한국어 서술 종결)
TAIL_OK = (
    ".", "。", "?", "!",
    '"', "'", ")", "]", "}", "”", "’",  # noqa: RUF001 — 둥근 따옴표는 종결 허용 문자
    "다", "함", "음", "임", "것",
)

# 본문으로 간주할 문자열 키 (재귀 합산 시 사용)
BODY_KEYS = {"body", "narrative", "content", "text", "summary"}
# 메타로 간주해 길이 합산에서 제외할 키
META_KEYS = {
    "title", "schema_version", "section_id", "card_id", "size_grade",
    "style", "scope_note", "split_part", "part_id", "part_label",
    "predecessor_part", "successor_part", "ref_id", "purpose",
    "location_in_text", "id", "name", "writer", "writing_date",
    "input_outline", "input_references", "keyref_directory",
    "estimated_words", "target_chars_min", "target_chars_max",
    "estimated_length_pages", "target_pages", "target_pages_total",
    "target_pages_this_part",
    "quick_summary",  # 핵심 요약 상자 — 본문 아님 (F64)
}


def parse_call_id(stem: str) -> tuple[str, str | None]:
    """카드 파일명 → (size_id, split_marker). 공용 파서 `techdoc_core.card_id` 래퍼.

    별첨 접두 문자(A~Z, 하이픈 유무)·문자가 가운데 오는 ID(`2.A.7`)·분할 표지(L/XL)를
    구분자 분해로 인식한다 (F58·F70·F73·F79·F81). 인식 실패면 ('?', None).
    """
    cid = parse_card_id_parts(stem)
    return size_id(cid), cid.split


def collect_body_chars(node, depth: int = 0) -> tuple[int, str]:
    """node 안의 모든 본문 문자열을 합산 + 마지막 본문 텍스트 일부 반환.

    BODY_KEYS에 해당하는 str 값은 본문으로 합산.
    META_KEYS는 무시.
    그 외 일반 dict/list는 재귀 탐색.
    100자 이하 단순 str (라벨/제목 등)은 본문으로 보지 않음.
    """
    total = 0
    last_tail = ""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in META_KEYS:
                continue
            if k in BODY_KEYS and isinstance(v, str):
                total += len(v)
                if v.strip():
                    last_tail = v.rstrip()[-200:]
                continue
            if isinstance(v, str):
                if len(v) >= 100:  # 짧은 라벨류는 본문 아님
                    total += len(v)
                    if v.strip():
                        last_tail = v.rstrip()[-200:]
                continue
            sub_total, sub_tail = collect_body_chars(v, depth + 1)
            total += sub_total
            if sub_tail:
                last_tail = sub_tail
    elif isinstance(node, list):
        for item in node:
            sub_total, sub_tail = collect_body_chars(item, depth + 1)
            total += sub_total
            if sub_tail:
                last_tail = sub_tail
    return total, last_tail


_TAIL_BODY_KEYS = ("body", "narrative", "content", "text")
_EMPHASIS_TAIL_RE = re.compile(r"[*_`]+$")


def _text_of(node) -> str:
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        for k in _TAIL_BODY_KEYS:
            if isinstance(node.get(k), str) and node[k].strip():
                return node[k]
    return ""


def last_body_tail(card: dict) -> str:
    """종결부 검사 대상: `sections`(dict면 마지막 값, list면 마지막 원소) → `blocks` 마지막.

    키 순회 순서에 기대지 않는다 — `quick_summary`가 `sections` 뒤에 있어도 요약 상자 끝을
    보지 않는다 (F64 ②). 끝의 마크다운 강조 표지(`**`·`*`·`_`·`` ` ``)는 벗긴다 (F64 ③).
    """
    for key in ("sections", "blocks"):
        node = card.get(key)
        last = None
        if isinstance(node, dict) and node:
            last = list(node.values())[-1]
        elif isinstance(node, list) and node:
            last = node[-1]
        text = _text_of(last)
        if text.strip():
            return _EMPHASIS_TAIL_RE.sub("", text.rstrip())[-200:]
    return ""


def check_card(path: Path) -> dict:
    info: dict = {
        "id": path.stem.replace("_card", ""),
        "size_id": "?", "size_actual": "?",
        "chars": 0, "tail": "", "schema_form": "?",
        "issues": [], "warns": [],
    }

    try:
        with path.open("r", encoding="utf-8") as f:
            card = json.load(f)
    except Exception as e:
        return {**info, "status": "FAIL", "issues": [f"JSON parse: {e}"]}

    sv = card.get("schema_version")
    # plugin v1.1.0+ 스키마 (0.1.0)·self-model 엄격 표준 (0.2.0)·별첨 B/C 신스키마
    # (blocks 기반, schema_version None) 모두 정상 허용. 그 외 값만 WARN.
    if sv is not None and sv not in ("0.1.0", "0.2.0"):
        info["warns"].append(f"schema_version={sv!r}")

    sid, _ = parse_call_id(path.stem)
    info["size_id"] = sid
    info["size_actual"] = card.get("size_grade", "?")

    if "sections" in card:
        info["schema_form"] = "sections"
    elif "blocks" in card:
        info["schema_form"] = "blocks"
    else:
        info["schema_form"] = "other"

    chars, fallback_tail = collect_body_chars(card)
    tail = last_body_tail(card) or _EMPHASIS_TAIL_RE.sub("", fallback_tail.rstrip())
    info["chars"] = chars
    info["tail"] = tail[-40:] if tail else ""

    threshold = THRESHOLDS.get(sid, 8000)
    if sid == "?":
        # 조용한 기본값 적용 금지 — 임계가 틀린 것인지 카드가 짧은 것인지 가려지게 (F73·F79)
        info["warns"].append("ID 꼴 인식 실패 — 임계 8000 기본값 적용")
    # 전문(前文)·일러두기 등 front matter 카드는 분량 임계 면제 (opt-in: self_check.front_matter)
    is_front = bool((card.get("self_check") or {}).get("front_matter"))
    if is_front:
        info["warns"].append(f"front matter — 분량 임계 면제 ({chars}자)")
    elif chars < threshold * 0.5:
        info["issues"].append(f"본문 매우 부족: {chars}자 (임계 {threshold} 절반 미만)")
    elif chars < threshold:
        info["warns"].append(f"본문 부족: {chars}자 (임계 {threshold})")

    if tail:
        last_char = tail.rstrip()[-1:] if tail.rstrip() else ""
        if last_char and not tail.rstrip().endswith(TAIL_OK):
            info["warns"].append(f"종결부 의심: ...'{tail[-30:]}' (마지막 '{last_char}')")

    val = card.get("validation") or card.get("self_check") or card.get("self_diagnosis") or {}
    if isinstance(val, dict):
        cc = val.get("citation_count")
        if cc is not None and cc == 0:
            info["issues"].append("citation_count=0")

    if info["issues"]:
        status = "FAIL"
    elif info["warns"]:
        status = "WARN"
    else:
        status = "PASS"
    return {**info, "status": status}


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
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
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
