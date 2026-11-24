"""집필 흔적 게이트 — V87 (v1.11-b 신규, F87).

원리(E17): **독자가 읽는 글에 집필 도구·작업 과정의 흔적이 새는 것.** 원본 시리즈 게이트가 없는
신규 게이트라, 꼴은 특정 문서의 건수가 아니라 플러그인이 스스로 만드는 산출물의 흔적에서 정한다.

- `call_id` — 카드 호출 번호: 분할 표지(`L2`·`XL3`)가 붙은 카드 ID(`3.2.L2`·`A-1.XL3`·`II.6.L2`).
  후보 토큰을 `card_id.parse_card_id_parts`(번호 꼴 설정)로 다시 읽어 분할 표지가 있고 종류를
  알아본 것만 센다. 분할 표지 없는 「3.2」는 정상적인 절 번호라 세지 않는다.
- `filename` — 작업 파일 이름: 플러그인 파이프라인이 쓰는 파일(`*_card.json`·`writer_state.json`·
  `reference_list.json`·`research_round_*.json`·`KeyRef/` 등) + 설정 `extra.leak.file_patterns`
  (글롭 목록 — `allow`와 같은 `fnmatch` 꼴 `*.py`·`params_?.txt`. 정규식이 필요하면 `re:` 접두).
- `split` — writer 분할 안내 「다음 분할」·「이전 분할」.
- `this_card` — 카드 지칭 「이 카드」.

자기 서술 「이 절은/장은」은 V24(META)가 맡으므로 세지 않는다(중복 집계 방지).

읽는 곳은 독자에게 보이는 글뿐이다 — 코드 펜스·인라인 코드·HTML 주석·태그·표제 앵커 `{#…}`·
링크 주소 `](…)`는 지운 뒤 본다. 문서가 파일을 정당하게 다루는 경우를 위해 허용 목록
`extra.leak.allow`(맞은 글자 그대로 또는 `fnmatch` 꼴)에 든 것은 세지 않는다.

원천(v1.11-c, F109) — **독자 글이 있으면 독자 글 하나만** 본다(`model.prose()`: draft 또는 렌더 트리).
카드 수준 필드는 렌더러가 싣지 않으면 독자에게 보이지 않고, 싣는다면 이미 렌더 트리에 있어 다시 읽으면
두 번 센다. 독자 글이 없을 때(카드만 있는 산출물)만 카드 필드 `extra.leak.card_fields`(기본
`scope_note`·`split_continuation_note` — 작성기가 분할 사이에 남기는 메모 칸)를 읽는다.

- `plan_doc` — 프로젝트 계획 문서 인용(F115): 설정 `extra.leak.plan_docs`(이름 목록, 기본 없음 —
  플러그인 파이프라인은 계획 문서를 만들지 않는다)의 이름마다 그 문서의 절·요구 번호 인용
  「PRD §1.2」·「PRD REQ-003」과, 확장자가 있는 이름이면 파일 이름 그대로(`case_plan.md`)를 센다.

같은 줄에서 같은 흔적이 두 번 나오면 글에 「(그 줄 n번째)」를 붙여 지적이 (위치, 글)로 고유하다(F111).
"""
from __future__ import annotations

import re
from fnmatch import fnmatchcase

from techdoc_core.card_id import parse_card_id_parts
from techdoc_core.qc.model import DocModel
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

FENCE = re.compile(r"^\s*(?:```|~~~)")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
INLINE_CODE = re.compile(r"(`+)(?!`).+?(?<!`)\1(?!`)")
HEAD_ANCHOR = re.compile(r"\{#[^}\n]*\}")
HTML_TAG = re.compile(r"</?[A-Za-z][^<>\n]*>")
LINK_TARGET = re.compile(r"\]\([^)\n]*\)")

