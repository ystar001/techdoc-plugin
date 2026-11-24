"""구조·상호참조 게이트 — V2·V21·V26·V30·V31·V34·V39·V44·V57·V59·V72·V78 (v1.11-b, F85).

시리즈 check_v2(카드 게이트 V2·V21·V57·V59)와 prose_gates(산문 게이트 나머지)에서 판정 로직을
그대로 옮기고 입력만 DocModel로 바꿨다. 바꾼 것은 둘뿐이다.

- **시리즈 고유 값은 설정으로**: 다른 문서 이름(`extra.structure.peer_doc_names`), 형제 문서로
  내보낸 번호 접두(`peer_prefix`), 분야 전문어(`qs_jargon`), 「발간사」(`intro_exempt_titles`),
  「작물편」(`extra.prose.meta_words`), 절 파일을 두지 않는 폴더(`folder_names`), 별첨 문자 범위
  (`appendix_letters`). 플러그인 기본은 비어 있거나 일반값이다(E17).
- **번호 꼴**: `numbering.section`이 arabic(기본)이면 원본 정규식을 그대로 쓴다. roman·letter_middle
  일 때만 `techdoc_core.qc.numbering` 조각을 쓴다(F82 — `II.6.3절`을 끊어진 참조로 잡지 않게).

카드 게이트의 지적 위치는 원본 면제 키와 같은 `"<카드>|<섹션키>: …"`(카드 수준은 섹션키 `-`).
원본이 면제(hit)를 거치지 않던 V2의 도표 번호 지적은 `"<카드> 도표: …"`로 두어 면제가 닿지 않는다.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from techdoc_core.card_id import parse_card_id_parts
from techdoc_core.qc.card_text import card_texts, sections_of
from techdoc_core.qc.dicts import layers_key, load_dict
from techdoc_core.qc.model import DocModel
from techdoc_core.qc.numbering import (
    CAPTION_KINDS,
    CAPTION_TOKEN,
    appendix_letters,
    head_num,
    lead_num,
    normalize_captions,
    section_file_re,
    section_num,
    section_ref_re,
)
from techdoc_core.qc.prose import MARKUP, sections
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model


def _style(model: DocModel) -> str:
    return (model.numbering or {}).get("section") or "arabic"


def _cfg(model: DocModel, group: str = "structure") -> dict:
    return (model.extra or {}).get(group) or {}


def _texts(model: DocModel) -> dict[str, str]:
    """산문 게이트 입력(원본 prose_gates.run의 texts) — draft가 있으면 draft, 없으면 렌더 트리."""
    return {tf.rel: tf.text for tf in model.prose()}


def _card(body: str, title: str = "", **extra) -> dict:
    return {"sections": {"s1": {"title": title, "body": body}}, **extra}


# ═══ 카드 ID (check_v2.base_id·section_ids·appendix_letters) ═══

_SPLIT_SUFFIX = re.compile(r"\.X?L\d+$")
_APP_HEAD = re.compile(r"^([A-Z])(?=-|\d)")


def base_id(cid: str) -> str:
    """분할 카드의 기저 ID — `11.1.XL3` → `11.1`. 분할이 아니면 그대로."""
    return _SPLIT_SUFFIX.sub("", cid)


def section_ids(ids) -> set[str]:
    """절로 실재하는 ID — 카드 ID와 분할 카드의 기저 ID."""
    return set(ids) | {base_id(c) for c in ids}


def appendix_letters_of(ids) -> set[str]:
    """별첨 문자 — `A-1.4.L1`·`D-10`의 하이픈 꼴과 `E1.XL3`·`G1.XL2`의 붙임 꼴."""
    out = {c.split("-")[0] for c in ids if "-" in c}
    out |= {m.group(1) for c in ids if (m := _APP_HEAD.match(c))}
    return out


def outline_appendices(outline: dict) -> set[str]:
    """final_outline.json이 선언한 별첨 ID — 아직 집필 전인 별첨도 실재로 본다."""
    out: set[str] = set()
    for a in (outline or {}).get("appendices") or []:
        i = a.get("id") if isinstance(a, dict) else a
        if isinstance(i, str) and re.fullmatch(r"[A-Z]", i.strip()):
            out.add(i.strip())
    return out


def _is_body_section(cid: str, model: DocModel) -> bool:
    """본문 절 카드(`N.M`, 개요 0.x 제외) — 핵심요약·절 결론을 두는 자리(원본 V21·V57 조건).

    roman이면 `II.6`처럼 부 번호 + 절 번호 두 마디인 본문 카드.
    """
    style = _style(model)
    if style != "roman":
        return bool(re.fullmatch(r"\d+\.\d+", cid)) and not cid.startswith("0.")
    pc = parse_card_id_parts(cid, model.numbering)
    return pc.kind == "body" and bool(re.fullmatch(rf"{lead_num(style)}\.\d+", cid))


# ═══ V2 끊어진 상호참조 (check_v2 170-222 · 1020-1051 · 1103-1116 · 1269-1309) ═══

# 「$18.1 절감」은 금액 뒤의 「절감」이지 18.1절이 아니다 — 통화 기호 뒤와 「절감」을 뺀다
REF_SEC = re.compile(r"(?<![\d.$€£¥])(\d{1,2}\.\d)\s*절(?!감)")
REF_CH = re.compile(r"(?:章\s*(\d{1,2})|제\s*(\d{1,2})\s*장)")
REF_CH_LIST = re.compile(r"章\s*\d{1,2}((?:\s*[·,]\s*\d{1,2})+)")
# 「항목」은 항 참조가 아니다 — 일반 명사로 쓰인다
REF_ITEM = re.compile(r"「([^」]{2,60})」\s*항(?!목)")
_ITEM_QUAL_ARABIC = r"\d+\.[A-Z]\.\d+|\b[A-Z]\d+|\d+\.\d+\s*절?"
# 캡션 정의줄 — 굵은 옛 꼴과 굵게 없는 정본 꼴(줄 첫머리 + 번호 + 마침표 + 빈칸)
CAP_PLAIN_AHEAD = r"(?=" + CAPTION_KINDS + r"\s" + CAPTION_TOKEN + r"\.\s)"  # 번호 조각은 numbering(F82)
CAP_OPEN = r"(?:\*\*|(?<![^\n])" + CAP_PLAIN_AHEAD + ")"
CAP_DEF = re.compile(CAP_OPEN + r"(그림|표|차트|사진|다이어그램)\s*([\dA-Za-z][\w.\-]*?)\.(?:\*\*|\s)")
CAP_DEF_LINE = re.compile(
    r"^(?:\*\*|" + CAP_PLAIN_AHEAD + r")(그림|표|차트|사진|다이어그램)\s*([\dA-Za-z][\w.\-]*?)\.(?:\*\*|\s)",
    re.M)
CAP_DEF_CHART = re.compile(
    r'"caption"\s*:\s*"(그림|표|차트|사진|다이어그램)\s*([\dA-Za-z][\w.\-]*)\.(?=\s|")')
CAP_USE = re.compile(
    r"(?<!\*\*)(그림|표|차트|사진|다이어그램)\s*([\dA-Za-z](?:[\dA-Za-z.\-]*[\dA-Za-z])?)")


def cap_defs(whole: str) -> list:
    """이 카드가 정의한 도표 — 마크다운 캡션 줄 + 차트 블록 caption."""
    return CAP_DEF_LINE.findall(whole) + CAP_DEF_CHART.findall(whole)


_VISUAL_CAP = re.compile(
    r"^\s*(?:\*\*)?(그림|표|차트|사진|다이어그램)\s*([\dA-Za-z](?:[\dA-Za-z.\-]*[\dA-Za-z])?)")


def card_visual_captions(card: dict) -> set[str]:
    """카드 시각 필드(F22 — `diagrams[].caption`·`figures[].caption`)가 정의한 도표 「그림II.8-1」."""
    out: set[str] = set()
    for field in ("diagrams", "figures"):
        items = card.get(field)
        for it in items if isinstance(items, list) else []:
            cap = it.get("caption") if isinstance(it, dict) else None
            m = _VISUAL_CAP.match(cap) if isinstance(cap, str) else None
            if m:
                out.add(f"{m.group(1)}{m.group(2)}")
    return out


def _title_forms(title: str):
    """참조는 표제를 줄여 적는다 — 부제(` — ` 뒤)·괄호 약어·권 표기를 뗀 꼴도 후보로."""
    for form in (title, re.sub(r"\s*\([^)]*\)", "", title)):
        yield form.strip()
        yield form.split(" — ")[0].strip()
        yield form.split("·")[0].strip()


def _ref_sec_res(style: str) -> list[re.Pattern]:
    if style == "roman":  # 부가 로마 숫자면 아라비아 「4.4절」은 이 문서의 절이 아니다(바깥 문헌)
        return [section_ref_re("roman")]
    if style == "letter_middle":
        return [REF_SEC, section_ref_re("letter_middle")]
    return [REF_SEC]


def _draft_head_res(style: str) -> list[re.Pattern]:
    arabic = re.compile(r"(?m)^#{1,3}\s+(\d+\.\d+)\b")
    if style == "arabic":
        return [arabic]
    other = re.compile(rf"(?m)^#{{1,3}}\s+({section_num(style)})\b")
    return [other] if style == "roman" else [arabic, other]


def _chapters(ids: set[str], style: str) -> set[int]:
    out = {int(c.split(".")[0]) for c in ids if re.fullmatch(r"\d+\.\d+", c)}
    if style == "roman":  # `II.6` — 장 번호는 부를 넘어 이어진다
        out |= {int(m.group(1)) for c in ids if (m := re.fullmatch(r"[IVX]+\.(\d+)", c))}
    return out


def _peer_item_re(model: DocModel) -> re.Pattern | None:
    """다른 문서 이름이 앞에 붙은 항 참조 — 그 문서의 항이라 여기서 찾지 않는다.

    `extra.structure.peer_doc_names`는 정규식 조각 목록(예: 시리즈 `[가-힣]{1,6}편`·`개론`).
    """
    names = [str(n) for n in _cfg(model).get("peer_doc_names") or [] if str(n)]
    if not names:
        return None
    return re.compile(r"(?:" + "|".join(names) + r")\s*(?:\d+\.\d+\s*절?)?\s*(?:의\s*)?"
                      r"「([^」]{2,60})」\s*항(?!목)")


@gate("V2", samples=[
    Sample(sample_model(cards={"1.1": _card("1.5절에서 다룬다.")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("1.1절에서 다룬다."), "1.4.L1": _card("1.4절 참조.")}),
           expect=0),
])
def v2_cross_refs(model: DocModel) -> GateOutput:
    """가리키는 대상이 실재하는가 — 항·절·장·별첨 참조, 정의 없는 도표 번호, 겹친 도표 번호."""
    cards = model.cards
    if not cards:
        return GateOutput(0, [])
    style = _style(model)
    letters = appendix_letters(model.extra)
    ref_app = re.compile(rf"별첨\s*([{letters}])\b")
    qual_alt = _ITEM_QUAL_ARABIC if style != "roman" else rf"{section_num(style)}\s*절?|{_ITEM_QUAL_ARABIC}"
    ref_item_qual = re.compile(rf"({qual_alt})\s*「([^」]{{2,60}})」\s*항(?!목)")
    ref_item_other = _peer_item_re(model)

    ids = section_ids(cards)
    for tf in model.draft:  # draft가 정본인 절도 상호참조 대상
        for rx in _draft_head_res(style):
            ids |= {m.group(1) for m in rx.finditer(tf.text)}
    chapters = _chapters(ids, style)
    apps = appendix_letters_of(cards) | outline_appendices(model.outline)
    all_titles = {f for c in cards.values() for _k, t, _b in sections_of(c) if t
                  for f in _title_forms(t)}

    out: list[Finding] = []
    for cid, card in cards.items():
        item_titles = {f for _k, t, _b in sections_of(card) if t for f in _title_forms(t)}
        # roman이면 번호 뒤 마침표 없는 캡션도 정의로(F82) — arabic은 그대로
        texts = [(k, t, normalize_captions(b, style)) for k, t, b in card_texts(card)]
        for key, title, body in texts:
            blob = f"{title}\n{body}"
            loc = f"{cid}|{key}"
            # 항 참조 — 카드 코드가 앞에 붙은 것은 문서 전체 항 제목에서 찾는다
            qualified = {m.group(2) for m in ref_item_qual.finditer(blob)}
            other = {m.group(1) for m in ref_item_other.finditer(blob)} if ref_item_other else set()
            for m in REF_ITEM.finditer(blob):
                if m.group(1) in other:
                    continue
                if m.group(1) in qualified and m.group(1) in all_titles:
                    continue
                if m.group(1) not in item_titles:
                    out.append(Finding(f"{loc}: 항", f"{cid}·{key} → 「{m.group(1)}」 항 없음"))
            for rx in _ref_sec_res(style):
                for m in rx.finditer(blob):
                    if m.group(1) not in ids:
                        out.append(Finding(f"{loc}: 절", f"{cid}·{key} → {m.group(1)}절 없음"))
            for m in REF_CH.finditer(blob):
                ch = int(m.group(1) or m.group(2))
                if ch not in chapters:
                    out.append(Finding(f"{loc}: 장", f"{cid}·{key} → 章{ch} 없음"))
            for m in REF_CH_LIST.finditer(blob):
                for n in re.findall(r"\d{1,2}", m.group(1)):
                    if int(n) not in chapters:
                        out.append(Finding(f"{loc}: 장", f"{cid}·{key} → 章{n} 없음(나열 표기)"))
            for m in ref_app.finditer(blob):
                if m.group(1) not in apps:
                    out.append(Finding(f"{loc}: 별첨", f"{cid}·{key} → 별첨 {m.group(1)} 없음"))

        # 표·그림 번호 — 정의 없이 쓰인 자기 카드 도표, 같은 번호가 두 도표에 (원본: 면제 없음)
        whole = "\n".join(b for _, _, b in texts)
        defined ={f"{k}{n.rstrip('.')}" for k, n in CAP_DEF.findall(whole) + CAP_DEF_CHART.findall(whole)}
        defined |= card_visual_captions(card)
        mine = cid + "-"
        for kind, num0 in CAP_USE.findall(whole):
            num = num0.rstrip(".")
            if f"{kind}{num}" not in defined and num.startswith(mine):
                out.append(Finding(f"{cid} 도표", f"{cid} → {kind} {num} 정의 없음"))
        dup = Counter(f"{k} {n.rstrip('.')}" for k, n in cap_defs(whole))
        for key, cnt in dup.items():
            if cnt > 1:
                out.append(Finding(f"{cid} 도표", f"{cid} → {key} 번호 중복 ×{cnt}"))  # noqa: RUF001
    return GateOutput(len(cards), out)


# ═══ V21 핵심요약 규약 · V57 절 끝 결론 (check_v2 549-573 · 743-814 · 1390-1444) ═══

QS_MIN, QS_MAX = 20, 160
QS_SENT_MAX = 110
QS_SENTS = (1, 2)
QS_SPLIT = re.compile(r"(?<=다[.])\s+|(?<=[.!?])\s+")
QS_OPEN_CASE = re.compile(r"^\s*(?:[‘'「\"“]|예를 들어|가령|[^.]{0,40}?처럼\s)")  # noqa: RUF001
QS_CAN_LIST = re.compile(r"(?:을|를|지|가)?\s*알 수 있다\.?\s*$")
GOAL_MIN, GOAL_MAX = 20, 160
GOAL_QN = (2, 4)
GOAL_Q_MAX = 80
CONC_MIN, CONC_MAX, CONC_LEN = 3, 5, 120
CONC_GUIDE = re.compile(r"이 절[은이]|다음 절|앞 절|뒤의? 절|\d+\.\d+절|\d+장(?:에서|이|은)|살펴보았|살펴본다"
                        r"|다루었다|다룬다\.?$|정리했다|REF-\d")
CONC_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def _jargon_re(model: DocModel) -> re.Pattern | None:
    """요약에 풀이 없이 넣지 않는 분야 전문어 — 분야 층 값이라 `extra.structure.qs_jargon`으로만."""
    words = [str(w) for w in _cfg(model).get("qs_jargon") or [] if str(w)]
    return re.compile("|".join(words)) if words else None


def is_goal_form(qs) -> bool:
    """quick_summary가 「목표 + 핵심 질문」 꼴인가."""
    return isinstance(qs, dict) and ("goal" in qs or "questions" in qs)


def goal_questions(qs) -> list[str]:
    if not is_goal_form(qs):
        return []
    q = qs.get("questions") or []
    return [str(x).strip() for x in q if str(x).strip()] if isinstance(q, list) else []


def goal_defects(qs, jargon: re.Pattern | None = None) -> list[str]:
    """「이 절의 목표」 상자 — 목표 한 문장 20~160자 · 핵심 질문 2~4개 · 물음표 · 80자."""
    out = []
    goal = str(qs.get("goal") or "").strip().replace("\\$", "$")
    if not goal:
        out.append("목표가 없다")
    else:
        if not (GOAL_MIN <= len(goal) <= GOAL_MAX):
            out.append(f"목표 {len(goal)}자(기준 {GOAL_MIN}~{GOAL_MAX})")
        sents = [s for s in QS_SPLIT.split(goal) if s.strip()]
        if len(sents) != 1:
            out.append(f"목표 {len(sents)}문장(한 문장이어야 한다)")
        jarg = sorted(set(jargon.findall(goal))) if jargon else []
        if jarg:
            out.append("풀이 없는 전문어 " + "·".join(jarg[:3]))
    raw = qs.get("questions")
    if not isinstance(raw, list):
        out.append("핵심 질문이 목록이 아니다")
        return out
    qs_ = goal_questions(qs)
    if not (GOAL_QN[0] <= len(qs_) <= GOAL_QN[1]):
        out.append(f"핵심 질문 {len(qs_)}개(기준 {GOAL_QN[0]}~{GOAL_QN[1]})")
    for q in qs_:
        if not q.endswith("?"):
            out.append(f"물음표로 끝나지 않음: {q[-16:]}")
        if len(q) > GOAL_Q_MAX:
            out.append(f"질문 {len(q)}자(기준 {GOAL_Q_MAX} 이하): {q[:24]}")
    return out


def summary_defects(summ: str, jargon: re.Pattern | None = None) -> list[str]:
    """옛 꼴 요약 — 20~160자 · 1~2문장 · 한 문장 110자 · 전문어 · 사례로 시작 · 「알 수 있다」 끝."""
    summ = summ.replace("\\$", "$")  # 통화 이스케이프의 역슬래시는 독자가 보는 글자가 아니다
    bad = []
    if not (QS_MIN <= len(summ) <= QS_MAX):
        bad.append(f"길이 {len(summ)}자(기준 {QS_MIN}~{QS_MAX})")
    sents = [s for s in QS_SPLIT.split(summ) if s.strip()]
    if not (QS_SENTS[0] <= len(sents) <= QS_SENTS[1]):
        bad.append(f"문장 {len(sents)}개(기준 {QS_SENTS[0]}~{QS_SENTS[1]})")
    longest = max((len(s) for s in sents), default=0)
    if longest > QS_SENT_MAX:
        bad.append(f"한 문장 {longest}자")
    jarg = sorted(set(jargon.findall(summ))) if jargon else []
    if jarg:
        bad.append("풀이 없는 전문어 " + "·".join(jarg[:3]))
    if sents and QS_OPEN_CASE.search(sents[0]):
        bad.append("사례·예시로 시작(105 — 첫 문장은 정의나 중심 답)")
    if QS_CAN_LIST.search(summ):
        bad.append("「알 수 있다」 목록으로 끝남(105)")
    return bad


@gate("V21", samples=[
    Sample(sample_model(cards={"1.1": _card("x")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("x", quick_summary={
        "goal": "기록의 요건이 무엇인지 알고, 값 하나를 판단에 쓸 수 있게 적을 수 있다.",
        "questions": ["기록의 요건은 무엇인가?", "여덟 항목은 어떤 차례로 채우나?"]})}), expect=0),
])
def v21_quick_summary(model: DocModel) -> GateOutput:
    """핵심요약 — 「이 절의 목표」 상자 또는 옛 꼴 요약의 규약, 본문 절의 요약 없음, 한 줄 정리 잔존."""
    jargon = _jargon_re(model)
    out: list[Finding] = []
    for cid, card in model.cards.items():
        loc = f"{cid}|-: 핵심요약"
        q = card.get("quick_summary")
        goal = is_goal_form(q)
        if goal:
            gd = goal_defects(q, jargon)
            if gd:
                out.append(Finding(loc, f"{cid} 이 절의 목표 — {' / '.join(gd)}"))
        if goal:
            summ = ""
        elif isinstance(q, dict):
            summ = (q.get("summary") or "").strip()
        else:
            summ = str(q or "").strip()
        one = (q.get("one_sentence") or "").strip() if isinstance(q, dict) else ""
        # 개요(0.x)와 별첨 앞머리는 규약상 요약을 두지 않는다
        if not goal and not summ and _is_body_section(cid, model):
            out.append(Finding(loc, f"{cid} 핵심요약이 없다"))
        if summ:
            bad = summary_defects(summ, jargon)
            if bad:
                out.append(Finding(loc, f"{cid} 핵심요약 — {' / '.join(bad)}"))
        if one:  # 「→ 한 줄 정리」는 폐지 — 결론은 절 끝 목록이 맡는다
            out.append(Finding(loc, f"{cid} 한 줄 정리가 남아 있다"))
    return GateOutput(len(model.cards), out)


def conclusion_defects(items, body: str) -> list[str]:
    if not isinstance(items, list) or not items:
        return ["결론이 없다"]
    out = []
    if not CONC_MIN <= len(items) <= CONC_MAX:
        out.append(f"항목 {len(items)}개(기준 {CONC_MIN}~{CONC_MAX})")
    for t in items:
        t = str(t).strip()
        if len(t) > CONC_LEN:
            out.append(f"{len(t)}자 항목: {t[:24]}")
        if not re.search(r"다\.?$|다\([^)]*\)\.?$|다\.?\s*\([^)]*\)\.?$", t):
            out.append(f"문장으로 끝나지 않음: {t[-16:]}")
        g = CONC_GUIDE.search(t)
        if g:
            out.append(f"안내·출처({g.group(0)}): {t[:24]}")
        for n in CONC_NUM.findall(t):
            if n not in body:
                out.append(f"본문에 없는 수치 {n}: {t[:24]}")
    return out


@gate("V57", samples=[
    Sample(sample_model(cards={"1.1": _card("본문 3건.")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("본문 3건.", conclusion=[
        "관측은 기록이다.", "기록은 판단의 바탕이다.", "판단은 3건으로 묶인다."])}), expect=0),
])
def v57_conclusion(model: DocModel) -> GateOutput:
    """절 끝 결론 — 본문 절에만. 3~5항목·120자·문장 끝·안내/출처 없음·본문에 있는 수치·질문마다 답."""
    out: list[Finding] = []
    targets = 0
    for cid, card in model.cards.items():
        if not _is_body_section(cid, model):
            continue
        targets += 1
        body = "\n".join(b for _, _, b in sections_of(card))
        conc = card.get("conclusion")
        cb = conclusion_defects(conc, body)
        nq = len(goal_questions(card.get("quick_summary")))
        nc = len(conc) if isinstance(conc, list) else 0
        if nq and nc < nq:
            cb.insert(0, f"결론 {nc}항목 < 핵심 질문 {nq}개(108)")
        if cb:
            out.append(Finding(f"{cid}|-: 결론", f"{cid} 결론 — {' / '.join(cb[:3])}"))
    return GateOutput(targets, out)


# ═══ V59 별첨 문자 (check_v2 1604-1609) ═══

@gate("V59", samples=[
    Sample(sample_model(cards={"A-1": _card("x"), "C-1": _card("x")}), expect=1),
    Sample(sample_model(cards={"A-1": _card("x"), "B-1": _card("x")}), expect=0),
])
def v59_appendix_letters(model: DocModel) -> GateOutput:
    """별첨 문자는 A부터 건너뛰지 않는다."""
    rx = re.compile(rf"([{appendix_letters(model.extra)}])-")
    letters = sorted({m.group(1) for c in model.cards for m in [rx.match(str(c))] if m})
    want = [chr(65 + i) for i in range(len(letters))]
    out = []
    if letters != want:
        out.append(Finding("별첨 문자", f"별첨 문자 {'·'.join(letters)} (기대 {'·'.join(want)})"))
    return GateOutput(len(model.cards), out)


# ═══ 산문 게이트 공통 — 절 머리 `## N.M` 목록 (prose_gates.run) ═══

def _tops_re(style: str) -> re.Pattern:
    if style == "arabic":
        return re.compile(r"^## ([0-9][0-9A-Za-z.\-]*)\s")
    return re.compile(rf"^## ({head_num(style)})\s")


def _tops(lines: list[str], style: str) -> list[tuple[int, re.Match]]:
    """`##` 절 머리 — 절 끝 「## n. 결론」은 앞 항에 붙여 본다."""
    rx = _tops_re(style)
    tops = [(i, m) for i, ln in enumerate(lines) if (m := rx.match(ln))]
    return [(a, b) for a, b in tops if not re.search(r"^##\s+\d+\.\s*결론\s*$", lines[a])]


