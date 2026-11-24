"""영문 약어·풀이 페어 추출 — `scripts/extract_glossary.py`에서 옮김 (v1.11-c Task 3).

`check_quality`의 표기 일관성 지표(F16)와 qc 게이트 PLG-CQ-undefined_abbreviations가 같이 쓴다.
`extract_glossary`는 이 모듈의 이름을 그대로 다시 내보낸다(공개 이름 불변). LLM 호출 0회.
"""
from __future__ import annotations

import re
from collections import Counter

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
