"""Plan H (F16) — KeyRef·카드에서 약어·용어 자동 추출.

자식 OpenFieldCrops/scripts/extract_glossary.py 를 plugin 맥락으로 적응 이식.
정규식·페어 추출 로직은 LLM 호출 0회·결정론적이다.

오케스트레이션:
  extract_from_output(output_dir) -> dict[str, str]   # outline.glossary 용 flat dict
  inject_into_outline(outline_path, glossary)          # 빈 glossary 슬롯 채움
  main(argv) -> int                                    # CLI (--output <dir>)

산출(선택):
  <output>/glossary.json
  <output>/abbreviations.json
  <output>/glossary_review.md
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Windows cp949 콘솔 안전화
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 카드 본문 추출 (self-model 0.2.0 sections[*].body + standard blocks 모두 robust)
# ---------------------------------------------------------------------------

_BODY_KEYS = ("body", "narrative", "content")  # 본문 카드 3 변형


def extract_card_text(card: dict) -> str:
    """카드의 모든 본문 텍스트를 한 문자열로 모은다. schema 변형 무관.

    지원 layout:
      - self-model 0.2.0:  {"sections": {"sec1": {"body": ...}}} 또는 {"sec1": "본문"}
      - standard:          {"blocks": {...}} / sections[*].blocks (list of dicts)
    """
    chunks: list[str] = []

    def _drain_section(sec_value) -> None:
        # sec_value 가 str 직접인 경우
        if isinstance(sec_value, str):
            if sec_value.strip():
                chunks.append(sec_value)
            return
        if not isinstance(sec_value, dict):
            return
        for key in _BODY_KEYS:
            value = sec_value.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value)
        # blocks 변형 (list of dicts) — 텍스트 필드 평탄화
        blocks = sec_value.get("blocks")
        if isinstance(blocks, list):
            for block in blocks:
                if isinstance(block, dict):
                    for v in block.values():
                        if isinstance(v, str) and v.strip():
                            chunks.append(v)

    secs = card.get("sections")
    if isinstance(secs, dict):
        for sec_value in secs.values():
            _drain_section(sec_value)

    # standard layout: card-level blocks dict (e.g. {"blocks": {"overview": "..."}})
    blocks = card.get("blocks")
    if isinstance(blocks, dict):
        for v in blocks.values():
            if isinstance(v, str) and v.strip():
                chunks.append(v)
            elif isinstance(v, dict):
                _drain_section(v)
    elif isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict):
                for v in block.values():
                    if isinstance(v, str) and v.strip():
                        chunks.append(v)

    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# 영문 약어 추출
# ---------------------------------------------------------------------------

# 본문에서 의미 있는 영문 약어 패턴: 2~8글자, 대문자 시작 + 대문자/숫자 1+개 포함.
# 자식 구현은 all-caps(IOT)만 잡았으나, plugin 코퍼스는 mixed-case 약어(IoT·LoRa·NDVI)가
# 빈출하므로 내부 소문자를 허용하도록 확장한다 (반드시 대문자 2개 이상 또는 대문자+숫자 포함).
# \b 는 한글 인접 시 경계를 인식 못 하므로 lookaround 방식으로 대체.
_ABBR_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z][A-Za-z0-9]{1,7})(?![A-Za-z0-9])"
)

# 약어로 인정할 토큰: 대문자 2개 이상이거나 (대문자 1개 이상 + 숫자 1개 이상).
# "Drip"·"Korea" 같은 일반 고유명사(앞글자만 대문자)는 약어로 보지 않는다.
_ABBR_TOKEN_RE = re.compile(r"^(?=(?:.*[A-Z]){2,}|(?=.*[A-Z])(?=.*[0-9]))[A-Za-z0-9]{2,8}$")


def _looks_like_abbr(token: str) -> bool:
    """mixed-case 토큰이 약어 형태인지 판정 (대문자 2+ 또는 대문자+숫자)."""
    return bool(_ABBR_TOKEN_RE.match(token))

# 추출에서 제외할 토큰 (인용 ID·일반어)
_ABBR_BLACKLIST = {
    "REF",  # 인용 ID prefix
    "PI",   # 프로젝트 PI 메타에서 빈출
}


def find_abbreviations(text: str) -> Counter:
    """텍스트에서 영문 약어 빈도를 집계한다."""
    counts: Counter[str] = Counter()
    for match in _ABBR_RE.finditer(text):
        token = match.group(1)
        if token in _ABBR_BLACKLIST:
            continue
        if not _looks_like_abbr(token):
            continue
        counts[token] += 1
    return counts


# ---------------------------------------------------------------------------
# 풀이 페어 추출
# ---------------------------------------------------------------------------

# abbr 그룹: 자식의 all-caps([A-Z][A-Z0-9]{1,6}) → mixed-case 허용으로 확장.
# 매칭 후 _looks_like_abbr 로 일반 단어를 걸러낸다.
_ABBR_GROUP = r"[A-Z][A-Za-z0-9]{1,7}"

# 패턴 1: 한글풀이(영문풀이, ABBR) — 가장 정형
_PAIR_RE_KE_ABBR = re.compile(
    r"([가-힣][가-힣\s·]{1,30})\(([A-Za-z][A-Za-z0-9\s\-]{2,60}),\s*(" + _ABBR_GROUP + r")\)"
)

# 패턴 2: 영문풀이(ABBR) — 영문 단독 풀이
_PAIR_RE_E_ABBR = re.compile(
    r"([A-Z][A-Za-z][A-Za-z0-9\s\-]{3,60})\((" + _ABBR_GROUP + r")\)"
)

# 패턴 3: 한글풀이(ABBR) — 한글 단독 풀이
_PAIR_RE_K_ABBR = re.compile(
    r"([가-힣][가-힣\s·]{1,30})\((" + _ABBR_GROUP + r")\)"
)

# 약어 풀이 앞에 붙은 한글 조사 제거용 패턴
_KO_PARTICLE_RE = re.compile(
    r'^[의은는이가을를에으로와과도만까지에서부터처럼만큼]{1,3}\s*'
)


def _strip_particle(korean: str) -> str:
    """한글 풀이 앞에 붙은 조사를 제거. 약어 풀이 추출 시 조사 노이즈 차단."""
    return _KO_PARTICLE_RE.sub("", korean.strip()).strip()


def find_explanation_pairs(text: str) -> list[dict]:
    """본문에서 풀이 페어를 추출한다.

    반환 형식: [{"abbr": "NDVI", "korean": "...", "english": "..."}]
    """
    pairs: list[dict] = []
    # 패턴 1 우선 (정보량 가장 많음)
    matched_spans: list[tuple[int, int]] = []
    for m in _PAIR_RE_KE_ABBR.finditer(text):
        if not _looks_like_abbr(m.group(3)):
            continue
        pairs.append({
            "abbr": m.group(3),
            "korean": _strip_particle(m.group(1)),
            "english": m.group(2).strip(),
        })
        matched_spans.append(m.span())
    # 패턴 2: 패턴 1과 겹치지 않는 영역만
    for m in _PAIR_RE_E_ABBR.finditer(text):
        if any(s <= m.start() < e for s, e in matched_spans):
            continue
        if not _looks_like_abbr(m.group(2)):
            continue
        # 첫 단어가 ABBR이면 제외 (예: USDA NRCS 같은 약어 나열)
        english = m.group(1).strip()
        if english.isupper() or english.split()[0].isupper():
            continue
        pairs.append({
            "abbr": m.group(2),
            "korean": "",
            "english": english,
        })
        matched_spans.append(m.span())
    # 패턴 3: 위 두 패턴과 겹치지 않는 영역만
    for m in _PAIR_RE_K_ABBR.finditer(text):
        if any(s <= m.start() < e for s, e in matched_spans):
            continue
        if not _looks_like_abbr(m.group(2)):
            continue
        pairs.append({
            "abbr": m.group(2),
            "korean": _strip_particle(m.group(1)),
            "english": "",
        })
    return pairs


# ---------------------------------------------------------------------------
# reference_list / KeyRef institution 필드에서 기관명·풀이 추출
# ---------------------------------------------------------------------------

# institution 필드는 보통 "미국 농무부 자연자원보전국 (USDA NRCS)" 형식
_INST_RE = re.compile(r"^(.+?)\s*\(([A-Z][A-Z0-9 \-]+)\)\s*$")


def extract_institution_pairs(refs: list[dict]) -> list[dict]:
    """reference_list.json 또는 KeyRef frontmatter의 institution 필드에서 풀이 페어 추출."""
    pairs: list[dict] = []
    for ref in refs:
        inst = (ref.get("institution") or "").strip()
        if not inst:
            continue
        m = _INST_RE.match(inst)
        if not m:
            continue
        korean_or_english = m.group(1).strip()
        abbr_field = m.group(2).strip()
        # "USDA NRCS" 같이 여러 약어가 들어있으면 각각 분리
        for abbr in abbr_field.split():
            if not abbr.isupper() or len(abbr) < 2:
                continue
            # 한글이 포함되면 korean 슬롯, 아니면 english 슬롯
            if re.search(r"[가-힣]", korean_or_english):
                pairs.append({"abbr": abbr, "korean": korean_or_english, "english": ""})
            else:
                pairs.append({"abbr": abbr, "korean": "", "english": korean_or_english})
    return pairs


# ---------------------------------------------------------------------------
# standard_form 결정 (빈도 1위 변형)
# ---------------------------------------------------------------------------

def decide_standard_form(pairs: list[dict]) -> dict[str, dict]:
    """약어별 standard_form 결정 — 빈도 1위 (korean, english) 페어 채택."""
    by_abbr: dict[str, Counter] = defaultdict(Counter)
    for p in pairs:
        key = (p.get("korean", ""), p.get("english", ""))
        by_abbr[p["abbr"]][key] += 1
    result: dict[str, dict] = {}
    for abbr, counter in by_abbr.items():
        # 빈도 1위 페어 중 정보량 많은 것 (korean + english 모두 있는 것 우선)
        top = sorted(
            counter.items(),
            key=lambda kv: (-kv[1], -(bool(kv[0][0]) + bool(kv[0][1]))),
        )[0][0]
        result[abbr] = {"korean": top[0], "english": top[1]}
    return result


# ---------------------------------------------------------------------------
# Glossary dict 빌드
# ---------------------------------------------------------------------------

def build_glossary_dict(pairs: list[dict], abbr_counts: Counter) -> dict:
    """약어·용어 통합 dict 생성. standard_form + variants + frequency.

    키는 약어(abbr). 값은 {standard_form, variants, frequency} 구조.
    """
    by_abbr: dict[str, Counter] = defaultdict(Counter)
    for p in pairs:
        key = (p.get("korean", ""), p.get("english", ""))
        by_abbr[p["abbr"]][key] += 1
    result: dict = {}
    all_abbrs = set(abbr_counts) | set(by_abbr)
    for abbr in all_abbrs:
        variants_counter = by_abbr.get(abbr, Counter())
        # decide_standard_form과 동일 타이브레이크 (정보량 많은 쪽 우선)
        variants_sorted = sorted(
            variants_counter.items(),
            key=lambda kv: (-kv[1], -(bool(kv[0][0]) + bool(kv[0][1]))),
        )
        if variants_sorted:
            top_key, _ = variants_sorted[0]
            standard = {"korean": top_key[0], "english": top_key[1]}
        else:
            standard = {"korean": "", "english": ""}
        variants_list = [
            {"korean": k[0], "english": k[1], "count": c}
            for k, c in variants_sorted
        ]
        result[abbr] = {
            "standard_form": standard,
            "variants": variants_list,
            "frequency": abbr_counts.get(abbr, 0),
        }
    return result


# ---------------------------------------------------------------------------
# 오케스트레이션: output_dir → flat glossary dict (outline.glossary 용)
# ---------------------------------------------------------------------------

def _glossary_definition(entry: dict) -> str:
    """rich glossary entry → outline.glossary 용 한 줄 정의 문자열."""
    std = entry.get("standard_form", {})
    kor = (std.get("korean") or "").strip()
    eng = (std.get("english") or "").strip()
    if kor and eng:
        return f"{kor} ({eng})"
    return kor or eng


def build_rich_glossary(output_dir) -> dict:
    """output_dir 의 cards·reference_list 에서 rich glossary dict 빌드.

    반환: {abbr: {standard_form, variants, frequency}} (build_glossary_dict 형식).
    카드 본문 키는 self-model 0.2.0(sections[*].body)·standard(blocks) 모두 robust 처리.
    """
    output_dir = Path(output_dir)
    abbr_counts: Counter = Counter()
    pairs: list[dict] = []

    # 1) 카드 본문 수집
    cards_dir = output_dir / "cards"
    if cards_dir.exists():
        for card_path in sorted(cards_dir.glob("*_card.json")):
            try:
                card = json.loads(card_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            text = extract_card_text(card)
            abbr_counts.update(find_abbreviations(text))
            pairs.extend(find_explanation_pairs(text))

    # 2) reference_list institution 페어
    ref_list_path = output_dir / "reference_list.json"
    if ref_list_path.exists():
        try:
            ref_list = json.loads(ref_list_path.read_text(encoding="utf-8"))
            refs = ref_list.get("refs") or ref_list.get("references") or []
            pairs.extend(extract_institution_pairs(refs))
        except (OSError, json.JSONDecodeError):
            pass

    return build_glossary_dict(pairs, abbr_counts)


def flatten_glossary(rich: dict) -> dict[str, str]:
    """rich glossary dict → outline.glossary 용 flat {abbr: 정의} dict."""
    flat: dict[str, str] = {}
    for abbr, entry in rich.items():
        definition = _glossary_definition(entry)
        if definition:
            flat[abbr] = definition
    return flat


def extract_from_output(output_dir) -> dict[str, str]:
    """output_dir → flat glossary dict (outline.glossary 용). dict[str, str] 에 바로 주입 가능."""
    return flatten_glossary(build_rich_glossary(output_dir))


# ---------------------------------------------------------------------------
# review.md 렌더링 (사용자 spot-check 입력)
# ---------------------------------------------------------------------------

def render_review_markdown(glossary: dict) -> str:
    """spot-check 용 markdown. 분기 후보(변형 2개 이상) 가장 위에 강조."""
    by_branching = sorted(
        glossary.items(),
        key=lambda kv: (-len(kv[1].get("variants", [])), -kv[1].get("frequency", 0)),
    )
    lines: list[str] = [
        "# Glossary spot-check (F16)",
        "",
        "다음 약어들 중 standard_form 이 적절한지 확인하세요. "
        "변형이 여러 개인 경우 가장 빈도 높은 것이 자동 채택됐습니다.",
        "",
        "## 분기 후보 (변형 2개 이상)",
        "",
    ]
    for abbr, entry in by_branching:
        variants = entry.get("variants", [])
        if len(variants) < 2:
            continue
        lines.append(f"### {abbr} (총 등장 {entry['frequency']}회)")
        std = entry["standard_form"]
        lines.append(f"- **standard_form**: `{std['korean']}` / `{std['english']}`")
        lines.append("- variants:")
        for v in variants:
            lines.append(f"  - `{v['korean']}` / `{v['english']}` ({v['count']}회)")
        lines.append("")
    lines.append("## 단일 변형")
    lines.append("")
    for abbr, entry in by_branching:
        if len(entry.get("variants", [])) >= 2:
            continue
        std = entry["standard_form"]
        lines.append(
            f"- {abbr}: `{std['korean']}` / `{std['english']}` ({entry['frequency']}회)"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# outline 주입 (기존 비어있는 glossary 슬롯만 채움)
# ---------------------------------------------------------------------------

def inject_into_outline(outline_path, glossary: dict[str, str]) -> int:
    """draft_outline.json 의 glossary 필드에 추출 glossary 를 주입.

    기존 glossary 에 없는 키만 추가(사용자 수동 항목 보존). 추가된 항목 수 반환.
    """
    outline_path = Path(outline_path)
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    existing = outline.get("glossary")
    if not isinstance(existing, dict):
        existing = {}
    added = 0
    for key, val in glossary.items():
        if key not in existing or not str(existing.get(key) or "").strip():
            existing[key] = val
            added += 1
    outline["glossary"] = existing
    outline_path.write_text(
        json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return added


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="F16: 약어·용어 자동 추출 → outline.glossary")
    parser.add_argument("--output", default="output", help="output 디렉토리")
    parser.add_argument(
        "--outline", default=None,
        help="draft_outline.json 경로 (생략 시 <output>/draft_outline.json)",
    )
    parser.add_argument(
        "--no-write", action="store_true",
        help="outline·산출 파일을 쓰지 않고 추출만 (dry-run)",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output)
    rich = build_rich_glossary(output_dir)
    flat = flatten_glossary(rich)

    print(f"[extract_glossary] 약어·용어 {len(flat)}건 추출")

    if not flat:
        print("WARN: glossary 비어 있음 — 수동 보강 권장")
        return 0

    if not args.no_write:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "glossary.json").write_text(
            json.dumps(rich, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (output_dir / "glossary_review.md").write_text(
            render_review_markdown(rich), encoding="utf-8"
        )

        outline_path = Path(args.outline) if args.outline else output_dir / "draft_outline.json"
        if outline_path.exists():
            added = inject_into_outline(outline_path, flat)
            print(f"[extract_glossary] outline.glossary 에 {added}건 주입 → {outline_path}")
        else:
            print(f"[extract_glossary] outline 없음(skip): {outline_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