# 분할 표지가 붙은 카드 ID 후보 — 판정은 parse_card_id_parts가 한다(번호 꼴 설정을 따름)
# 앞뒤 경계는 ASCII로만 본다 — 한글 조사(「3.2.L2와」)가 바로 붙기 때문
CALL_ID = re.compile(r"(?<![0-9A-Za-z_.\-/])([0-9A-Za-z][0-9A-Za-z\-]*(?:\.[0-9A-Za-z\-]+)*\.X?L\d+)"
                     r"(?![0-9A-Za-z_\-]|\.[0-9A-Za-z])")

# 플러그인 파이프라인이 쓰는 작업 파일 (scripts·agents가 만드는 이름)
PLUGIN_WORK_FILES = (
    r"[\w.\-]+_card\.json",
    r"writer_state\.json",
    r"reference_list\.json",
    r"research_round_[\w\-]*\.json",
    r"merged_research\.json",
    r"(?:draft|final)_outline\.json",
    r"document_(?:draft|final)\.json",
    r"autopilot_state\.json",
    r"notion_state\.json",
    r"(?:quality|qc)_report\.json",
    r"KeyRef[/\\]",
)
SPLIT_NOTE = re.compile(r"(?:다음|이전)\s*분할")
THIS_CARD = re.compile(r"(?<![가-힣])이\s+카드")

CARD_FIELDS = ("scope_note", "split_continuation_note")


def _cfg(model: DocModel) -> dict:
    return (model.extra or {}).get("leak") or {}


def _plan_doc_re(model: DocModel) -> re.Pattern | None:
    """계획 문서 인용 — 이름마다 「<이름> §n」·「<이름> REQ-n」, 확장자가 있으면 파일 이름도."""
    alts = []
    for name in (str(n).strip() for n in _cfg(model).get("plan_docs") or []):
        if not name:
            continue
        stem = name.rsplit(".", 1)[0] if "." in name else name
        alts.append(re.escape(stem) + r"\s*(?:§\s*\d+(?:\.\d+)*|REQ-[0-9A-Za-z\-]*\d)")
        if "." in name:
            alts.append(re.escape(name))
    if not alts:
        return None
    return re.compile(r"(?<![0-9A-Za-z_.\-])(?:" + "|".join(alts) + r")(?![0-9A-Za-z_])")


def number_repeats(msgs: list[str], where: str = "그 줄") -> list[str]:
    """한 자리에서 같은 글이 되풀이되면 두 번째부터 「(그 줄 n번째)」를 붙인다(F111)."""
    seen: dict[str, int] = {}
    out = []
    for m in msgs:
        seen[m] = seen.get(m, 0) + 1
        out.append(m if seen[m] == 1 else f"{m} ({where} {seen[m]}번째)")
    return out


# 파일 이름 한 글자(ASCII) — 글롭 `*`·`?`가 공백·경로 구분자·한글 조사를 넘지 않게
_GLOB_CHAR = r"[0-9A-Za-z_.\-]"


def glob_fragment(pat: str) -> str:
    """설정 파일 꼴 → 정규식 조각(앞뒤 고정 없음). `re:`로 시작하면 정규식 조각 그대로.

    글롭은 `fnmatch`와 같은 기호(`*`·`?`·`[...]`)를 받되, 본문에서 찾는 것이라 `*`·`?`는 ASCII 파일
    이름 글자만 먹는다 — `allow`(fnmatch)와 같은 꼴로 적을 수 있게(v1.11-c).
    """
    if pat.startswith("re:"):
        return pat[3:]
    out, i = [], 0
    while i < len(pat):
        c = pat[i]
        if c == "*":
            out.append(_GLOB_CHAR + "*")
        elif c == "?":
            out.append(_GLOB_CHAR)
        elif c == "[" and (j := pat.find("]", i + 2)) != -1:
            body = pat[i + 1:j]
            out.append("[" + ("^" + body[1:] if body.startswith("!") else body) + "]")
            i = j
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


def _file_re(model: DocModel) -> re.Pattern:
    pats = list(PLUGIN_WORK_FILES) + [glob_fragment(str(p))
                                      for p in _cfg(model).get("file_patterns") or [] if str(p)]
    return re.compile(r"(?<![0-9A-Za-z_.\-])(?:" + "|".join(f"(?:{p})" for p in pats) + ")")


