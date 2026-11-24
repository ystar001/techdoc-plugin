"""문장(산문) 게이트 — V23·V24·V25·V27·V28·V29·V35·V36·V41·V41W·V43·V50·V53·V54·V56·V69·V76·V81
(v1.11-b, F85).

시리즈 check_v2(카드 게이트 V23)와 prose_gates(나머지)에서 판정 로직을 그대로 옮기고 입력만
DocModel로 바꿨다. 산문 게이트의 입력은 `model.prose()`(draft가 있으면 draft, 없으면 렌더 트리).

- **시리즈 고유 값은 설정으로**(E17): 문서가 자기를 부르는 말 「작물편」(`extra.prose.meta_words`,
  V31과 같은 키), 다른 자리를 가리키는 안내의 「…편」(`extra.prose.guide_words`), 개요 파일 머리
  (`extra.prose.overview_prefixes`, 기본 「개요/」), 굵은 글씨 검사의 표식(`extra.prose.markers` —
  목표 상자 `goalbox`·결론 항 `conclusion`은 기본 꺼짐, 절 끝 인용 목록 줄 `cited_refs`는 플러그인
  렌더러가 내는 꼴이라 기본 켜짐).
- **번호 꼴**: arabic(기본)이면 원본 정규식 그대로. roman이면 표 번호(V69)·절 안내(V54)에 로마 숫자
  번호를 더 받는다.
- **V41W**: 원본은 흩어진 서수 나열(넓힘)을 편 설정 `pilot_strict`일 때만 V41에 더했다. 여기서는
  별도 시범 게이트로 건수를 따로 낸다.
"""
from __future__ import annotations

import re
from functools import lru_cache

from techdoc_core.qc.card_text import card_texts
from techdoc_core.qc.dicts import layers_key, load_dict
from techdoc_core.qc.model import DocModel
from techdoc_core.qc.numbering import ROMAN
from techdoc_core.qc.prose import (
    BOLD,
    CAP_PLAIN,
    MARKUP,
    RUNIN,
    SENT,
    is_cap_line,
    paragraphs,
    strip_en_gloss,
    table_before,
)
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
PROSE_SKIP = re.compile(r"^\s*(?:\||```)")


def _style(model: DocModel) -> str:
    return (model.numbering or {}).get("section") or "arabic"


def _prose_cfg(model: DocModel) -> dict:
    return (model.extra or {}).get("prose") or {}


def _texts(model: DocModel) -> dict[str, str]:
    """산문 게이트 입력(원본 prose_gates.run의 texts)."""
    return {tf.rel: tf.text for tf in model.prose()}


def _no_index(texts: dict[str, str]) -> dict[str, str]:
    return {n: t for n, t in texts.items() if not n.endswith("INDEX.md")}


@lru_cache(maxsize=512)
def _paras(text: str, style: str) -> tuple[tuple[int, str, str], ...]:
    """문단 분해는 여러 게이트가 같은 원고에 되풀이하므로 한 번만 한다."""
    return tuple(paragraphs(text, style))


def _card(body: str, title: str = "") -> dict:
    return {"sections": {"s1": {"title": title, "body": body}}}


# ═══ V23 붙어 버린 두 문장 (check_v2 640-694 · 1143-1148) ═══

_V23_END = (r"(?:ㄴ다|는다|한다|된다|썼다|았다|었다|였다|겠다|온다|간다|"
            r"이다|아니다|같다|낫다|많다|적다|없다|있다|크다|작다|다르다|드물다)")
# 다음 문장의 첫머리로 그럴듯한 것 — 그 자리에서 새 문장이 선다는 표지
_V23_NEXT = (r"(?:그러나|그런데|그래서|따라서|하지만|반면|다만|또한|이때|이는|"
             r"이것|그것|여기서|거기서|현장에서|실제로|즉|곧|결국|끝으로|먼저|"
             r"이어|왼쪽|오른쪽|위|아래|가운데|맨|표|그림|차트|각|모든|한|두|세|네)")
V23_GLUE = re.compile(r"(?<![다·])(" + _V23_END + r")\s(" + _V23_NEXT + r")(?=[\s가-힣])")
# 가운뎃점으로 열거한 뒤 수관형사로 받는 꼴은 한 문장이다
V23_LIST = re.compile(r"다·")
V23_SKIP = re.compile(r"^\s*(?:\||```|!!!|>|#{1,6}\s|\$\$|"
                      r"\*\*(?:그림|표|차트|사진|다이어그램)\s|"
                      r"(?:그림|표|차트|사진|다이어그램)\s[\dA-Za-z][0-9A-Za-z.\-]*\.(?:\s|$))")


def glued_sentences(body: str) -> list[str]:
    """마침표가 빠져 두 문장이 붙은 자리."""
    out, infence = [], False
    for ln in body.split("\n"):
        s = ln.strip()
        if s.startswith("```"):
            infence = not infence
            continue
        if infence or not s or V23_SKIP.match(ln):
            continue
        for m in V23_GLUE.finditer(s):
            if V23_LIST.search(s[max(0, m.start(1) - 30):m.start(1)]):
                continue
            out.append("문장이 붙었다 「…" + s[max(0, m.start(1) - 16):m.end(2) + 14] + "…」")
    return out


_ECHO = re.compile(r"([^.!?\n]{12,})\s그래서\s([^.!?\n—]{12,})")


def echoed_clause(body: str) -> list[str]:
    """「그래서 X」의 X가 바로 앞 문장의 되풀이인 자리(꼬리 12자 이상 겹침)."""
    out: list[str] = []
    if "그래서" not in body:  # 정규식이 문장마다 되짚어 느리다 — 「그래서」가 없으면 맞을 수 없다
        return out
    for m in _ECHO.finditer(body):
        a, b = m.group(1).strip(), m.group(2).strip()
        tail = 0
        while tail < min(len(a), len(b)) and a[-1 - tail] == b[-1 - tail]:
            tail += 1
        if tail >= 12:
            out.append(f"「그래서」 뒤가 앞 문장의 되풀이다(꼬리 {tail}자) 「…{b[-30:]}」")
    return out