# ═══ V26 개요 절 아래 분업·항해 (prose_gates 203-207 · 978-1002) ═══

NAV_SUB = re.compile(r"분업|겹치지 않는|어디서 갈리|진입점")


@gate("V26", samples=[
    Sample(sample_model(tree={"a.md": "## 1.A.0 개요\n\n### 부 사이 분업\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "## 1.A.0 개요\n\n### 작물 개관\n"}), expect=0),
])
def v26_overview_nav(model: DocModel) -> GateOutput:
    """개요 절(N.X.0) 아래에 부 간 분업·항해 하위절이 달렸는가."""
    style = _style(model)
    ov = re.compile(r"^[0-9]+\.[A-Z0-9]+\.0$" if style == "arabic"
                    else rf"^{lead_num(style)}\.[A-Z0-9]+\.0$")
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        lines = text.split("\n")
        tops = _tops(lines, style)
        for k, (i, m) in enumerate(tops):
            if not ov.match(m.group(1)):
                continue
            j = tops[k + 1][0] if k + 1 < len(tops) else len(lines)
            for k2 in range(i, j):
                if not lines[k2].startswith("### "):
                    continue
                t2 = lines[k2][4:]
                if NAV_SUB.search(t2):
                    out.append(Finding(f"{name}:{k2 + 1}",
                                       f"개요 절 {m.group(1)} 아래 분업·항해 절 — {t2[:44]}"))
    return GateOutput(len(texts), out)


# ═══ V30 md 상호참조 (prose_gates 212-256 · 630-640 · 1044-1051) ═══

NUM = r"[0-9]+\.[A-H0-9]+[a-z]?\.[0-9]+(?:\.[0-9]+)?(?:-[0-9]+)?"
X_HEAD_SEC = re.compile(r"(?m)^#{1,3} (" + NUM + r")(?=[ .])")
X_CAPTION = re.compile(r"(?:표|그림)\s(" + NUM + r"-[0-9]+|" + NUM + r")")
X_REF_SEC = re.compile(r"(?<![0-9.])(" + NUM + r")(?![0-9])")
X_OBSOLETE = re.compile(r"(?m)^.*\|\s*구 (?:" + NUM + r"|[^|]*구 " + NUM + r")[^|]*\|.*$")
# roman(F82) — `II.6.3`·`II.6-1`. 부 번호가 로마 숫자라 아라비아 `NUM`으로는 못 본다
NUM_ROMAN = r"[IVX]+(?:\.[0-9]+)+(?:-[0-9]+)?"
X_HEAD_SEC_ROMAN = re.compile(r"(?m)^#{1,3} ([IVX]+(?:\.[0-9]+)+)(?=[ .])")
X_CAPTION_ROMAN = re.compile(r"(?:표|그림)\s([IVX]+(?:\.[0-9]+)*-[0-9]+|[IVX]+(?:\.[0-9]+)+)")
X_REF_SEC_ROMAN = re.compile(r"(?<![\w.])(" + NUM_ROMAN + r")(?![0-9])")
X_OBSOLETE_ROMAN = re.compile(r"(?m)^.*\|\s*구 (?:" + NUM_ROMAN + r"|[^|]*구 " + NUM_ROMAN + r")[^|]*\|.*$")
# 절 번호처럼 생긴 날짜·판 번호·표준 번호는 참조가 아니다
X_VER_BEFORE = re.compile(r"(?:(?<![A-Za-z])[vV]|[vV]er\.?\s?|버전\s?|(?<![A-Za-z0-9])[A-Za-z][A-Za-z\-]+\s)$")
_VER = r"\d+(?:\.\d+)+\+?(?:\([^)\n]{0,12}\))?"
X_VER_CHAIN = re.compile(r"(?:(?<![A-Za-z])[vV]|(?<![A-Za-z0-9])[A-Za-z][A-Za-z\-]+\s)" + _VER
                         + r"(?:\s?[·,/]\s?" + _VER + r")*\s?[·,/]\s?$")
X_VER_AFTER = re.compile(r"\+?\((?:19|20)\d{2}")


def not_section_ref(text: str, start: int, end: int, num: str) -> bool:
    """절 번호 꼴이지만 날짜·판·표준 번호인 것. ① 첫 마디가 세 자리 이상(연도·표준 번호)."""
    first = num.split(".")[0]
    if first.isdigit() and len(first) >= 3:  # 로마 숫자 부(`III`)는 연도가 아니다
        return True
    pre = text[max(0, start - 80):start]
    if X_VER_BEFORE.search(pre) or X_VER_CHAIN.search(pre):
        return True
    return bool(X_VER_AFTER.match(text, end))


def dead_xrefs(text: str, anchors: set, peer: tuple = (), ref_re: re.Pattern = X_REF_SEC) -> list[str]:
    """앵커가 없는 절 번호 참조. 같은 파일에서 판 번호로 밝혀진 수는 다른 자리에서도 판 번호다."""
    hits = [(m.group(1), m.start(1), m.end(1)) for m in ref_re.finditer(text)]
    versions = {s for s, a, b in hits if not_section_ref(text, a, b, s)}
    return [s for s, a, b in hits
            if not (s in anchors or (peer and s.startswith(peer)) or s in versions)]


@gate("V30", samples=[
    Sample(sample_model(tree={"a.md": "## 3.2.1 제목\n\n3.2.2절을 보라.\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "## 3.2.1 제목\n\n3.2.1절과 IEEE 802.15.4를 보라.\n"}), expect=0),
])
def v30_md_xrefs(model: DocModel) -> GateOutput:
    """md 상호참조 — 앵커(표제·캡션)가 없는 절 번호·별첨 번호 참조. 앵커는 전 파일에서 먼저 모은다."""
    roman = _style(model) == "roman"
    head_sec, caption = (X_HEAD_SEC_ROMAN, X_CAPTION_ROMAN) if roman else (X_HEAD_SEC, X_CAPTION)
    ref_sec, obsolete = (X_REF_SEC_ROMAN, X_OBSOLETE_ROMAN) if roman else (X_REF_SEC, X_OBSOLETE)
    letters = appendix_letters(model.extra)
    head_apx = re.compile(rf"(?m)^#{{1,3}} ([{letters}]-[0-9]+)(?=[ .])")
    ref_apx = re.compile(rf"별첨\s*([{letters}]-[0-9]+)")
    peer = tuple(str(p) for p in _cfg(model).get("peer_prefix") or ())
    texts = _texts(model)
    anchors: set[str] = set()
    for t in texts.values():
        anchors |= set(head_sec.findall(t)) | set(head_apx.findall(t)) | set(caption.findall(t))
    out: list[Finding] = []
    for name, text in texts.items():
        t = obsolete.sub("", text)
        for m in dead_xrefs(t, anchors, peer, ref_sec):
            out.append(Finding(name, f"죽은 참조 {m}"))
        for m in ref_apx.findall(t):
            if m not in anchors:
                out.append(Finding(name, f"죽은 참조 별첨 {m}"))
    return GateOutput(len(texts), out)


# ═══ V31 표제 형식 (prose_gates 192-202 · 408 · 960-974) ═══

T_QUESTION = re.compile(r"(?:무엇|어떻게|어디|누가|얼마|왜\s)|(?:나|까|는가|은가)\s*$")
# 표제가 「…다」로 끝나면 평서문이다. 「잣대」·「대」 같은 명사 꼬리만 뺀다
T_ASSERT = re.compile(r"(?<![가-힣]대)다\s*$")
T_REASON = re.compile(r"(?:이유|까닭|배경)\s*$")
T_SUBTITLE = re.compile(r"\s[—–]\s")  # noqa: RUF001 — 줄표·엔대시 모두
MAX_TITLE = 20  # 공백 제외
CONC_BLOCK = re.compile(r"(?ms)^## \d+\. 결론[ \t]*\r?\n.*?(?=^\*\*인용 참고문헌|\Z)")


def _meta_re(model: DocModel) -> re.Pattern:
    """메타 표제 — 「이 장」·「들어가며」. 문서가 자기를 부르는 말(시리즈 「작물편」)은 `extra.prose.meta_words`."""
    words = "".join("|" + re.escape(str(w)) for w in _cfg(model, "prose").get("meta_words") or [] if str(w))
    return re.compile(r"이\s*(?:장|절|부|영역|판" + words + r")|들어가며|답하는 것"
                      r"|이 (?:장|절|부)의 (?:지위|자리)|왜 이 절")


@gate("V31", samples=[
    Sample(sample_model(tree={"a.md": "## 1.1 왜 노지인가\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "## 1.1 관측 체계\n"}), expect=0),
])
def v31_title_form(model: DocModel) -> GateOutput:
    """표제 — 의문형·이유형·주장 서술형·메타·부제·20자 넘음."""
    style = _style(model)
    t_meta = _meta_re(model)
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for _lvl, num, title, line, _body in sections(CONC_BLOCK.sub("", text), style):
            loc = f"{name}:{line}"
            if T_QUESTION.search(title):
                out.append(Finding(loc, f"의문형 표제 — {num} {title[:40]}"))
            elif T_REASON.search(title):
                out.append(Finding(loc, f"이유형 표제 — {num} {title[:40]}"))
            elif T_ASSERT.search(title):
                out.append(Finding(loc, f"주장 서술형 표제 — {num} {title[:40]}"))
            elif t_meta.search(title):
                out.append(Finding(loc, f"메타 표제 — {num} {title[:40]}"))
            elif T_SUBTITLE.search(title):
                out.append(Finding(loc, f"부제 달린 표제 — {num} {title[:40]}"))
            elif (n := len(re.sub(r"\s", "", title))) > MAX_TITLE:
                out.append(Finding(loc, f"긴 표제 {n}자 — {num} {title[:40]}"))
    return GateOutput(len(texts), out)


# ═══ V34 절 도입부 (prose_gates 1021-1042) ═══

@gate("V34", samples=[
    Sample(sample_model(tree={"a.md": "## 1.1 가\n\n### 1.1.1 나\n본문\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "## 1.1 가\n\n이 절은 관측값을 기록하는 요건과 그 쓰임을 정하고 남는 물음을"
                                      " 다음 절로 넘기며 관측 주기와 기록 단위도 함께 밝힌다.\n\n### 1.1.1 나\n"}),
           expect=0),
])
def v34_section_lead(model: DocModel) -> GateOutput:
    """`##` 절 제목 바로 뒤에 `###`가 오면 도입부가 빈 것(40자 미만). 「발간사」 같은 면제는 설정으로."""
    style = _style(model)
    exempt = [str(t) for t in _cfg(model).get("intro_exempt_titles") or [] if str(t)]
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        lines = text.split("\n")
        tops = _tops(lines, style)
        for k, (i, m) in enumerate(tops):
            j = tops[k + 1][0] if k + 1 < len(tops) else len(lines)
            lead: list[str] = []
            for k2 in range(i + 1, j):
                if lines[k2].startswith("### "):
                    break
                lead.append(lines[k2])
            txt = MARKUP.sub("", "\n".join(lead))
            txt = re.sub(r"[\s─—·|:\-]", "", txt)
            if len(txt) < 40 and not any(t in lines[i] for t in exempt):
                out.append(Finding(f"{name}:{i + 1}",
                                   f"절 도입부 없음 — {m.group(1)} "
                                   f"{lines[i][3 + len(m.group(1)):][:30].strip()}"))
    return GateOutput(len(texts), out)


# ═══ V39 표제 꼴 (prose_gates 262-277 · 816-831) ═══

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
_HEAD_NUM = (r"제?\d+(?:\.[\dA-Z]+)*[장절]?\.?\s*(?:—|-|:)?\s*|[A-Z]-\d+\.?\s*(?:—|-)?\s*|\d+\.\s+")
_HEAD_NUM_RE = re.compile(rf"^(?:{_HEAD_NUM})")
_HEAD_NUM_ROMAN_RE = re.compile(rf"^(?:[IVX]+(?:\.[\dA-Z]+)+\.?\s*(?:—|-|:)?\s*|{_HEAD_NUM})")
HEAD_FORM = [
    ("물음꼴 표제", re.compile(r"(?:[운은인는한른]가|을까|할까|일까|정하나|보나|맞나|있나|없나|되나|드나|오나|쓰나|\?)$")),
    ("「~때」 꼴 표제", re.compile(r"[가-힣]\s때$")),
    ("연결어미 표제", re.compile(r"(?:하고|하며|하면|해서|지만|는데|으며|으면)$")),
]


def head_text(raw: str, style: str = "arabic") -> str:
    """표제에서 번호·강조·앵커를 뗀 글."""
    t = re.sub(r"\*\*|`", "", raw).strip()
    t = (_HEAD_NUM_ROMAN_RE if style == "roman" else _HEAD_NUM_RE).sub("", t).strip()
    return re.sub(r"\s*\{#[^}]*\}$", "", t)


@gate("V39", samples=[
    Sample(sample_model(tree={"a.md": "## 처방이 부딪힐 때\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "## 수확 적기 판정\n"}), expect=0),
])
def v39_heading_form(model: DocModel) -> GateOutput:
    """표제 꼴 — 물음꼴·「~때」 꼴·연결어미, 절과 바로 아래 항이 같은 표제. INDEX.md는 목차라 뺀다."""
    style = _style(model)
    texts = {n: t for n, t in _texts(model).items() if not n.endswith("INDEX.md")}
    out: list[Finding] = []
    for name, text in texts.items():
        heads = []
        for ln, line in enumerate(text.split("\n"), 1):
            hm = HEADING.match(line)
            if not hm:
                continue
            t = head_text(hm.group(2), style)
            heads.append((len(hm.group(1)), t, ln))
            for label, rx in HEAD_FORM:
                if rx.search(t):
                    out.append(Finding(f"{name}:{ln}", f"{label} — {t[:40]}"))
        for lv, t, _ln in heads:
            for lv2, t2, ln2 in heads:
                if lv2 == lv + 1 and t2 == t and t:
                    out.append(Finding(f"{name}:{ln2}", f"절과 항이 같은 표제 — {t[:40]}"))
    return GateOutput(len(texts), out)


# ═══ V44 물음꼴 볼드 소표제 (prose_gates 292 · 856-857) ═══

BOLD_QUESTION = re.compile(r"\*\*[^*\n]{2,40}(?:(?:[은는른운한된진던]|인)가[.?]?|[을일할]까[.?]?"
                           r"|[가-힣](?:나|냐|가)\?)\*\*")
PROSE_SKIP = re.compile(r"^\s*(?:\||```)")


@gate("V44", samples=[
    Sample(sample_model(tree={"a.md": "**왜 이 다섯인가.**\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "**적용.**\n"}), expect=0),
])
def v44_bold_question(model: DocModel) -> GateOutput:
    """「**왜 이 다섯인가.**」 꼴 물음 볼드 소표제(표·펜스 밖)."""
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
            for m in BOLD_QUESTION.finditer(line):
                out.append(Finding(f"{name}:{i + 1}", f"물음꼴 볼드 소표제 — {m.group(0)[:30]}"))
    return GateOutput(len(texts), out)


# ═══ V72 별첨 번호 꼴 (prose_gates 375-376 · 746-747) ═══

@gate("V72", samples=[
    Sample(sample_model(tree={"a.md": "**표 A-1-2.** 작기 일정\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "**표 A-2.** 작기 일정\n"}), expect=0),
])
def v72_appendix_number(model: DocModel) -> GateOutput:
    """별첨 표·그림 번호는 「표 A-n」 — 「표 A-1-n」(별첨 안 절 번호를 끼운 꼴)은 쓰지 않는다."""
    appx = re.compile(rf"(?:표|그림) [{appendix_letters(model.extra)}]-\d+-\d+")
    texts = {n: t for n, t in _texts(model).items() if not n.endswith("INDEX.md")}
    out: list[Finding] = []
    for name, text in texts.items():
        infence = False
        for i, line in enumerate(text.split("\n")):
            if line.strip().startswith("```"):
                infence = not infence
                continue
            if infence or not line.strip() or HEADING.match(line):
                continue
            for m in appx.finditer(line):
                out.append(Finding(f"{name}:{i + 1}", f"별첨 번호 꼴 — {m.group(0)}"))
    return GateOutput(len(texts), out)


# ═══ V78 항 안 번호 층위 (prose_gates 1239-1299 · 1960-1965) ═══

_SUB_KIND = [("1)", re.compile(r"^(\d+)\)\s*")), ("1.", re.compile(r"^(\d+)\.\s+")),
             ("①", re.compile(r"^([①-⑳])\s*")), ("가.", re.compile(r"^([가-하])[.)]\s+")),
             ("(1)", re.compile(r"^\((\d+)\)\s*"))]
_OL_LINE = re.compile(r"^\d+\.\s+\S")
# 절 파일을 두지 않는 폴더 — 앞붙이·부록·별첨(한국어 문서 일반 이름). 시리즈 `0_`은 설정으로
DEFAULT_FOLDER_NAMES = ("개요", "부록", "별첨")


@lru_cache(maxsize=16)
def _v78_limits(layers: tuple = ()) -> tuple[int, str]:
    lim = (load_dict("gate_limits.json", list(layers)) or {}).get("V78") or {}
    return (int(lim.get("max_subitems") or 7),
            lim.get("summary_names") or r"^(?:종합|정리|요약|소결)(?:\s|$)")


def _sub_kind(title: str):
    for k, rx in _SUB_KIND:
        m = rx.match(title)
        if m:
            return k, m.group(1), title[m.end():].strip()
    return "없음", None, title.strip()


def subitem_issues(text: str, max_subitems: int | None = None,
                   summary_name: re.Pattern | None = None,
                   layers: tuple = ()) -> list[tuple[int, str]]:
    """(줄 번호, 메시지) — 한 항(`## n.`) 안의 소항(`###`)·목록 번호. 결론 항은 보지 않는다."""
    lim_n, lim_rx = _v78_limits(layers)
    max_subitems = lim_n if max_subitems is None else max_subitems
    summary_name = summary_name or re.compile(lim_rx)
    lines = text.split("\n")
    blocks, cur, fence = [], None, False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r"^(#{2,3})\s+(.+?)\s*$", ln)
        if m and len(m.group(1)) == 2:
            cur = {"line": i + 1, "title": m.group(2), "subs": [], "ol": []}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        if m:
            cur["subs"].append((i + 1, m.group(2)))
        elif _OL_LINE.match(ln):  # 들여쓰지 않은 번호 목록만(상자 안 목록은 들여 씀)
            cur["ol"].append(i + 1)
    out = []
    for b in blocks:
        if re.search(r"결론\s*$", b["title"]):
            continue
        kinds = [(ln, *_sub_kind(t)) for ln, t in b["subs"]]
        numbered = [k for k in kinds if k[1] != "없음"]
        ks = sorted({k[1] for k in numbered})
        head = f"{b['title'][:24]}"
        if len(ks) > 1:
            out.append((b["line"], f"소항 번호 종류 섞임({'·'.join(ks)}) — {head}"))
        if numbered and len(numbered) < len(kinds):
            out.append((b["line"], f"번호 있는 소항과 없는 소항 섞임 — {head}"))
        for kind in ks:
            seq = [k[2] for k in numbered if k[1] == kind]
            if kind in ("1)", "1.", "(1)"):
                want = [str(n) for n in range(1, len(seq) + 1)]
                if seq != want:
                    out.append((b["line"], f"소항 번호 어긋남({','.join(seq)}) — {head}"))
        if len(kinds) > max_subitems:
            out.append((b["line"], f"소항 {len(kinds)}개(> {max_subitems}) — 묶을 갈래 — {head}"))
        for ln, _k, _n, rest in kinds:
            if summary_name.search(rest):
                out.append((ln, f"「종합」류 소항 — {rest[:24]}"))
        if b["ol"] and any(k[1] == "1)" for k in numbered):
            out.append((b["ol"][0], f"「1.」 목록과 「1)」 소항이 한 항에 섞임 — {head}"))
    return out


@gate("V78", samples=[
    Sample(sample_model(tree={"제1부/1.1. 가.md": "## 1. 갈래\n\n### 1) 가\n\n### 3) 나\n"}), expect=1),
    Sample(sample_model(tree={"제1부/1.1. 가.md": "## 1. 갈래\n\n### 1) 가\n\n### 2) 나\n"}), expect=0),
])
def v78_subitem_levels(model: DocModel) -> GateOutput:
    """항 안 번호 층위 — 소항 번호 종류 섞임·어긋남·너무 많음·「종합」 소항·목록과 소항 섞임.

    독자가 보는 렌더 트리의 절 파일(`N.M. 제목.md`)만 본다. 트리가 없으면 산문 원고.
    """
    style = _style(model)
    file_re = section_file_re(style)
    folders = tuple(str(f) for f in (_cfg(model).get("folder_names") or DEFAULT_FOLDER_NAMES))
    files = ({tf.rel: tf.text for tf in model.tree} if model.tree else _texts(model))
    layers = layers_key(model)
    out: list[Finding] = []
    targets = 0
    for key, text in files.items():
        segs = key.split("/")
        if segs[-1] == "INDEX.md":
            continue
        if not file_re.match(segs[-1]) or any(s.startswith(folders) for s in segs[:-1]):
            continue
        targets += 1
        for ln, msg in subitem_issues(text, layers=layers):
            out.append(Finding(f"{key}:{ln}", msg))
    return GateOutput(targets, out)