def _allowed(model: DocModel):
    allow = [str(a) for a in _cfg(model).get("allow") or [] if str(a)]
    return lambda tok: any(tok == a or fnmatchcase(tok, a) for a in allow)


def _visible(line: str) -> str:
    """독자에게 보이지 않는 부분(인라인 코드·앵커·태그·링크 주소)을 지운 줄."""
    for rx in (INLINE_CODE, HEAD_ANCHOR, HTML_TAG, LINK_TARGET):
        line = rx.sub(" ", line)
    return line


def visible_lines(text: str):
    """(줄번호, 보이는 글) — 코드 펜스 안과 HTML 주석은 뺀다(줄 수는 그대로)."""
    text = HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    infence = False
    for i, ln in enumerate(text.split("\n"), 1):
        if FENCE.match(ln):
            infence = not infence
            continue
        if infence or not ln.strip():
            continue
        yield i, _visible(ln)


def scan(line: str, model: DocModel) -> list[str]:
    """한 줄에서 찾은 흔적 — 「종류: 설명」 문자열 목록."""
    allowed = _allowed(model)
    out: list[str] = []
    for m in CALL_ID.finditer(line):
        tok = m.group(1)
        cid = parse_card_id_parts(tok, model.numbering)
        if cid.split and cid.kind != "unknown" and not allowed(tok):
            out.append(f"call_id: 카드 호출 번호 {tok} — 독자에게는 절·별첨 이름으로")
    for m in _file_re(model).finditer(line):
        tok = m.group(0)
        if not allowed(tok):
            out.append(f"filename: 작업 파일 이름 {tok} — 집필 도구의 파일")
    plan = _plan_doc_re(model)
    for m in plan.finditer(line) if plan else ():
        if not allowed(m.group(0)):
            out.append(f"plan_doc: 계획 문서 인용 「{m.group(0)}」 — 집필 과정의 문서")
    for m in SPLIT_NOTE.finditer(line):
        if not allowed(m.group(0)):
            out.append(f"split: 분할 안내 「{m.group(0)}」 — 원고 분할은 독자에게 보이지 않음")
    for m in THIS_CARD.finditer(line):
        if not allowed(m.group(0)):
            out.append(f"this_card: 카드 지칭 「{m.group(0)}」 — 독자에게는 절·항")
    return out


@gate("V87", samples=[
    Sample(sample_model(tree={"a.md": "자세한 계산은 3.2.L2에서 이어진다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "자세한 계산은 3.2절에서 이어진다.\n"}), expect=0),
    Sample(sample_model(tree={"a.md": "값은 writer_state.json에 남긴다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "다음 분할에서 사례를 본다. 이 카드는 원리를 다룬다.\n"}), expect=2),
    Sample(sample_model(tree={"a.md": "```\nwriter_state.json 3.2.L2\n```\n`A-1.XL3`\n"}), expect=0),
])
def v87_writing_trace(model: DocModel) -> GateOutput:
    """집필 흔적 — 카드 호출 번호·작업 파일 이름·분할 안내·「이 카드」가 독자 글에 샘."""
    texts = model.prose()
    out: list[Finding] = []
    for tf in texts:
        for i, line in visible_lines(tf.text):
            out += [Finding(f"{tf.rel}:{i}", msg) for msg in number_repeats(scan(line, model))]
    if texts:  # 독자 글이 있으면 그것만 — 카드 필드는 렌더되지 않거나 이미 렌더 트리에 있다(F109)
        return GateOutput(len(texts), out)
    fields = _cfg(model).get("card_fields")
    fields = [str(k) for k in (CARD_FIELDS if fields is None else fields) if str(k)]
    n_fields = 0
    for cid, card in model.cards.items():
        for key in fields:
            val = card.get(key)
            if not isinstance(val, str) or not val.strip():
                continue
            n_fields += 1
            msgs = [msg for _i, line in visible_lines(val) for msg in scan(line, model)]
            out += [Finding(f"{cid}|{key}: 카드 필드", msg) for msg in number_repeats(msgs)]
    return GateOutput(n_fields, out)