@gate("V23", samples=[
    Sample(sample_model(cards={"1.1": _card("양방향 결합이다 현장에서 잰 값이 있다.")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("양방향 결합이다. 현장에서 잰 값이 있다.")}), expect=0),
])
def v23_glued_sentences(model: DocModel) -> GateOutput:
    """마침표가 빠져 두 문장이 붙었는가 · 「그래서」 뒤가 앞 문장의 되풀이인가 (카드 글 전부)."""
    out: list[Finding] = []
    for cid, card in model.cards.items():
        for key, _title, body in card_texts(card):
            for e in glued_sentences(body) + echoed_clause(body):
                out.append(Finding(f"{cid}|{key}: 문장", f"{cid}·{key} {e}"))
    return GateOutput(len(model.cards), out)


# ═══ V24 메타 서술 · 집필지시 누수 (prose_gates 65-84 · 901-917) ═══

_META_REST = [
    ("재정의 선언", re.compile(r"(?:여기서|이 장에서|이 절에서)\s*(?:는\s*)?(?:다시|또)\s*(?:정의|세우지|만들지|쓰지)")),
    ("편집 규율 서술", re.compile(r"인용만 한다|인용할 뿐|재정의하지 않는다|다시 정의하지 않는다|다시 세우지 않는다"
                              r"|여기서 다시 만들지")),
    ("편집 사정", re.compile(r"인용이\s*\d+\s*건|\d+\s*파일에 걸린|번호가? 전부 깨(?:진다|져)"
                           r"|인용의 앵커|앵커(?:로|가|를)\s*(?:쓰|삼|유지)|앵커와 (?:겹|맞)")),
    ("개정 이력", re.compile(r"20\d\d-\d\d-\d\d\s*[—\-–]|초판(?:이|은|의)\s*[^.\n]{0,30}(?:고쳐|바꿔|교체)"  # noqa: RUF001
                           r"|신설분을 반영")),
    ("집필 지시", re.compile(r"(?:섹션 개요|카드)(?:다|이다|의 도입부)|여기서는 인용만|본문 작업")),
    ("장 소개", re.compile(r"(?:먼저 전체를|이 절은 그 경계를|왜 (?:또|다시) 쓰는가|그것이 이 (?:장|절|영역)"
                         r"|이 (?:장|절|영역|항)(?:은|이)[^.\n]{0,40}에 지나지 않는다)")),
]


_SELFREF_NOUNS = ("장", "절", "항", "영역", "판")  # 사전이 없을 때(원본 목록)
_SELFREF_VERBS = ("답한다", "다룬다", "적는다", "세운다", "하는 일", "무엇인가")


@lru_cache(maxsize=16)
def _selfref_words(layers: tuple = ()) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """자칭 서술 낱말 — 층 사전 `dicts/meta_self_reference.json`의 nouns·verbs(F114)."""
    d = load_dict("meta_self_reference.json", list(layers)) or {}
    nouns = tuple(str(w) for w in d.get("nouns") or _SELFREF_NOUNS if str(w))
    verbs = tuple(str(w) for w in d.get("verbs") or _SELFREF_VERBS if str(w))
    return nouns, verbs


def _meta(model: DocModel) -> list[tuple[str, re.Pattern]]:
    """자칭 서술의 문서 이름(시리즈 「작물편」)은 `extra.prose.meta_words`로 더한다.

    글 단위 명사·서술 동사 목록은 층 사전(`meta_self_reference.json`)이 싣는다(v1.11-c, F114).
    설정 `extra.prose.selfref_nouns`·`selfref_verbs`가 있으면 그 목록으로 통째로 바꾼다 — 시리즈 층
    설정이 원본 목록을 지키는 자리.
    """
    nouns, verbs = _selfref_words(layers_key(model))
    cfg = _prose_cfg(model)
    if cfg.get("selfref_nouns") is not None:
        nouns = tuple(str(w) for w in cfg["selfref_nouns"] if str(w))
    if cfg.get("selfref_verbs") is not None:
        verbs = tuple(str(w) for w in cfg["selfref_verbs"] if str(w))
    words = [*nouns, *(str(w) for w in _prose_cfg(model).get("meta_words") or [] if str(w))]
    selfref = re.compile(r"이\s*(?:" + "|".join(map(re.escape, words)) + r")(?:은|이|의|에서는)\s*"
                         r"[^.\n]{0,40}?(?:" + "|".join(map(re.escape, verbs)) + ")")
    return [("자칭 서술", selfref), *_META_REST]


