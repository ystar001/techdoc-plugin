"""캡션·도표 게이트 — V6·V12·V15·V17·V18·V40·V62·V63·V66·V73·V75·V80 (v1.11-b, F85·F82).

시리즈 check_v2(카드 게이트 V6·V12·V15·V17·V18)와 prose_gates(산문 게이트 나머지)에서 판정 로직을
그대로 옮기고 입력만 DocModel로 바꿨다.

- **시리즈 고유 값은 설정으로**(E17): 설명 문단을 두지 않는 표 제목(`extra.caption.skip_table_titles`,
  기본 「개정 이력·판 이력」), 근거 등급 열을 요구하는 표준표 캡션 낱말(`standard_table_words`, 기본 빔
  → V40 대상 없음), 축이 있는 그래프 종류·축 이름 키(`chart_axis_types`·`chart_axis_keys` — 기본은
  원본 집합에 플러그인 `scripts/generate_chart`의 `comparison`과 `x_label`/`y_label`을 더함).
- **번호 꼴**: arabic(기본)이면 원본 정규식 그대로. roman이면 ① 번호 뒤 마침표 없는 캡션
  「**표 I.1-1 제목**」을 캡션으로 본다(`numbering.normalize_captions`, F82) ② 표의 참조 열(V62)
  값에 로마 숫자 절 번호 「II.6」을 더 받는다. 별첨 문자 범위는 `appendix_letters`.

지적 위치: 카드 게이트 `"<카드>|<섹션키>: …"`(V12는 원본 hit 키 `(cid, "-")`라 `"<카드>|-: …"`),
면제를 적용하지 않던 V6은 `"<카드> 도표: …"`. 산문 게이트 `"<상대 경로>:<줄>"`.
원본이 한 자리를 n건으로 세던 곳(V6 결손 수·V12 결번 수)은 같은 지적을 n개 낸다.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache

from techdoc_core.card_id import parse_card_id_parts
from techdoc_core.qc.card_text import card_texts
from techdoc_core.qc.dicts import load_dict
from techdoc_core.qc.gates.structure import CAP_DEF_CHART, CAP_OPEN, base_id, cap_defs
from techdoc_core.qc.model import DocModel
from techdoc_core.qc.numbering import appendix_letters, normalize_captions
from techdoc_core.qc.prose import strip_en_gloss
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model


def _style(model: DocModel) -> str:
    return (model.numbering or {}).get("section") or "arabic"


def _cfg(model: DocModel) -> dict:
    return (model.extra or {}).get("caption") or {}


def _card(body: str, title: str = "") -> dict:
    return {"sections": {"s1": {"title": title, "body": body}}}


def _card_texts(model: DocModel, card: dict) -> list[tuple[str, str, str]]:
    """카드 글(원본 texts) — roman이면 번호 뒤 마침표 없는 캡션을 원본 꼴로(F82)."""
    style = _style(model)
    return [(k, t, normalize_captions(b, style)) for k, t, b in card_texts(card)]


def _texts(model: DocModel) -> dict[str, str]:
    """산문 게이트 입력(원본 prose_gates.run의 texts)."""
    style = _style(model)
    return {tf.rel: normalize_captions(tf.text, style) for tf in model.prose()}


def _no_index(texts: dict[str, str]) -> dict[str, str]:
    return {n: t for n, t in texts.items() if not n.endswith("INDEX.md")}


TABLE = "| 가 | 나 |\n|---|---|\n| 1 | 2 |"


# ═══ V6 캡션·본문 연계 (check_v2 697-719 · 821-826 · 1311-1353) ═══

# 구분선에는 하이픈이 하나라도 있어야 한다 — 빈칸만 있는 서식 행은 구분선이 아니다
TBL_SEP = re.compile(r"^\s*\|[\s:|-]*-[\s:|-]*\|\s*$", re.M)
FENCE = re.compile(r"```(mermaid|chart)")
IMG = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
MAX_CAPTION_CHARS = 90  # 캡션은 제목 — 길이는 상한으로 잰다
CALLOUT = re.compile(r"^(\s*)!!!\s+\S+", re.M)
_CAP_TEXT = re.compile(
    r"^(?:\*\*(?:그림|표|차트|사진|다이어그램)\s*[\dA-Za-z][\w.\-]*\.?\*\*"
    r"|(?:그림|표|차트|사진|다이어그램)\s[\dA-Za-z][0-9A-Za-z.\-]*\.(?=\s))[ \t]*([^\n]*)", re.M)
_CAP_LINE_STRIP = re.compile(
    r"\*\*(?:그림|표|차트|사진|다이어그램)\s*[\dA-Za-z][\w.\-]*\.?\*\*[^\n]*"
    r"|(?<![^\n])(?:그림|표|차트|사진|다이어그램)\s[\dA-Za-z][0-9A-Za-z.\-]*\.(?=\s)[^\n]*")


def strip_callouts(body: str) -> str:
    """콜아웃 상자의 안쪽을 지운다 — 상자 안 표는 본문 도표가 아니다(빈 줄은 상자를 끊지 않는다)."""
    lines = body.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = CALLOUT.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        base = len(m.group(1))
        out.append(lines[i])
        i += 1
        while i < len(lines):
            s = lines[i]
            if s.strip() and (len(s) - len(s.lstrip())) <= base:
                break
            i += 1
    return "\n".join(out)


def _is_front(cid: str, model: DocModel) -> bool:
    """앞부분(0.x) 카드 — 표에 번호 없는 제목을 단다(원본 `cid.startswith("0.")`)."""
    return cid.startswith("0.") or parse_card_id_parts(cid, model.numbering).kind == "front"


@gate("V6", samples=[
    Sample(sample_model(cards={"1.1": _card(TABLE)}), expect=1),
    Sample(sample_model(cards={"1.1": _card(f"**표 1.1-1.** 값\n\n{TABLE}\n\n표 1.1-1은 값을 보인다.")}),
           expect=0),
])
def v6_caption_links(model: DocModel) -> GateOutput:
    """도표 수 대비 캡션 결손, 캡션 90자 초과, 본문이 번호로 부르지 않는 도표(원본: 면제 없음)."""
    out: list[Finding] = []
    for cid, card in model.cards.items():
        whole = "\n".join(b for _, _, b in _card_texts(model, card))
        vis_src = strip_callouts(whole)
        fences = FENCE.findall(vis_src)
        vis = (len(TBL_SEP.findall(vis_src)) + fences.count("mermaid") + fences.count("chart")
               + len(IMG.findall(vis_src)))
        caps = cap_defs(whole)
        short = sum(1 for m in _CAP_TEXT.finditer(whole) if len(m.group(1)) > MAX_CAPTION_CHARS)
        loc = f"{cid} 도표"
        if vis and len(caps) < vis and not _is_front(cid, model):
            out += [Finding(f"{loc}: 캡션 결손", f"{cid} 캡션 결손 {vis - len(caps)}/{vis}")] * (vis - len(caps))
        if short:
            out += [Finding(f"{loc}: 캡션 길이",
                            f"{cid} 캡션 {MAX_CAPTION_CHARS}자 초과 {short}")] * short
        body_only = _CAP_LINE_STRIP.sub("", whole)
        uncalled = [f"{k} {n.rstrip('.')}" for k, n in caps
                    if not re.search(
                        rf"{'(?:그림|차트|사진|다이어그램)' if k != '표' else '표'}\s*"
                        rf"{re.escape(n.rstrip('.'))}(?![\d\-.])", body_only)]
        if uncalled:
            msg = (f"{cid} 본문이 부르지 않는 도표 {len(uncalled)}/{vis}: " + ", ".join(uncalled[:5])
                   + (" …" if len(uncalled) > 5 else ""))
            out += [Finding(f"{loc}: 부르지 않음", msg)] * len(uncalled)
    return GateOutput(len(model.cards), out)


# ═══ V12 도표 번호 정합 (check_v2 257-318 · 449 · 1360-1376) ═══

NUM_CAP = re.compile(CAP_OPEN + r"(그림|표|차트|사진|다이어그램)\s*([\dA-Za-z][\w.\-]*?)\.(?:\*\*|\s)")
_NUM_TAIL = re.compile(r"(?:^|-)\d+$")


def num_seq(whole: str) -> list[tuple[str, str]]:
    """번호가 붙은 도표를 등장 순서대로 — 마크다운 캡션과 차트 caption을 위치로 병합."""
    got = [(m.start(), m.group(1), m.group(2)) for m in NUM_CAP.finditer(whole)]
    got += [(m.start(), m.group(1), m.group(2)) for m in CAP_DEF_CHART.finditer(whole)]
    got.sort(key=lambda x: x[0])
    return [(k, n) for _, k, n in got]


def fig_number_issues(seq: list, label_id: str) -> list[tuple[int, str]]:
    """등장 순서의 도표 번호 → (건수, 메시지) — 역전·결번·0번·「그림」「차트」 번호 충돌."""
    out: list[tuple[int, str]] = []
    charts = [n for k, n in seq if k == "차트"]
    figs = [n for k, n in seq if k in ("그림", "다이어그램")]
    if charts and figs and (set(charts) & set(figs)):
        dupes = sorted(set(charts) & set(figs))
        out.append((len(dupes), f"{label_id} 「그림」·「차트」 번호 충돌 {len(dupes)}건: {', '.join(dupes)}"))
    for kind_group, label in (("표", "표"), (("그림", "차트", "다이어그램"), "그림")):
        got = [n for k, n in seq
               if (k == kind_group if isinstance(kind_group, str) else k in kind_group)]
        tails = []
        for n in got:
            m = re.search(r"(\d+)$", n)
            if m:
                tails.append(int(m.group(1)))
        if not tails:
            continue
        if 0 in tails:
            out.append((1, f"{label_id} {label} 0번 존재 (번호는 1부터)"))
        if tails != sorted(tails):
            bad = [f"{label} {n}" for n, t, prev in
                   zip(got[1:], tails[1:], tails[:-1], strict=False) if t < prev]
            out.append((len(bad), f"{label_id} {label} 번호가 등장 순서를 거스름: {', '.join(bad[:5])}"))
        missing = sorted(set(range(1, max(tails) + 1)) - set(tails))
        if missing:
            out.append((len(missing), f"{label_id} {label} 결번 {len(missing)}건: {missing[:6]}"))
    return out


def split_group_issues(seq: list, label_id: str) -> list[tuple[int, str]]:
    """분할 묶음 — 번호 접두(`4.4`·`11.3.XL1`)별로 계열을 갈라 본다."""
    by_pre: dict[str, list] = defaultdict(list)
    for k, n in seq:
        by_pre[_NUM_TAIL.sub("", n)].append((k, n))
    out: list[tuple[int, str]] = []
    for pre, s in by_pre.items():
        out += fig_number_issues(s, f"{label_id}·{pre or '-'}")
    return out


def _split_order(cid: str) -> tuple[str, int]:
    m = re.search(r"\.X?L(\d+)$", cid)
    return (base_id(cid), int(m.group(1)) if m else 0)


@gate("V12", samples=[
    Sample(sample_model(cards={"1.1": _card("**표 1.1-1.** 가\n\n**표 1.1-3.** 나\n")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("**표 1.1-1.** 가\n\n**표 1.1-2.** 나\n")}), expect=0),
])
def v12_figure_numbers(model: DocModel) -> GateOutput:
    """도표 번호 — 등장 순서 역전·결번·0번·「그림」「차트」 충돌. 분할 카드는 묶음의 첫 카드에서 한 번."""
    cards = model.cards
    groups: dict[str, list[str]] = defaultdict(list)
    for c in sorted(cards, key=_split_order):
        if base_id(c) != c:
            groups[base_id(c)].append(c)
    out: list[Finding] = []

    def whole(c: str) -> str:
        return "\n".join(b for _, _, b in _card_texts(model, cards[c]))

    for cid in cards:
        b = base_id(cid)
        if b == cid:
            issues = fig_number_issues(num_seq(whole(cid)), cid)
        elif groups[b] and groups[b][0] == cid:
            seq = [x for m in groups[b] for x in num_seq(whole(m))]
            issues = split_group_issues(seq, f"{b}(분할 {len(groups[b])})")
        else:
            continue
        for n, msg in issues:
            out += [Finding(f"{cid}|-: 도표 번호", msg)] * n
    return GateOutput(len(cards), out)


# ═══ V15 표 뒤 빈 줄 (check_v2 1150-1168) ═══

@gate("V15", samples=[
    Sample(sample_model(cards={"1.1": _card(f"{TABLE}\n다음 문단이다.")}), expect=1),
    Sample(sample_model(cards={"1.1": _card(f"{TABLE}\n\n다음 문단이다.")}), expect=0),
])
def v15_blank_after_table(model: DocModel) -> GateOutput:
    """표 마지막 행 바로 다음 줄이 문단이면 마크다운이 그 문단을 표의 한 행으로 삼킨다(펜스 밖)."""
    out: list[Finding] = []
    for cid, card in model.cards.items():
        for key, _title, body in _card_texts(model, card):
            lines = body.splitlines()
            in_fence = False
            for i, ln in enumerate(lines[:-1]):
                if ln.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence or not ln.strip().startswith("|"):
                    continue
                nx = lines[i + 1]
                if nx.strip().startswith("|") or not nx.strip():
                    continue
                out.append(Finding(f"{cid}|{key}: 표 뒤",
                                   f"{cid}·{key} 표 뒤에 빈 줄이 없다 — 다음 문단이 표에 삼켜진다: "
                                   f"{nx.strip()[:40]}"))
    return GateOutput(len(model.cards), out)


# ═══ V17 캡션 규약의 일관성 (check_v2 576-595 · 1209-1245) ═══

CAP_ANY = re.compile(r"^\*\*(그림|표|차트)\s*([\dA-Za-z][\dA-Za-z.\-]*?)(\.?)\*\*[ \t]*(.*)$")
CAP_ANY_PLAIN = re.compile(r"^(그림|표|차트)\s([\dA-Za-z][0-9A-Za-z.\-]*?)(\.)\s+(.*)$")
V17_NARRATIVE = re.compile(
    r"(?:했다|한다|된다|이다|었다|있다|없다|린다|난다|준다|는지|은지|을지|"
    r"보인다|드러낸다|나타낸다|정리했다|대비했다|모았다|"
    r"입니다|습니다|합니다|십시오)\.?$")
V17_ASK_WORD = re.compile(r"무엇|누구|누가|어디|언제|어느|어떻게|어떤|왜|얼마")
V17_QUESTION = re.compile(r"(?:나|까|는가|을까|일까)\.?$")
# 「하나」는 어미(앞말에 붙음)이기도 수사(띄어 섬)이기도 하다 — 앞자리 공백이 둘을 가른다
V17_CONNECT = re.compile(
    r"(?:(?<!\s)하나|으로|되어|이며|하며|하고|이고|되고|면서|는데|지만|되면|하면|"
    r"이라|라서|므로|어서|아서|거나|든지|도록|고자)\.?$")


def caption_line_defects(cap_line: str) -> list[str]:
    """캡션 정의줄 하나 → 결함 목록(원본 V17 차례). 캡션이 아니면 빈 목록."""
    cm = CAP_ANY.match(cap_line.strip()) or CAP_ANY_PLAIN.match(cap_line.strip())
    if not cm:
        return []
    out = []
    dot, cap = cm.group(3), cm.group(4).strip()
    if not dot:
        out.append("번호 뒤 마침표 없음")
    if not cap:
        out.append("제목 없음")
        return out
    if V17_NARRATIVE.search(cap):
        out.append(f"서술형 종결 「…{cap[-12:]}」")
    elif V17_ASK_WORD.search(cap) and V17_QUESTION.search(cap):
        out.append(f"물음꼴 캡션 「…{cap[-12:]}」")
    elif V17_CONNECT.search(cap):
        out.append(f"연결어미에서 끊김 「…{cap[-12:]}」")
    if cap.rstrip().endswith("."):
        out.append("캡션이 마침표로 끝남(제목이 아니라 문장)")
    if cap.count("(") != cap.count(")"):
        out.append("괄호가 짝을 잃음")
    if "[REF-" in cap:
        out.append("캡션에 출처 표기(설명이 단다)")
    if cap.count("|") >= 2:  # 캡션 통일 도구가 캡션 줄과 표 머리행을 한 줄로 합친 자리
        out.append("캡션이 표 머리행을 삼켰다")
    return out


@gate("V17", samples=[
    Sample(sample_model(cards={"1.1": _card("**표 1.1-1.** 값을 정리했다")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("**표 1.1-1.** 관측 항목과 주기")}), expect=0),
])
def v17_caption_conventions(model: DocModel) -> GateOutput:
    """캡션은 제목 — 번호 뒤 마침표·제목 있음·서술형/물음꼴/연결어미 종결·마침표 끝·괄호 짝·REF·머리행 삼킴."""
    out: list[Finding] = []
    caps = 0
    for cid, card in model.cards.items():
        for key, _title, body in _card_texts(model, card):
            for ln in body.split("\n"):
                cm = CAP_ANY.match(ln.strip()) or CAP_ANY_PLAIN.match(ln.strip())
                if not cm:
                    continue
                caps += 1
                where = f"{cid}·{key} {cm.group(1)} {cm.group(2)}"
                for d in caption_line_defects(ln):
                    out.append(Finding(f"{cid}|{key}: 캡션", f"{where} — {d}"))
    return GateOutput(caps, out)


# ═══ V18 도표 아래 설명 문단의 가독성 (check_v2 463-476 · 597-626 · 1170-1207) ═══

CAP_LINE_RE = re.compile(r"\*\*(그림|표|차트)\s*([\dA-Za-z][\w.\-]*)\.\*\*[ \t]*[^\n]*")
CAP_LINE_RE_PLAIN = re.compile(r"(?m)^(그림|표|차트)\s([\dA-Za-z][0-9A-Za-z.\-]*?)\.(?=\s)[ \t]*[^\n]*")
TBL_BLOCK = re.compile(r"(?:[ \t]*\|.*\|[ \t]*\n)+")
# 판 이력 표에는 설명 문단을 두지 않는다 — 관리용 표라 「눈을 어디에 둘지」가 없다
DEFAULT_SKIP_TABLE_TITLES = ("개정 이력", "판 이력")
V18_MAX_SENT = 160
V18_MAX_EMPH = 2
V18_MAX_LEN = 700
# 마침표를 문장 끝으로 — 「마다」·「보다」는 끝이 아니다. 닫는 강조·따옴표·괄호까지 지나야 끝
SENT_SPLIT = re.compile(r"(?<=[.!?])[*”’\"')\]]*\s+|(?<=다)\n")  # noqa: RUF001


def cap_lines(body: str) -> list[re.Match]:
    """캡션 정의줄(옛 꼴 + 정본 꼴) — 본문 차례대로."""
    return sorted(list(CAP_LINE_RE.finditer(body)) + list(CAP_LINE_RE_PLAIN.finditer(body)),
                  key=lambda m: m.start())


def _skip_title_re(model: DocModel) -> re.Pattern | None:
    """설명 문단을 두지 않는 표 제목 — `extra.caption.skip_table_titles`(정규식 조각 목록)."""
    words = _cfg(model).get("skip_table_titles")
    words = DEFAULT_SKIP_TABLE_TITLES if words is None else words
    words = [str(w) for w in words if str(w)]
    return re.compile("|".join(words)) if words else None


def description_defects(para: str) -> list[str]:
    bad = []
    longest = max((len(strip_en_gloss(s)) for s in SENT_SPLIT.split(para)), default=0)
    if longest > V18_MAX_SENT:
        bad.append(f"한 문장 {longest}자")
    if para.count("**") // 2 > V18_MAX_EMPH:
        bad.append(f"강조 {para.count('**') // 2}군데")
    if len(para) > V18_MAX_LEN:
        bad.append(f"문단 {len(para)}자")
    if para.count(")") > para.count("("):
        bad.append("여는 괄호 없이 닫힘")
    return bad


@gate("V18", samples=[
    Sample(sample_model(cards={"1.1": _card("**그림 1.1-1.** 흐름\n\n값은 크다) 그래서 본다.")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("**그림 1.1-1.** 흐름\n\n값은 위에서 아래로 흐른다.")}), expect=0),
])
def v18_description_readability(model: DocModel) -> GateOutput:
    """도표 아래 설명 문단(있을 때만) — 한 문장 160자·강조 2군데·문단 700자 초과·여는 괄호 없이 닫힘."""
    skip = _skip_title_re(model)
    out: list[Finding] = []
    caps = 0
    for cid, card in model.cards.items():
        for key, _title, body in _card_texts(model, card):
            for mm in cap_lines(body):
                if mm.group(1) == "표" and skip and skip.search(mm.group(0)):
                    continue
                caps += 1
                tail = body[mm.end():]
                if mm.group(1) == "표":  # 표는 캡션이 표 위 — 표를 건너뛴다
                    lead = len(tail) - len(tail.lstrip("\n"))
                    t = TBL_BLOCK.match(tail[lead:])
                    if t:
                        tail = tail[lead + t.end():]
                nxt = tail.lstrip("\n")
                first = nxt.split("\n", 1)[0].strip() if nxt else ""
                if (not first or first.startswith(("|", "!!!", "```", "- ", "#", "$$"))
                        or CAP_LINE_RE.match(first) or CAP_LINE_RE_PLAIN.match(first)):
                    continue
                para = nxt.split("\n\n", 1)[0].strip()
                bad = description_defects(para)
                if bad:
                    out.append(Finding(f"{cid}|{key}: 설명",
                                       f"{cid}·{key} {mm.group(1)} {mm.group(2)} — {'·'.join(bad)}"))
    return GateOutput(caps, out)


# ═══ V40 표준표의 근거 등급 열 (prose_gates 280-283 · 422-434 · 893-900) ═══

EVIDENCE_COL = re.compile(r"근거|출처 ?등급|등급\s*\(근거\)")


def _std_caption_re(model: DocModel) -> re.Pattern | None:
    """캡션이 표준표·임계값을 말하는 표 — 낱말은 `extra.caption.standard_table_words`(기본 빔)."""
    words = [str(w) for w in _cfg(model).get("standard_table_words") or [] if str(w)]
    if not words:
        return None
    return re.compile(r"(?:\*\*표\s*[\w.\-]+\.\*\*|^\s*표\s[\dA-Za-z][0-9A-Za-z.\-]*\.(?=\s))\s*[^\n]*(?:"
                      + "|".join(words) + r")[^\n]*")


def table_header(lines: list[str], cap_i: int) -> str | None:
    """캡션 아래 세 줄 안의 표 머리행, 없으면 캡션 바로 위 표의 머리행."""
    for j in range(cap_i + 1, min(cap_i + 4, len(lines))):
        if lines[j].lstrip().startswith("|"):
            return lines[j]
    j = cap_i - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j >= 0 and lines[j].lstrip().startswith("|"):
        while j > 0 and lines[j - 1].lstrip().startswith("|"):
            j -= 1
        return lines[j]
    return None


_V40_EX = {"caption": {"standard_table_words": ["표준표"]}}


@gate("V40", samples=[
    Sample(sample_model(tree={"a.md": "**표 17.6-1.** 핵심 파라미터 표준표\n\n| 파라미터 | 값 |\n|---|---|"},
                        extra=_V40_EX), expect=1),
    Sample(sample_model(tree={"a.md": "**표 6.1-2.** 관수 표준표\n\n| 값 | 근거 등급 |\n|---|---|"},
                        extra=_V40_EX), expect=0),
])
def v40_evidence_column(model: DocModel) -> GateOutput:
    """표준표·임계값 캡션의 표 머리행에 근거(출처 등급) 열이 있는가. 낱말 설정이 없으면 대상 없음."""
    rx = _std_caption_re(model)
    if rx is None:
        return GateOutput(0, [])
    out: list[Finding] = []
    targets = 0
    for name, text in _texts(model).items():
        lines = text.split("\n")
        for i, line in enumerate(lines):
            cm = rx.search(line)
            if not cm:
                continue
            targets += 1
            hdr = table_header(lines, i)
            if hdr is not None and not EVIDENCE_COL.search(hdr):
                out.append(Finding(f"{name}:{i + 1}", f"근거 등급 열 없음 — {cm.group(0)[:50]}"))
    return GateOutput(targets, out)


# ═══ V62 표의 참조 열 · V63 표 열 이름 (prose_gates 409-416 · 783-806) ═══

REF_HEAD = re.compile(
    r"관련 ?(?:절|장|항)|참조 ?(?:절|장)|규정 ?(?:위치|절|장)|담당 ?(?:절|장)|다루는 ?(?:절|장|곳)"
    r"|이어받는 ?(?:절|곳)|넘기는 곳|잡는 곳|대응 ?(?:절|위치)|정의 위치|출처 절|연계 ?절|근거 ?절"
    r"|해당 ?(?:절|장)|반영 위치|처리 위치|^절$|^위치$|^이관 위치$")
HEAD_ASK = re.compile(r"(?:는가|하나|되나|보나|재나|막히나|걸리나|정하나|적나|바뀌나|생기나|하는지|할지|을지"
                      r"|ㄹ지|는지)\??$|\?$|^(?:무엇|왜|어디|누가|언제|어떻게)(?:\s|$|을|이|에|로|서)")
HEAD_DESC = re.compile(r"(?:하는|되는|담는|쓰는|보는|여는|맡는|정하는|펼치는|막히는|생기는|묻는|넘기는|재는|잃는"
                       r"|얻는|주는|받는|내놓는|요구하는|규정하는|보장하지 못하는|다루는) ?(?:것|곳|사람|때|자리|일)$"
                       r"|면 생기는 일$")
HEAD_TWO = re.compile(r"사람과 때|주체와 시점|대상과 시기")
HEAD_FIG = re.compile(r"펼치|딛고|떠받|길목")
_TBL_SEP_LINE = re.compile(r"^\|[\s:|-]+\|\s*$")


def ref_val_re(letters: str, style: str = "arabic") -> re.Pattern:
    """참조 열 값 — 절·장 번호, 별첨 번호. roman이면 「II.6」도(F82 번호 꼴)."""
    roman = r"[IVX]+(?:\.\d+)+|" if style == "roman" else ""
    return re.compile(rf"^(?:{roman}제?\d+(?:\.\d+)*(?:\.[A-Z]\.\d+)?(?:절|장|항)?|[{letters}]-\d+"
                      rf"|별첨 ?[{letters}]|이 절)(?:[\s·,~∼]|$)")  # noqa: RUF001


@gate("V62", samples=[
    Sample(sample_model(tree={"a.md": "| 항목 | 관련 절 |\n|---|---|\n| 가 | 3.2 |\n| 나 | 4.1 |"}), expect=1),
    Sample(sample_model(tree={"a.md": "| 항목 | 관련 절 |\n|---|---|\n| 가 | 관측 |\n| 나 | 기록 |"}), expect=0),
])
def v62_reference_column(model: DocModel) -> GateOutput:
    """표에 다른 절을 가리키는 열 — 머리말이 참조를 뜻하고 값 절반 이상이 절·장 번호(분담·구성표 제외)."""
    ref_val = ref_val_re(appendix_letters(model.extra), _style(model))
    out: list[Finding] = []
    tables = 0
    for name, text in _texts(model).items():
        tl = text.split("\n")
        for ti in range(len(tl) - 1):
            if not (tl[ti].startswith("|") and _TBL_SEP_LINE.match(tl[ti + 1])
                    and not (ti and tl[ti - 1].startswith("|"))):
                continue
            tables += 1
            hd = [c.strip() for c in tl[ti].strip().strip("|").split("|")]
            rows = []
            tj = ti + 2
            while tj < len(tl) and tl[tj].startswith("|"):
                rows.append([c.strip() for c in tl[tj].strip().strip("|").split("|")])
                tj += 1
            # 절마다 맡는 일을 적은 분담·분업·구성표는 장 자체가 내용이라 뺀다
            cap = next((tl[q] for q in range(ti - 1, max(-1, ti - 4), -1) if tl[q].strip().startswith("**")), "")
            for ci, h in enumerate(hd if not re.search(r"분담|분업|구성", cap) else []):
                vals = [r[ci] for r in rows if ci < len(r) and r[ci]]
                if vals and REF_HEAD.search(h) and sum(bool(ref_val.match(x)) for x in vals) * 2 >= len(vals):
                    out.append(Finding(f"{name}:{ti + 1}", f"표의 참조 열 — 「{h}」"))
    return GateOutput(tables, out)


@gate("V63", samples=[
    Sample(sample_model(tree={"a.md": "| 무엇을 재나 | 값 |\n|---|---|\n| 1 | 2 |"}), expect=1),
    Sample(sample_model(tree={"a.md": "| 측정 대상 | 값 |\n|---|---|\n| 1 | 2 |"}), expect=0),
])
def v63_column_names(model: DocModel) -> GateOutput:
    """표 열 이름 — 물음꼴·서술 꼴(…하는 것)·두 속성 합침(사람과 때)·비유(펼치·딛고·떠받·길목)."""
    out: list[Finding] = []
    tables = 0
    for name, text in _texts(model).items():
        lines = text.split("\n")
        for ti in range(len(lines) - 1):
            if not (lines[ti].startswith("|") and _TBL_SEP_LINE.match(lines[ti + 1])):
                continue
            tables += 1
            for h in [c.strip().strip("*").strip() for c in lines[ti].strip().strip("|").split("|")]:
                for rx, nm in ((HEAD_ASK, "물음꼴"), (HEAD_DESC, "서술 꼴"), (HEAD_TWO, "두 속성"),
                               (HEAD_FIG, "비유")):
                    if h and rx.search(h):
                        out.append(Finding(f"{name}:{ti + 1}", f"열 이름 {nm} — 「{h[:24]}」"))
                        break
    return GateOutput(tables, out)


# ═══ V66 자리 호출 · V73 mermaid 물결표 · V75 그래프 축 이름 (prose_gates 334-339 · 378-405 · 700-765) ═══

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
# 인쇄본은 그림을 빈자리 없이 앉히려고 뒤 문단을 앞으로 당긴다 — 「아래 그림」은 위에 놓일 수 있다
POS_REF = re.compile(
    r"(?<![가-힣])(?:아래|위|다음|앞|뒤|위쪽|아래쪽|이어지는|이어질)(?:의)?\s?"
    r"(?:그림|표|도표|도해|도식|차트|그래프)(?:들)?(?:은|는|이|가|을|를|에|에서|과|와|처럼|로|으로|의|만|도|에서처럼)?"
    r"(?![가-힣])")
FIG_START = re.compile(r"^(?:```(?:mermaid|chart)|!\[|<figure|<img)")
# 마디 글 안에 「~」가 둘이면 mermaid가 지움줄로 읽는다 — 범위는 「∼」(U+223C)로  # noqa: RUF003
MER_TILDE = re.compile(r"(?<!~)(?:~|#126;)(?!~)")
# 원본 CHART_AXIS_TYPES + 플러그인 generate_chart의 축 있는 종류(bar·line·comparison)
DEFAULT_CHART_AXIS_TYPES = ("bar", "paired_bar", "grouped_bar", "line", "scatter", "box", "timeline",
                            "stacked_bar", "comparison")
# 축 이름 키 — 시리즈 웹북 xlabel/ylabel, 플러그인 generate_chart x_label/y_label
DEFAULT_CHART_AXIS_KEYS = {"x": ("xlabel", "x_label"), "y": ("ylabel", "y_label")}


def chart_axis_missing(raw: str, types=DEFAULT_CHART_AXIS_TYPES,
                       keys: dict | None = None) -> str | None:
    """```chart 원문 → 빠진 축 이름 안내(없으면 None). JSON이 깨진 명세는 보지 않는다."""
    keys = keys or DEFAULT_CHART_AXIS_KEYS
    try:
        sp = json.loads(raw)
    except Exception:
        return None
    if not isinstance(sp, dict) or str(sp.get("type", "")).strip().lower() not in set(types):
        return None
    names = {"x": "xlabel", "y": "ylabel"}
    miss = [names[a] for a in ("x", "y")
            if not any(str(sp.get(k) or "").strip() for k in keys.get(a) or ())]
    if not miss:
        return None
    return f"그래프 축 이름 없음({'·'.join(miss)}) — {str(sp.get('title') or sp.get('type'))[:40]}"


def _chart_cfg(model: DocModel) -> tuple[tuple, dict]:
    cfg = _cfg(model)
    types = tuple(str(t).lower() for t in cfg.get("chart_axis_types") or DEFAULT_CHART_AXIS_TYPES)
    raw = cfg.get("chart_axis_keys") or {}
    keys = {a: tuple(str(k) for k in (raw.get(a) or DEFAULT_CHART_AXIS_KEYS[a])) for a in ("x", "y")}
    return types, keys


def _figure_lines(model: DocModel, want: str) -> GateOutput:
    """원본 v2.2 줄 루프(INDEX.md 제외) — 펜스를 따라가며 V66·V73·V75 지적만 모은다."""
    types, keys = _chart_cfg(model)
    texts = _no_index(_texts(model))
    out: list[Finding] = []
    targets = 0
    for name, text in texts.items():
        lines = text.split("\n")
        fence = mer = chart = False
        cbuf: list[str] = []
        cat = 0
        for i, ln in enumerate(lines):
            if ln.strip().startswith("```"):
                if fence and chart and want == "V75":  # 그래프 명세가 닫힐 때 축 이름을 본다
                    targets += 1
                    miss = chart_axis_missing("\n".join(cbuf), types, keys)
                    if miss:
                        out.append(Finding(f"{name}:{cat}", miss))
                if not fence and want == "V73" and ln.strip().startswith("```mermaid"):
                    targets += 1
                fence = not fence
                mer = fence and ln.strip().startswith("```mermaid")
                chart, cbuf, cat = fence and ln.strip().startswith("```chart"), [], i + 1
                continue
            if chart:
                cbuf.append(ln)
            if want == "V73" and mer and len(MER_TILDE.findall(ln)) >= 2:
                out.append(Finding(f"{name}:{i + 1}", f"mermaid 홑 물결표 — {ln.strip()[:60]}"))
            if fence or not ln.strip() or want != "V66":
                continue
            if HEADING.match(ln):
                continue
            for m in POS_REF.finditer(ln):
                out.append(Finding(f"{name}:{i + 1}", f"자리로 부름 — {ln[max(0, m.start() - 12):m.end() + 8]}"))
            if re.search(r"다음과 같다[.:]?\s*$", ln):
                k = i + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k < len(lines) and FIG_START.match(lines[k].strip()):
                    out.append(Finding(f"{name}:{i + 1}", f"그림 앞 「다음과 같다」 — {ln.strip()[-40:]}"))
    return GateOutput(len(texts) if want == "V66" else targets, out)


