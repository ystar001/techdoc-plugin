"""코드 네임스페이스 게이트 — V90 (v1.11-c 신규, F75).

원리: 규범 문서에서 **같은 코드 토큰이 절마다 다른 뜻으로 정의되면** 사람은 문맥으로 가르지만, 표에서
값만 긁는 기계 처리는 가르지 못한다(F75 — `E1~E4`·`L0~L3`이 근거 계층·산정 절차·발현 시차·에스컬레이션
단계로 겹쳐 쓰임). 카드 층 게이트는 카드 하나만 보므로 이 충돌을 원리적으로 못 잡는다 — 이 게이트는
문서 전역 코드 사전을 만들어 한 토큰의 다중 정의를 경고한다. 특정 문서 건수에 맞춰 정하지 않았다(E17).

- **코드 토큰**: 기본 `[A-Z]{1,3}-?\\d{1,3}`(앞뒤가 영숫자가 아닐 것 — 「E1」「L0」「OP-30」「N4」).
  `extra.code_namespace.pattern`으로 바꾼다(정규식, 앞뒤 경계는 게이트가 붙인다). 인용 id(`REF-…`)는
  늘 뺀다. `extra.code_namespace.allow`(토큰 목록)에 든 토큰은 세지 않는다.
- **정의**(이 둘만 — 본문 속 언급·참조는 정의가 아니다):
  ① 표 행: 마크다운 표의 **첫 칸이 토큰 하나뿐**(굵게·인라인 코드 표시는 걷음)이고 뒤 칸에 글이 있는 행.
     뜻 = 첫 칸 다음의 비지 않은 첫 칸(F75 기대 「표의 첫 열에 코드가 있고 그 행이 뜻을 적는 표」).
  ② 줄머리 정의: 줄 첫머리(목록 기호 `-`·`*`·`1.`·표제 `#` 허용, 굵게·코드 표시 허용)에 토큰이 오고 바로
     쌍점(반각·전각)·줄표(em·en)·` - `·`(` 가 뒤따르는 줄. 뜻 = 구분 기호 뒤 글(괄호 꼴이면 괄호 안).
  코드 펜스(```) 안은 보지 않는다.
- **절**: 카드 id(분할 표지 `.L1`·`.XL2`를 뗀 것 — 분할 카드는 같은 절). 카드가 없으면 산문 파일 하나.
- **지적**: 한 토큰이 **두 절 이상**에서 정의되고, 절마다의 첫 정의 중 **뜻이 다른 쌍**이 있으면 토큰마다
  경고 하나. 뜻 비교는 표시·인용·문장부호·빈칸을 걷고 소문자로 맞춘 뒤, 같거나 한쪽이 다른 쪽을 품으면
  같은 뜻(정본 표를 줄여 다시 적은 것)으로 본다. 위치는 처음 어긋난 절의 정의 자리.
"""
from __future__ import annotations

import re

from techdoc_core.qc.model import DocModel
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

DEFAULT_PATTERN = r"[A-Z]{1,3}-?\d{1,3}"
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP = re.compile(r"^[\s:\-|]+$")
_MARKS = re.compile(r"\*\*|__|`")
_SPLIT = re.compile(r"\.(?:L|XL)\d+$")
_NORM_DROP = re.compile(r"\[REF-\d+\]|[\s\W_]+")


def _token_re(model: DocModel) -> re.Pattern:
    pat = ((model.extra or {}).get("code_namespace") or {}).get("pattern") or DEFAULT_PATTERN
    return re.compile(rf"(?<![A-Za-z0-9])(?:{pat})(?![A-Za-z0-9])")


def _allow(model: DocModel) -> set[str]:
    allow = ((model.extra or {}).get("code_namespace") or {}).get("allow") or []
    return {str(a) for a in allow}


def _line_def_re(tok: re.Pattern) -> re.Pattern:
    return re.compile(  # 전각 쌍점·en 줄표는 정의 구분 기호로 일부러 받는다
        r"^\s*(?:#{1,6}\s+)?(?:(?:[-*+]|\d+[.)])\s+)?(?:\*\*|`)?"
        rf"({tok.pattern})(?:\*\*|`)?\s*(?:[:：]|—|–|\s-\s|\()\s*(.*)$")  # noqa: RUF001


def norm(defn: str) -> str:
    """뜻 비교용 — 표시·인용·문장부호·빈칸을 걷고 소문자."""
    return _NORM_DROP.sub("", _MARKS.sub("", defn)).lower()


def definitions(text: str, tok: re.Pattern):
    """(줄번호, 토큰, 뜻) — 표 행·줄머리 정의만, 코드 펜스 밖."""
    line_def = _line_def_re(tok)
    infence = False
    for i, ln in enumerate(text.split("\n"), 1):
        if _FENCE.match(ln):
            infence = not infence
            continue
        if infence:
            continue
        m = _TABLE_ROW.match(ln)
        if m:
            if _TABLE_SEP.match(m.group(1)):
                continue
            cells = [c.strip() for c in m.group(1).split("|")]
            head = _MARKS.sub("", cells[0]).strip()
            rest = [c for c in cells[1:] if _MARKS.sub("", c).strip()]
            if rest and tok.fullmatch(head):
                yield i, head, rest[0]
            continue
        m = line_def.match(ln)
        if m:
            body = m.group(2).strip()
            if ln[m.end(1):].lstrip("*` ").startswith("("):
                body = body.split(")", 1)[0]
            if norm(body):
                yield i, m.group(1), body


def _same(a: str, b: str) -> bool:
    return a == b or (bool(a) and bool(b) and (a in b or b in a))


def _sources(model: DocModel):
    """(절 키, 위치 앞부분, 글) — 카드가 있으면 카드 섹션, 없으면 산문 파일."""
    if model.cards:
        for cid, key, _title, body in model.card_items():
            yield _SPLIT.sub("", cid), f"{cid}:{key}", body
    else:
        for tf in model.prose():
            yield tf.rel, tf.rel, tf.text


@gate("V90", samples=[
    Sample(sample_model(cards={"8.3": {"sections": {"s": {"body": "| E1 | 무작위 대조 |"}}},
                               "19.1": {"sections": {"s": {"body": "| E1 | 비용 항목 |"}}}}), 1),
    Sample(sample_model(cards={"8.3": {"sections": {"s": {"body": "| E1 | 무작위 대조 |"}}},
                               "9.1": {"sections": {"s": {"body": "E1: 무작위 대조"}}}}), 0),
])
def v90(model: DocModel) -> GateOutput:
    tok, allow = _token_re(model), _allow(model)
    # 토큰 → {절: (위치, 뜻 원문, 뜻 정규형)} — 절마다 첫 정의만
    seen: dict[str, dict[str, tuple[str, str, str]]] = {}
    n_sources = 0
    for sec, loc, text in _sources(model):
        n_sources += 1
        for line, token, defn in definitions(text, tok):
            if token in allow or token.startswith("REF-"):
                continue
            seen.setdefault(token, {}).setdefault(sec, (f"{loc}:{line}", defn, norm(defn)))
    items: list[Finding] = []
    for token, by_sec in seen.items():
        if len(by_sec) < 2:
            continue
        secs = list(by_sec.items())
        clash = [b for k, a in enumerate(secs) for b in secs[k + 1:]
                 if not _same(a[1][2], b[1][2])]
        if not clash:
            continue
        listing = " · ".join(f"{s} 「{v[1][:30]}」" for s, v in secs)
        items.append(Finding(clash[0][1][0],
                             f"{token} — 서로 다른 절에서 다른 뜻으로 정의: {listing}"))
    return GateOutput(n_sources, items)