@gate("V24", samples=[
    Sample(sample_model(tree={"a.md": "이 장은 관측 체계를 다룬다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "관측 체계는 2.E.4에 있다.\n"}), expect=0),
])
def v24_meta(model: DocModel) -> GateOutput:
    """메타 서술·집필지시 누수 — 인용구 줄과 산문 문단."""
    style = _style(model)
    meta = _meta(model)
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for i, ln in enumerate(text.split("\n"), 1):
            if not ln.lstrip().startswith(">"):
                continue
            for label, rx in meta:
                for m in rx.finditer(ln):
                    out.append(Finding(f"{name}:{i}", f"인용구 {label} — …{m.group(0)[:40]}…"))
        for start, para, _head in _paras(text, style):
            for label, rx in meta:
                for m in rx.finditer(para):
                    out.append(Finding(f"{name}:{start}", f"{label} — …{m.group(0)[:46]}…"))
    return GateOutput(len(texts), out)


# ═══ V25 도표 되읽기 (prose_gates 108-114 · 544-552 · 930-937) ═══

REREAD = [("줄 되읽기", re.compile(r"(?:^|(?<=\. )|(?<=\.\*\* ))(?:\*\*)?(?:첫|둘|셋|넷|다섯|여섯|일곱|여덟)째\s*(?:줄|행)"))]
_TBL = "| 가 | 나 |\n|---|---|\n| 1 | 2 |\n\n"


@gate("V25", samples=[
    Sample(sample_model(tree={"a.md": _TBL + "첫째 줄은 관수량이다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": _TBL + "관수량은 하루 3mm이다.\n"}), expect=0),
])
def v25_reread(model: DocModel) -> GateOutput:
    """표 바로 뒤 문단이 「첫째 줄/행」으로 행을 지목해 여는가(앞에 표가 있을 때만)."""
    style = _style(model)
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for start, para, _head in _paras(text, style):
            if not table_before(text, start):
                continue
            for label, rx in REREAD:
                for m in rx.finditer(para):
                    out.append(Finding(f"{name}:{start}", f"{label} — …{m.group(0)[:46]}…"))
    return GateOutput(len(texts), out)


# ═══ V27 문장 길이 · V28 줄표 · V29 강조 밀도 (prose_gates 49 · 56-63 · 258-259 · 437-541 · 938-958) ═══

MAX_SENT = 160
MAX_DASH = 1
MAX_BOLD_PARA = 1


def dash_uses(sent: str) -> int:
    """줄표를 몇 번 썼는가 — 짝을 이룬 삽입구(사이 60자 이하, 뒤 10자 이상)는 한 번."""
    at = [i for i, ch in enumerate(sent) if ch == "—"]
    n = len(at)
    k = 0
    while k + 1 < len(at):
        inner = re.sub(r"\s", "", sent[at[k] + 1:at[k + 1]])
        rest = re.sub(r"\s", "", sent[at[k + 1] + 1:])
        if len(inner) <= 60 and len(rest) >= 10:
            n -= 1
            k += 2
        else:
            k += 1
    return n


def _is_cite_head(head: str) -> bool:
    """「근거·인용」 항 — 출처를 잇대어 적는 자리라 문장 길이·줄표 규율을 대지 않는다."""
    return ("근거" in head and "인용" in head) or head.strip() == "근거·인용"


def _sentences(model: DocModel):
    """(파일, 문단 시작줄, 문장) — 「근거·인용」 항은 뺀다."""
    style = _style(model)
    for name, text in _texts(model).items():
        for start, para, head in _paras(text, style):
            if _is_cite_head(head):
                continue
            for s in SENT.split(para):
                s = s.strip()
                if s:
                    yield name, start, s


@gate("V27", samples=[
    Sample(sample_model(tree={"a.md": "가" * 161 + "다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "가" * 150 + "다.\n"}), expect=0),
])
def v27_sentence_length(model: DocModel) -> GateOutput:
    """문장 160자 넘음(문단으로 이어 붙여 셈 · 마크업·공백·영문 원어 풀이 뺌)."""
    out: list[Finding] = []
    for name, start, s in _sentences(model):
        n = len(re.sub(r"\s", "", MARKUP.sub("", strip_en_gloss(s))))
        if n > MAX_SENT:
            out.append(Finding(f"{name}:{start}", f"{n}자 — …{s[:40]}…"))
    return GateOutput(len(model.prose()), out)


@gate("V28", samples=[
    Sample(sample_model(tree={"a.md": "가는 — 나는 — 다이다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "가는 — 짧은 삽입 — 뒤에 이어지는 본문이 충분히 길다.\n"}), expect=0),
])
def v28_dash(model: DocModel) -> GateOutput:
    """한 문장에 줄표를 두 번 이상(짝 이룬 삽입구는 한 번)."""
    out: list[Finding] = []
    for name, start, s in _sentences(model):
        d = dash_uses(s)
        if d > MAX_DASH:
            out.append(Finding(f"{name}:{start}", f"줄표 {d}회 — …{s[:40]}…"))
    return GateOutput(len(model.prose()), out)


@gate("V29", samples=[
    Sample(sample_model(tree={"a.md": "값은 **가**와 **나**를 본다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "**주장.** 값은 **가**다.\n"}), expect=0),
])
def v29_bold_density(model: DocModel) -> GateOutput:
    """한 문단 볼드 둘 이상 — 문단 앞머리 짧은 명사형 러닝헤드는 표제라 세지 않는다."""
    style = _style(model)
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for start, para, _head in _paras(text, style):
            b = len(BOLD.findall(RUNIN.sub("", para, count=1)))
            if b > MAX_BOLD_PARA:
                out.append(Finding(f"{name}:{start}", f"한 문단 볼드 {b}개"))
    return GateOutput(len(texts), out)


# ═══ V35 낯선 표현 · V36 구성 설명 (prose_gates 129-164 · 924-929) ═══

PLAIN = [
    ("딛고 서다", re.compile(r"딛고\s*(?:서|선|섰)")),
    ("떠받치다", re.compile(r"떠받(?:치|쳐|친)")),
    ("손에 쥐다", re.compile(r"손에\s*쥐")),
    ("걷어내다", re.compile(r"걷어\s*(?:내|낸|냈|낼)")),
    ("되받다", re.compile(r"되받(?:아|는|은|을)")),
    ("여물다", re.compile(r"여물(?:어|었|게|기)")),
    ("길어 올리다", re.compile(r"길어\s*올")),
    ("못 박다", re.compile(r"못\s*박(?:는|은|아|았|을)")),
    ("갉아먹다", re.compile(r"갉아먹")),
    ("짚다", re.compile(r"(?<!넘겨)짚(?:는다|었다|어 둔다|어 본다|어 두|고 넘어)")),
]
_KNUM = r"(?:\d+|[한두세네다섯여섯일곱여덟아홉열]{1,3})"
LAYOUT = [
    ("표 읽는 법", re.compile(r"왼쪽\s*「[^」]{1,24}」\s*(?:열|칸)"
                          r"|「[^」]{1,24}」\s*(?:열|칸)(?:을|를)?\s*(?:따라|먼저 훑|위에서 아래로)")),
    ("표 읽는 법", re.compile(r"(?:가로|세로)로\s*읽으면|이 (?:표|그림)의 요점이다|(?:열|칸)이 이 표의 요점")),
    ("행·열 소개", re.compile(r"(?:두|세|네|다섯|여섯|일곱|여덟|\d+)\s*행(?:은|이)\s*[^.\n]{0,60}(?:이고|이며|를 맡고),?"
                          r"\s*[^.\n]{0,30}(?:열은|열이|열에는)")),
    ("표기 해명", re.compile(r"빠뜨린 것이 아니다|괄호는\s*[^.\n]{0,40}가리킨다")),
    ("길 안내", re.compile(r"이 절은\s*(?:먼저|이어|끝으로)|이 절만으로"
                        r"|「[^」]{2,40}」\s*항(?:에서|이)\s*(?:다룬다|다시 다룬다|이어받는다)")),
    ("길 안내", re.compile(r"다음 (?:절|장)(?:에서|이|은)\s*[^.\n]{0,40}(?:본다|다룬다|살핀다|살펴본다)\.")),
    ("기계 배치 설명", re.compile(r"(?:표|그림)는\s*왼쪽에\s*[^.\n]{0,80}(?:붙인다|놓는다|놓고|두고|붙입니다|놓습니다|둡니다)"
                             r"|오른쪽에\s*[^.\n]{0,40}(?:붙인다|붙입니다)")),
    ("기계 배치 설명", re.compile(r"행은\s*" + _KNUM + r"\s*개(?:\s*\([^)\n]{0,40}\))?(?:이고|이며|,)\s*열은\s*"
                             + _KNUM + r"\s*개")),
    ("기계 배치 설명", re.compile(r"상자는\s*" + _KNUM + r"\s*개(?:다|이다|이며|이고|입니다)")),
]


def _para_patterns(model: DocModel, patterns, gid_msg_len: int) -> GateOutput:
    style = _style(model)
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for start, para, _head in _paras(text, style):
            for label, rx in patterns:
                for m in rx.finditer(para):
                    out.append(Finding(f"{name}:{start}", f"{label} — …{m.group(0)[:gid_msg_len]}…"))
    return GateOutput(len(texts), out)


@gate("V35", samples=[
    Sample(sample_model(tree={"a.md": "현장이 손에 쥐는 것\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "결과를 넘겨짚는다\n"}), expect=0),
])
def v35_plain(model: DocModel) -> GateOutput:
    """일반 독자에게 낯선 비유·문어투 — 뜻이 하나뿐인 것만."""
    return _para_patterns(model, PLAIN, 40)


@gate("V36", samples=[
    Sample(sample_model(tree={"a.md": "행은 6개이고 열은 4개다\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "관수량은 열에 따라 다르다\n"}), expect=0),
])
def v36_layout(model: DocModel) -> GateOutput:
    """내용이 아니라 문서·표의 구성을 설명하는 문장."""
    return _para_patterns(model, LAYOUT, 50)


# ═══ V41 서수 나열 문단 (prose_gates 417-419 · 832-843) ═══

ORDINAL = re.compile(r"(첫째|둘째|셋째|넷째|다섯째|여섯째|일곱째)(?=[,·]\s)")
LIST_OR_TABLE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||#|>|!!!)")


@gate("V41", samples=[
    Sample(sample_model(tree={"a.md": "첫째, 관리를 본다. 둘째, 근거를 밝힌다. 셋째, 경계를 정한다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "첫째, 하나. 둘째, 둘.\n"}), expect=0),
])
def v41_ordinals(model: DocModel) -> GateOutput:
    """한 줄(문단)에 「첫째, … 둘째, … 셋째,」가 셋 이상 — 번호 목록으로."""
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        infence = False
        for i, line in enumerate(text.split("\n")):
            if line.lstrip().startswith("```"):
                infence = not infence
                continue
            if infence or LIST_OR_TABLE.match(line):
                continue
            n = len(set(ORDINAL.findall(line)))
            if n >= 3:
                out.append(Finding(f"{name}:{i + 1}", f"서수 나열 {n}개 — 번호 목록으로"))
    return GateOutput(len(texts), out)


# ═══ V41W 흩어진 서수 나열 — V41 넓힘 (prose_gates 1730-1770 · check_v2 1592-1602) ═══

_ORD = "첫째|둘째|셋째|넷째|다섯째|여섯째|일곱째"
_ORD_ORDER = _ORD.split("|")
ORD_SCATTER = re.compile(rf"(?:^|(?<=[.。]\s)|(?<=의\s))({_ORD})(?:,\s|\s?([가-힣]{{1,6}}?)(?:은|는|이|가|으로|로)\s)")


def scattered_ordinals(text: str) -> list[tuple[int, str]]:
    """(줄, 메시지) — 한 항(`##`·`###`) 안의 목록이 아닌 문단들에 서수가 흩어진 자리.

    같은 낱말을 받는 서수가 둘 이상이거나 서로 다른 문단에 서수가 셋 이상. 한 줄 안의 셋 이상은 V41 몫.
    """
    out: list[tuple[int, str]] = []
    fence = False
    cur: list[tuple[int, str, str]] = []

    def flush():
        if not cur:
            return
        lines = {ln for ln, _, _ in cur}
        ords = {o for _, o, _ in cur}
        by_noun: dict[str, set] = {}
        for _, o, nn in cur:
            if nn:
                by_noun.setdefault(nn, set()).add(o)
        same = max((len(v) for v in by_noun.values()), default=0)
        if len(lines) >= 2 and (same >= 2 or len(ords) >= 3):
            out.append((cur[0][0], f"흩어진 서수 나열 {len(ords)}개 — "
                                   f"{'·'.join(sorted(ords, key=_ORD_ORDER.index))}"))

    for i, line in enumerate(text.split("\n")):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if re.match(r"^#{2,3}\s", line):
            flush()
            cur = []
            continue
        if LIST_OR_TABLE.match(line) or not line.strip():
            continue
        ms = list(ORD_SCATTER.finditer(line.strip()))
        if len({m.group(1) for m in ms}) >= 3:
            continue
        for m in ms:
            cur.append((i + 1, m.group(1), m.group(2) or ""))
    flush()
    return out


@gate("V41W", samples=[
    Sample(sample_model(tree={"a.md": "## 1. 가\n\n첫째 축은 시간이다.\n\n둘째 축은 공간이다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "## 1. 가\n\n첫째 해에는 심는다. 둘째 해에는 거둔다.\n"}), expect=0),
])
def v41w_scattered_ordinals(model: DocModel) -> GateOutput:
    """문단마다 흩어진 서수 나열(V41 넓힘, 시범). INDEX.md는 보지 않는다."""
    texts = {n: t for n, t in _texts(model).items() if n.rsplit("/", 1)[-1] != "INDEX.md"}
    out: list[Finding] = []
    for name, text in texts.items():
        for ln, msg in scattered_ordinals(text):
            out.append(Finding(f"{name}:{ln}", msg))
    return GateOutput(len(texts), out)


# ═══ V43 문서 주어 결손 (prose_gates 290 · 854-855) · V50 겹친 말 (302-305 · 881-883) ═══

DOC_LACK = re.compile(r"이\s?(?:문서|가이드|백과|책|편|절|장)(?:은|는|이|가|에서는|로서는)?\s[^.\n]{0,60}?"
                      r"(?:확보하지 못했|찾지 못했|구하지 못했|확인하지 못했|다루지 못했)")
DUP_WORD = re.compile(r"(?<![가-힣])((?:[가-힣]{2,})(?: [가-힣]{2,})?) \1(?![가-힣])")
DUP_OK = re.compile(r"^([가-힣]+[이가]) \1 [되된돼될]")


@gate("V43", samples=[
    Sample(sample_model(tree={"a.md": "이 문서는 확보하지 못했다\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "국내 기준은 아직 확인되지 않았다\n"}), expect=0),
])
def v43_doc_lack(model: DocModel) -> GateOutput:
    """「이 문서는 … 확보하지 못했다」 — 문서를 주어로 세운 자료 결손(표·펜스 밖)."""
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        infence = False
        for i, line in enumerate(text.split("\n")):
            if line.lstrip().startswith("```"):
                infence = not infence
                continue
            if infence or PROSE_SKIP.match(line):
                continue
            for m in DOC_LACK.finditer(line):
                out.append(Finding(f"{name}:{i + 1}", f"문서를 주어로 세운 결손 — {m.group(0)[:40]}"))
    return GateOutput(len(texts), out)


@gate("V50", samples=[
    Sample(sample_model(tree={"a.md": "조건이 다른 다른 연구의\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "기준이 있어야 표준이 표준이 된다\n"}), expect=0),
])
def v50_dup_words(model: DocModel) -> GateOutput:
    """같은 말이 공백 하나 사이로 되풀이 — 일괄 치환의 흔적. 펜스 밖(표 칸 포함)."""
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        infence = False
        for i, line in enumerate(text.split("\n")):
            if line.lstrip().startswith("```"):
                infence = not infence
                continue
            if infence:
                continue
            for m in DUP_WORD.finditer(line):
                if not DUP_OK.match(line[m.start():m.end() + 3]):
                    out.append(Finding(f"{name}:{i + 1}", f"겹친 말 — {m.group(0)[:30]}"))
    return GateOutput(len(texts), out)


# ═══ V53 · V54 · V56 · V69 — 줄 단위 v2.2 게이트 (prose_gates 314-354 · 564-568 · 693-782) ═══

LAYOUT_WORDS = re.compile(
    r"위에서 아래로|아래에서 위로|왼쪽에서 오른쪽|오른쪽에서 왼쪽|왼쪽(?:에|은|의|부터|으로)|오른쪽(?:에|은|의|으로|끝)|"
    r"맨 위|맨 아래|위쪽(?:에|은)|아래쪽(?:에|은)|가운데(?:에|로) (?:놓|있|두)|점선|실선|"
    r"상자(?:에|는|가|로|들|마다|안|를|와)|화살표|가지(?:가|로) (?:갈|나뉘)|갈라진다|마름모|육각형")
FIG_CAP_LINE = re.compile(r"^(?:\*\*(?:그림|차트)\s*[\dA-Za-z][\w.\-]*\.\*\*"
                          r"|(?:그림|차트)\s[\dA-Za-z][0-9A-Za-z.\-]*\.(?=\s|$))")
_GUIDE_HEAD = r"\d+\.\d+절|제?\d+장|별첨 [A-Z]|표 \S+|그림 \S+"
_GUIDE_TAIL = (r")(?:의 \S+)?(?:에|이|을|를|에서|에게|으로)?\s*"
               r"(?:있다|자세히 안내한다|안내한다|모아 두었다|정리하였다|정리했다|보면 된다|참고하면 된다"
               r"|참고한다|다룬다)\.$")
CAPTION_CALL = re.compile(r"^(?P<subj>[^.]{4,70}?)(?:은|는|이|가)\s+(?P<k>표|그림)\s(?P<n>[\dA-Z][\w.\-]*?)"
                          r"[와과]\s같다\.$")
# 「이 문서의 해석이다」 꼴(F114) — 서술어(이다·이며)로 끝나는 자기 선언만. 괄호 출처 표시
# 「(이 문서의 정리)」는 서술어가 없어 잡지 않는다
SELF_DECL = re.compile(r"것이 이 문서의|이 문서의 (?:정식화|위상|독자는|기여|핵심 명제)|독자는 [^.]{0,40}셋이다"
                       r"|그치지 않고 [^.]{0,40}이 문서"
                       r"|(?<!것이 )이 문서의 (?:해석|판단|선택|정리)(?:이다|이며)")
_TABLE_READ_REST = (
    r"(?:에서|의|을 보면|를 보면)[^.\n]{0,50}?(?<=[\s)」'’])(?:열|행|칸)(?! 편| 가지| 개)(?=[을를이가은는에의과와(,]|\s|$)"  # noqa: RUF001
    r"|(?<![가-힣])(?:열|칸|항목|행)(?:이|은|는|에) ?[「'‘][^」'’]{1,30}[」'’](?:인|이라고|으로 적힌|로 적힌)\s"  # noqa: RUF001
    r"|[「'‘][^」'’]{1,30}[」'’](?:인|이라고 적힌|으로 적힌|로 적힌) (?:행|항목|칸|열)"  # noqa: RUF001
    r"|(?:첫째|둘째|셋째|넷째|다섯째|마지막) (?:항목|행|열|칸)(?:을|를|은|는) ?[「'‘]"  # noqa: RUF001
    r"|(?<![가-힣])(?:열|행|칸)을 (?:위에서부터|아래로|차례로|따라) ?읽")
TABLE_READ = re.compile(r"(?:표|그림) ?\d+(?:\.[0-9A-Z]+)*-\d+" + _TABLE_READ_REST)
# roman(F82) — 「표 II.6-1」도 표 번호로
TABLE_READ_ROMAN = re.compile(r"(?:표|그림) ?(?:" + ROMAN + r"|\d+)(?:\.[0-9A-Z]+)*-\d+" + _TABLE_READ_REST)
_CAP_KEY = (re.compile(r"^\*\*(표|그림|차트)\s*([\dA-Za-z][\w.\-]*)\.\*\*\s*(.*)$"),
            re.compile(r"^(표|그림|차트)\s([\dA-Za-z][0-9A-Za-z.\-]*)\.\s+(.*)$"))


def caption_overlap(subj: str, cap: str) -> float:
    """문장 주어가 표 제목을 얼마나 되풀이하는가 — 낱말(2자 이상) 앞 두 글자 기준."""
    w = {x[:2] for x in re.findall(r"[가-힣A-Za-z0-9]{2,}", subj) if x != "이문"}
    c = {x[:2] for x in re.findall(r"[가-힣A-Za-z0-9]{2,}", cap)}
    return len(w & c) / len(w) if w else 0.0


def _guide_sent(model: DocModel) -> re.Pattern:
    """개요의 안내 문장 — 「…편」 같은 문서 이름 꼴은 `extra.prose.guide_words`(정규식 조각)로 더한다."""
    head = _GUIDE_HEAD
    if _style(model) == "roman":
        head = ROMAN + r"\.\d+절|" + head
    words = "".join("|" + str(w) for w in _prose_cfg(model).get("guide_words") or [] if str(w))
    return re.compile(r"(?:" + head + words + _GUIDE_TAIL)


def _overview(name: str, model: DocModel) -> bool:
    """개요 파일인가 — `extra.prose.overview_prefixes`(기본 「개요/」 폴더)."""
    prefixes = tuple(str(p) for p in _prose_cfg(model).get("overview_prefixes") or ("개요/",))
    return name.startswith(prefixes)


def _line_hits(model: DocModel, want: str) -> GateOutput:
    """원본 v2.2 줄 루프 — 펜스·빈 줄·표제를 건너뛰고 한 게이트의 지적만 모은다."""
    texts = _no_index(_texts(model))
    style = _style(model)
    table_read = TABLE_READ_ROMAN if style == "roman" else TABLE_READ
    guide = _guide_sent(model) if want == "V54" else None
    out: list[Finding] = []
    for name, text in texts.items():
        lines = text.split("\n")
        caps: dict[tuple[str, str], str] = {}
        if want == "V54":
            for ln in lines:
                cm = _CAP_KEY[0].match(ln.strip()) or _CAP_KEY[1].match(ln.strip())
                if cm:
                    caps[(cm.group(1), cm.group(2))] = cm.group(3)
        overview = _overview(name, model)
        fence = False
        for i, ln in enumerate(lines):
            if ln.strip().startswith("```"):
                fence = not fence
                continue
            if fence or not ln.strip():
                continue
            if HEADING.match(ln):
                continue
            loc = f"{name}:{i + 1}"
            if want == "V56":
                for m in SELF_DECL.finditer(ln):
                    out.append(Finding(loc, f"문서 자기 선언 — {ln[max(0, m.start() - 16):m.end() + 10]}"))
            elif want == "V69":
                if not ln.lstrip().startswith(("|", "**표", "**그림")) and not is_cap_line(ln, style):
                    for m in table_read.finditer(ln):
                        out.append(Finding(loc, f"표 읽어 주기 — {ln[max(0, m.start() - 12):m.end() + 12]}"))
            elif want == "V53":
                if FIG_CAP_LINE.match(ln.strip()):
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines):
                        nxt = lines[j]
                        m = LAYOUT_WORDS.search(nxt)
                        if m and not nxt.lstrip().startswith(("|", "```", "#", "**표", "**그림")) \
                                and not is_cap_line(nxt, style):
                            out.append(Finding(f"{name}:{j + 1}",
                                               f"그림 구성 설명 — {nxt[max(0, m.start() - 16):m.end() + 16]}"))
            elif want == "V54":
                if ln.lstrip().startswith(("|", ">", "!!!", "**표", "**그림", "**차트")) or is_cap_line(ln, style):
                    continue
                for s in re.split(r"(?<=다\.)\s+", ln.strip()):
                    if overview and guide.search(s) and len(s) < 80:
                        out.append(Finding(loc, f"안내 문장 — {s[:50]}"))
                    cc = CAPTION_CALL.match(s)
                    if cc and caption_overlap(cc.group("subj"),
                                              caps.get((cc.group("k"), cc.group("n")), "")) >= 0.5:
                        out.append(Finding(loc, f"제목 되풀이 호출 — {s[:50]}"))
    return GateOutput(len(texts), out)


@gate("V53", samples=[
    Sample(sample_model(tree={"a.md": "**그림 1.1-1.** 흐름\n\n위에서 아래로 네 부가 이어진다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "**그림 1.1-1.** 흐름\n\n잎을 세어 평균을 낸다.\n"}), expect=0),
])
def v53_figure_layout(model: DocModel) -> GateOutput:
    """그림 캡션 바로 아래 문단이 배치(위에서 아래로·상자·화살표·점선)를 옮겨 적는가."""
    return _line_hits(model, "V53")


@gate("V54", samples=[
    Sample(sample_model(tree={"개요/0.1. 가.md": "경계와 그것을 다루는 편은 0.2절에 있다.\n"}), expect=1),
    Sample(sample_model(tree={"개요/0.1. 가.md": "이 값은 12.3절의 기준온도를 쓴다.\n"}), expect=0),
])
def v54_guide_and_caption_call(model: DocModel) -> GateOutput:
    """개요의 짧은 안내 문장(다른 자리를 가리키기만) · 「X는 표 N과 같다」로 표 제목을 되풀이하는 호출."""
    return _line_hits(model, "V54")


@gate("V56", samples=[
    Sample(sample_model(tree={"a.md": "이 문서의 독자는 농가다\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "이 문서는 농가를 대상으로 작성되었다\n"}), expect=0),
])
def v56_self_declaration(model: DocModel) -> GateOutput:
    """문서가 자기 기여·독자를 선언하는 꼴."""
    return _line_hits(model, "V56")


@gate("V69", samples=[
    Sample(sample_model(tree={"a.md": "표 10.2-1의 등급 칸을 순서 코드로\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "처방은 이행 기록과 함께(표 9.1-2) 남긴다\n"}), expect=0),
])
def v69_table_reading(model: DocModel) -> GateOutput:
    """본문이 표의 열·행·칸 이름과 값을 라벨처럼 옮겨 적는가(표 줄·캡션 밖)."""
    return _line_hits(model, "V69")


# ═══ V76 띄어쓰기 (prose_gates 1166-1236 · 1948-1949) ═══

# 받침이 ㄹ인 한글 음절 전체(관형형 어미 -ㄹ: 할·될·볼·있을 …)
_L_FINAL = "[" + "".join(chr(0xAC00 + i * 28 + 8) for i in range(19 * 21)) + "]"
# 보지 않는 자리 — 인라인 코드·링크 주소·HTML 태그·주소·REF 표지(같은 길이 빈칸으로 덮어 자리를 지킨다)
_QMASK = re.compile(r"`[^`\n]*`|\]\([^)]*\)|<[^>\n]*>|https?://\S+|\[(?:USER-)?REF-[^\]]*\]")


@lru_cache(maxsize=16)
def _spacing(layers: tuple = ()) -> tuple:
    """띄어쓰기 목록 — 층 사전이 본체를 덮거나(`extend: true`면) 잇는다."""
    out = []
    for it in (load_dict("spacing_list.json", list(layers)) or {}).get("items") or []:
        try:
            rx = re.compile(it["re"].replace("{ㄹ받침}", _L_FINAL))
            ex = [re.compile(e.replace("{ㄹ받침}", _L_FINAL)) for e in it.get("except") or []]
        except (re.error, KeyError):
            continue
        out.append((it, rx, ex))
    return tuple(out)


def spacing_hits(line: str, layers: tuple = ()) -> list:
    """(항목, 맞은 자리) — 제외 규칙은 맞은 자리 앞뒤 8자 안에서 본다."""
    s = _QMASK.sub(lambda m: " " * len(m.group(0)), line)
    hits = []
    for it, rx, ex in _spacing(layers):
        for m in rx.finditer(s):
            ctx = s[max(0, m.start() - 8):min(len(s), m.end() + 8)]
            if any(e.search(ctx) for e in ex):
                continue
            hits.append((it, m))
    return hits


@gate("V76", samples=[
    Sample(sample_model(tree={"a.md": "측정할수 있다\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "측정할 수 있다\n"}), expect=0),
])
def v76_spacing(model: DocModel) -> GateOutput:
    """국립국어원 기준으로 확실한 띄어쓰기 틀린 꼴(본체 사전 `dicts/spacing_list.json`)."""
    texts = _no_index(_texts(model))
    layers = layers_key(model)
    out: list[Finding] = []
    for name, text in texts.items():
        fence = False
        for i, ln in enumerate(text.split("\n")):
            if ln.strip().startswith("```"):
                fence = not fence
                continue
            if fence or not ln.strip():
                continue
            for it, m in spacing_hits(ln, layers):
                out.append(Finding(f"{name}:{i + 1}",
                                   f"띄어쓰기 {it['id']} 「{m.group(0).strip()}」→「{it['right']}」 — "
                                   f"{ln[max(0, m.start() - 10):m.end() + 6].strip()}"))
    return GateOutput(len(texts), out)


# ═══ V81 굵은 글씨 (prose_gates 1480-1582 · 1992-1993) ═══

_BOLD_ANY = re.compile(r"\*\*([^*\n]+?)\*\*|<strong>(.*?)</strong>|<b>(.*?)</b>")
_LIST_HEAD = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
_CAP_LABEL = re.compile(r"^\s*(?:\*\*(?:표|그림|차트|사진|다이어그램)\s*[\w.\-]+\.\*\*|" + CAP_PLAIN + ")")
_NUM_ONLY = re.compile(r"^[\s\d.,%~∼\-–+×/()℃㎜]+$")  # noqa: RUF001
# 플러그인 렌더러(markdown_tree)가 절 끝에 내는 인용 목록 줄 — 렌더러 꼴이라 기본으로 안다
DEFAULT_CITED_REFS = r"^\*\*인용 참고문헌"


@lru_cache(maxsize=16)
def _repeat_max(layers: tuple = ()) -> int:
    lim = (load_dict("gate_limits.json", list(layers)) or {}).get("V81") or {}
    return int(lim.get("repeat_max_chars") or 30)


def _bkey(s: str) -> str:
    return re.sub(r"[\s.,:;·「」『』()\[\]—–\-]", "", s)  # noqa: RUF001


def _cell_index(row: str, pos: int) -> int:
    return row[:pos].count("|") - 1


def bold_issues(texts: dict[str, str], markers: dict | None = None,
                layers: tuple = ()) -> list[tuple[str, int, str]]:
    """(파일, 줄, 메시지) — ① 정의 자리 밖 반복 굵게 ③ 목록 머리말 일부만 굵게
    ④ 표제·캡션·표 칸·숫자만·목표 상자·결론 안 굵게.

    `markers`: `goalbox`(목표 상자 줄의 표식 글자, 기본 없음) · `conclusion`(결론 항 `##` 표제 정규식,
    기본 없음) · `cited_refs`(절 끝 인용 목록 줄 정규식, 기본 렌더러 꼴).
    """
    markers = markers or {}
    goalbox = str(markers.get("goalbox") or "")
    conc = markers.get("conclusion")
    conc_rx = re.compile(conc) if conc else None
    cited = markers.get("cited_refs", DEFAULT_CITED_REFS)
    cited_rx = re.compile(cited) if cited else None
    repeat_max = _repeat_max(layers)
    out: list[tuple[str, int, str]] = []
    seen: dict[str, str] = {}
    for name, text in texts.items():
        if name.endswith("INDEX.md"):
            continue
        lines = text.split("\n")
        fence, in_con, tbl_row = False, False, 0
        lists: dict[int, list] = {}

        def close(upto: int = -1, name=name, lists=lists):
            for ind in sorted([k for k in lists if k > upto], reverse=True):
                items = lists.pop(ind)
                nb = sum(1 for _, b in items if b)
                if len(items) >= 2 and 0 < nb < len(items):
                    out.append((name, items[0][0], f"목록 머리말 일부만 굵음({nb}/{len(items)})"))

        for i, ln_text in enumerate(lines):
            ln = i + 1
            if ln_text.strip().startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            s = ln_text.strip()
            if not s:
                continue
            hm = re.match(r"^(#{1,6})\s+(.*)$", ln_text)
            if hm:
                close()
                in_con = bool(conc_rx and conc_rx.search(hm.group(2))) and len(hm.group(1)) == 2
                if _BOLD_ANY.search(hm.group(2)):
                    out.append((name, ln, f"표제 안 굵게 — {hm.group(2)[:30]}"))
                tbl_row = 0
                continue
            if s.startswith("|"):
                tbl_row = tbl_row + 1 if tbl_row else 1
                if tbl_row >= 3 and _BOLD_ANY.search(s):  # 1 = 머리행, 2 = 가름줄
                    m = _BOLD_ANY.search(s)
                    where = "표 첫 열(행 머리) 굵게" if _cell_index(s, m.start()) == 0 else "표 칸 안 굵게"
                    out.append((name, ln, f"{where} — {(m.group(1) or m.group(2) or m.group(3) or '')[:24]}"))
                continue
            tbl_row = 0
            if cited_rx and cited_rx.match(s):  # 절 끝 인용 목록 줄 — 결론 항 밖, 굵은 머리는 렌더러 꼴
                in_con = False
                continue
            if goalbox and goalbox in s and _BOLD_ANY.search(s):
                out.append((name, ln, "「이 절의 목표」 상자 안 굵게"))
                continue
            if _CAP_LABEL.match(s):
                rest = _CAP_LABEL.sub("", s)
                if _BOLD_ANY.search(rest):
                    out.append((name, ln, f"캡션 안 굵게 — {rest[:30]}"))
                continue
            lm = _LIST_HEAD.match(ln_text)
            if lm:
                ind = len(lm.group(1).replace("\t", "    "))
                close(ind)
                lists.setdefault(ind, []).append((ln, lm.group(2).startswith(("**", "<strong>", "<b>"))))
                body = lm.group(2)
            else:
                if not ln_text.startswith((" ", "\t")):
                    close()
                body = s
            if in_con and _BOLD_ANY.search(body):
                out.append((name, ln, "결론 안 굵게"))
            for m in _BOLD_ANY.finditer(body):
                t = (m.group(1) or m.group(2) or m.group(3) or "").strip()
                if _NUM_ONLY.match(t):
                    out.append((name, ln, f"숫자만 굵게 — {t[:16]}"))
                    continue
                # 목록 머리말·러닝헤드(「**주의** …」 — 조사가 붙으면 문장의 일부라 아님)·핵심 문장은 ① 밖
                head = m.start() == 0 and (lm is not None or t.endswith((".", ":"))
                                           or body[m.end():].lstrip().startswith(("—", "–", ":", "-"))  # noqa: RUF001
                                           or (bool(RUNIN.match(body)) and body[m.end():m.end() + 1] in ("", " ")))
                if head or len(t) > repeat_max:
                    continue
                k = _bkey(t)
                if len(k) < 2:
                    continue
                if k in seen:
                    out.append((name, ln, f"정의 자리 밖 반복 굵게 — {t[:24]} (처음 {seen[k]})"))
                else:
                    seen[k] = f"{name.rsplit('/', 1)[-1][:24]}:{ln}"
        close()
    return out


@gate("V81", samples=[
    Sample(sample_model(tree={"a.md": "값은 **12.5%** 이다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "- **입력** — 값\n- **출력** — 값\n"}), expect=0),
])
def v81_bold(model: DocModel) -> GateOutput:
    """굵은 글씨 — 정의 자리 밖 반복·목록 머리말 일부만·표제/캡션/표 칸/숫자만/목표 상자/결론 안."""
    texts = _no_index(_texts(model))
    markers = _prose_cfg(model).get("markers") or {}
    out = [Finding(f"{n}:{ln}", msg) for n, ln, msg in bold_issues(texts, markers, layers_key(model))]
    return GateOutput(len(texts), out)