@gate("V66", samples=[
    Sample(sample_model(tree={"a.md": "아래 그림처럼 물은 근권을 지난다.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "그림 3.1-1처럼 물은 근권을 지난다.\n"}), expect=0),
])
def v66_position_reference(model: DocModel) -> GateOutput:
    """그림·표를 자리(아래·위·다음·앞)로 부름, 그림 바로 앞 「다음과 같다」 — 번호로만 부른다."""
    return _figure_lines(model, "V66")


@gate("V73", samples=[
    Sample(sample_model(tree={"a.md": '```mermaid\nA["투입비 −8~20%"] --> B["1~3일"]\n```\n'}), expect=1),  # noqa: RUF001
    Sample(sample_model(tree={"a.md": '```mermaid\nA["-8∼20% +2∼3"] --> B\n```\n'}), expect=0),  # noqa: RUF001
])
def v73_mermaid_tilde(model: DocModel) -> GateOutput:
    """mermaid 원문 한 줄에 홑 물결표(~·#126;) 둘 이상 — 지움줄로 읽혀 그림에 오류가 찍힌다."""
    return _figure_lines(model, "V73")


@gate("V75", samples=[
    Sample(sample_model(tree={"a.md": '```chart\n{"type":"bar","categories":["가"],"unit":"%"}\n```\n'}),
           expect=1),
    Sample(sample_model(tree={"a.md": '```chart\n{"type":"bar","xlabel":"권역","ylabel":"손실률(%)"}\n```\n'}),
           expect=0),
])
def v75_chart_axis(model: DocModel) -> GateOutput:
    """축 있는 그래프 명세에 가로·세로 축 이름이 둘 다 있는가."""
    return _figure_lines(model, "V75")


# ═══ V80 그림 안 글 길이 (prose_gates 1390-1477 · 1968-1987 + gate_limits.json) ═══

_MER_EDGE = re.compile(r"\|\s*\"?([^|\"]*)\"?\s*\|")
_MER_QUOTED = re.compile(r"\"([^\"]*)\"")
_MER_BARE = re.compile(r"\b[A-Za-z_][\w\-]*\s*(?:\[\[|\[\(|\(\[|\(\(|\{\{|\[/|\[\\|\[|\(|\{|>)\s*"
                       r"([^\[\]\(\)\{\}\"|]+?)\s*(?:\]\]|\)\]|\]\)|\)\)|\}\}|/\]|\\\]|\]|\)|\})")
_MER_SKIP = re.compile(r"^\s*(?:%%|classDef|class\s|style\s|linkStyle|click\s|direction\s|flowchart|graph\s"
                       r"|graph$|sequenceDiagram|xychart|pie|timeline|mindmap|gantt|stateDiagram|erDiagram"
                       r"|quadrantChart|journey|end\s*$)")
_MER_BREAK = re.compile(r"<br\s*/?>|\\n", re.I)
_MER_TAGS = re.compile(r"<[^>]+>|\*\*|&nbsp;|#quot;")
_MER_ENT = re.compile(r"#\d+;|&#?\w+;")


@lru_cache(maxsize=1)
def _l80() -> dict:
    return dict((load_dict("gate_limits.json", []) or {}).get("V80") or {})


def text_width(s: str, ascii_weight: float | None = None) -> float:
    """화면 폭 — 한글 1, 반각(영문·숫자·기호) ascii_weight(기본 0.5)."""
    w = float(_l80().get("ascii_weight", 0.5) if ascii_weight is None else ascii_weight)
    return sum(w if ord(c) < 128 else 1.0 for c in s)


def _seg_max(label: str) -> tuple[float, str]:
    best = (0.0, "")
    for seg in _MER_BREAK.split(label):
        seg = _MER_ENT.sub("·", _MER_TAGS.sub("", seg)).strip()
        w = text_width(seg)
        if w > best[0]:
            best = (w, seg)
    return best


def mermaid_text_issues(lines: list[str]) -> list[tuple[int, str]]:
    """mermaid 원문 줄 목록 → (원문 안 줄 순번, 메시지)."""
    lim = _l80()
    out = []
    lim_n = float(lim.get("node_chars", 24))
    lim_e = float(lim.get("edge_chars", 24))
    lim_a = float(lim.get("axis_chars", 20))
    lim_c = float(lim.get("category_chars", 20))
    for j, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("%%"):
            continue
        xm = re.match(r"^([xy])-axis\s+\"([^\"]*)\"\s*(\[.*\])?", s)
        if xm:
            w, seg = _seg_max(xm.group(2))
            if w > lim_a:
                out.append((j, f"축 이름 {w:g}자(> {lim_a:g}) — {seg[:30]}"))
            for c in _MER_QUOTED.findall(xm.group(3) or ""):
                w, seg = _seg_max(c)
                if w > lim_c:
                    out.append((j, f"눈금 글 {w:g}자(> {lim_c:g}) — {seg[:30]}"))
            continue
        if _MER_SKIP.match(s) and not re.match(r"^\s*(?:pie|timeline)\b.*\"", s):
            continue
        for lab in _MER_EDGE.findall(s):
            w, seg = _seg_max(lab)
            if w > lim_e:
                out.append((j, f"연결선 글 {w:g}자(> {lim_e:g}) — {seg[:30]}"))
        rest = _MER_EDGE.sub(" ", s)
        labels = _MER_QUOTED.findall(rest) + _MER_BARE.findall(_MER_QUOTED.sub(" ", rest))
        for lab in labels:
            w, seg = _seg_max(lab)
            if w > lim_n:
                out.append((j, f"마디 글 {w:g}자(> {lim_n:g}) — {seg[:30]}"))
    return out


def chart_text_issues(raw: str) -> list[str]:
    """그래프 명세(JSON) → 메시지 목록. 축 이름(xlabel·ylabel)과 눈금 글(categories·x·axes·rows·cols)."""
    try:
        spec = json.loads(raw)
    except Exception:
        return []
    if not isinstance(spec, dict):
        return []
    lim = _l80()
    out = []
    lim_a = float(lim.get("axis_chars", 20))
    lim_c = float(lim.get("category_chars", 20))
    for k in ("xlabel", "ylabel"):
        v = spec.get(k)
        if isinstance(v, str):
            w = text_width(v.strip())
            if w > lim_a:
                out.append(f"축 이름 {k} {w:g}자(> {lim_a:g}) — {v[:30]}")
    for k in ("categories", "x", "axes", "rows", "cols", "labels"):
        v = spec.get(k)
        if isinstance(v, list):
            for c in v:
                if isinstance(c, str):
                    w, seg = _seg_max(c)
                    if w > lim_c:
                        out.append(f"눈금 글 {k} {w:g}자(> {lim_c:g}) — {seg[:30]}")
    return out


@gate("V80", samples=[
    Sample(sample_model(tree={"a.md": f'```mermaid\nA["{"가" * 25}"]\n```\n'}), expect=1),
    Sample(sample_model(tree={"a.md": '```mermaid\nA["짧은 글<br/>둘째 줄"] --> B["다음"]\n```\n'}), expect=0),
])
def v80_figure_text_length(model: DocModel) -> GateOutput:
    """그림 안 글 길이 — mermaid 마디·연결선 24자, 그래프 축 이름·눈금 글 20자(반각 0.5자).

    독자가 보는 렌더 트리(INDEX.md 제외)를 본다. 트리가 없으면 산문 원고.
    """
    if model.tree:
        files = {tf.rel: tf.text for tf in model.tree if tf.rel.rsplit("/", 1)[-1] != "INDEX.md"}
    else:
        files = _no_index(_texts(model))
    out: list[Finding] = []
    blocks = 0
    for key, text in files.items():
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith("```mermaid") or s.startswith("```chart"):
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    j += 1
                body = lines[i + 1:j]
                blocks += 1
                if s.startswith("```mermaid"):
                    for jj, msg in mermaid_text_issues(body):
                        out.append(Finding(f"{key}:{i + 2 + jj}", msg))
                else:
                    for msg in chart_text_issues("\n".join(body)):
                        out.append(Finding(f"{key}:{i + 1}", msg))
                i = j + 1
                continue
            i += 1
    return GateOutput(blocks, out)
