"""인용·서지 게이트 — V8·V13·V45·V68 (v1.11-a, 시리즈 check_v2·prose_gates에서 이식).

원본 로직을 그대로 옮기고 입력만 DocModel로 바꿨다. 시리즈 고유 값(내부 작업 파일 이름,
백과사전 면제 목록)은 `extra.citation`에서 받는다. 의도된 차이는 하나 — V68이 영문 단체
지은이 「… Team」을 자리표시로 잡는다(시리즈 다음판 3).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

from techdoc_core.qc.card_text import card_texts
from techdoc_core.qc.model import DocModel, TreeFile
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

# ── 인용 추출 (check_v2.cited_refs) ──
# 인라인 코드 안 REF는 인용이 아니라 표기 대상. 「수확편:REF-162」꼴은 다른 문서의 번호.
_REF_TICK = re.compile(r"`[^`\n]*?(REF-\d{3,4})[^`\n]*?`")
_REF_ANY = re.compile(r"(?<!:)REF-\d{3,4}")
# 펜스는 여는 줄·닫는 줄 짝으로. mermaid 펜스는 그림 속 인용이라 내용을 남긴다.
_FENCE_ANY = re.compile(r"```([^\n]*)\n([\s\S]*?)```")


def _fence_sub(m: re.Match) -> str:
    return " " + m.group(2) + " " if m.group(1).strip().startswith("mermaid") else " "


def cited_refs(text: str) -> set[str]:
    """본문이 실제로 인용한 REF 번호. 백틱·코드 펜스 안은 세지 않는다(mermaid는 셈)."""
    text = text.replace("\\n", "\n")
    text = _FENCE_ANY.sub(_fence_sub, text).replace("```", "   ")
    return set(_REF_ANY.findall(_REF_TICK.sub(" ", text)))


def _walk_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _walk_strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk_strings(x)


def _citation_cfg(model: DocModel) -> dict:
    return (model.extra or {}).get("citation") or {}


# ── V8 ──

@gate("V8", samples=[
    Sample(sample_model(cards={"1.1": {"sections": {"s": {"body": "[REF-001] [REF-002]"}}}},
                        references=[{"id": "REF-001"}]), expect=1),
    Sample(sample_model(cards={"1.1": {"sections": {"s": {"body": "[REF-001]"}}}},
                        references=[{"id": "REF-001"}]), expect=0),
])
def v8_ref_integrity(model: DocModel) -> GateOutput:
    """인용됐으나 목록에 없는 REF · 목록에 있으나 어디서도 안 부르는 고아 REF.

    원천은 카드(self_check 제외)와 md 직접 저작 원고(draft)다. 렌더 트리는 끝에 참고문헌
    목록이 통째로 붙어 모든 REF가 「쓰인 것」이 되므로 원천에서 뺀다(거짓 통과 방지).
    """
    if not model.references:
        return GateOutput(0, [])
    have = {str(r.get("id")) for r in model.references if r.get("id")}
    used: set[str] = set()
    for card in model.cards.values():
        probe = {k: v for k, v in card.items() if k != "self_check"}
        for s in _walk_strings(probe):
            used |= cited_refs(s)
    for tf in model.draft:
        used |= cited_refs(tf.text)
    out = [Finding(r, f"인용됐으나 목록에 없음: {r}") for r in sorted(used - have)]
    out += [Finding(r, f"고아 REF(어디서도 인용 안 함): {r}") for r in sorted(have - used)]
    return GateOutput(len(model.references), out)


# ── V13 ──

_NON_PRIMARY = re.compile(r"wikipedia\.org|bionity\.com|namu\.wiki|\bwikipedia\b", re.I)
_CITED_LIST = re.compile(r"인용 참고문헌 \((\d+)건\)\.\*\*(.{0,1200})", re.S)


@gate("V13", samples=[
    Sample(sample_model(cards={"1.1": {"sections": {"s": {"body": "x"}}}},
                        references=[{"id": "REF-001", "url": "https://a/x", "title": "T"},
                                    {"id": "REF-002", "url": "https://a/x/", "title": "T"}]),
           expect=1),
    Sample(sample_model(cards={"1.1": {"sections": {"s": {"body": "x"}}}},
                        references=[{"id": "REF-001", "url": "https://a/x", "title": "T"}]),
           expect=0),
])
def v13_ref_registry(model: DocModel) -> GateOutput:
    """같은 문헌 중복 등록 · 비원전(백과사전) 출처 · 카드 말미 「인용 참고문헌」 목록 정합."""
    out: list[Finding] = []
    by_url: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in model.references:
        u = str(r.get("url", "")).strip().rstrip("/")
        t = re.sub(r"\s+", "", str(r.get("title", "")))[:40]
        if u:
            by_url[(u, t)].append(str(r.get("id")))
    for (u, _t), ids in by_url.items():
        if len(ids) > 1:
            out.append(Finding("=".join(ids), f"동일 문헌 중복 등록: {'='.join(ids)}  {u[:60]}"))
    np_ok = _citation_cfg(model).get("nonprimary_ok") or {}
    cards_dump = json.dumps(model.cards, ensure_ascii=False)
    for r in model.references:
        rid = str(r.get("id"))
        if rid in np_ok or not _NON_PRIMARY.search(str(r.get("url", ""))):
            continue
        n = len(re.findall(re.escape(rid), cards_dump))
        out.append(Finding(rid, f"비원전 출처(백과사전 등): {rid} — 본문 인용 {n}회  "
                                f"{str(r.get('title', ''))[:40]}"))
    for cid, card in model.cards.items():
        whole = "\n".join(b for _, _, b in card_texts(card))
        m = _CITED_LIST.search(whole)
        if not m:
            continue
        listed = set(re.findall(r"REF-\d{3,4}", m.group(2)))
        used = set(re.findall(r"REF-\d{3,4}", whole[:m.start()]))
        for r in sorted(used - listed):
            out.append(Finding(f"{cid}:{r}", f"{cid} 말미 인용 목록에 없음: {r}"))
        for r in sorted(listed - used):
            out.append(Finding(f"{cid}:{r}", f"{cid} 말미 목록에만 있고 본문에 없음: {r}"))
    return GateOutput(len(model.references) + len(model.cards), out)


# ── V45 ──

# 인용 뒤 괄호 덧말이 붙어 마크다운 링크가 된 것. 주소 꼴(http·경로·.md/.html·앵커)은 제외.
_REF_PAREN_LINK = re.compile(
    r"\[(?:USER-)?REF-\d{3,4}\]\((?!https?:|mailto:|#|\.{0,2}/)"
    r"(?![^()\n]*\.(?:md|html?)(?:#[^()\n]*)?\))"
    r"(?:[^()\n]|\([^()\n]*\)){1,300}\)")
_REF_PAREN_OPEN = re.compile(r"\[(?:USER-)?REF-\d{3,4}\]\((?!https?:|mailto:|#|\.{0,2}/)[^()\n]*$")


@gate("V45", samples=[
    Sample(sample_model(tree={"a.md": "근거[REF-003](표 1-2)."}), expect=1),
    Sample(sample_model(tree={"a.md": "근거[REF-003] (표 1-2)."}), expect=0),
])
def v45_ref_paren_link(model: DocModel) -> GateOutput:
    """인용 바로 뒤 괄호가 링크 주소로 읽혀 웹북에서 죽은 링크가 되는 꼴."""
    files = model.prose()
    out: list[Finding] = []
    for tf in files:
        in_fence = False
        for i, line in enumerate(tf.text.split("\n")):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in [*_REF_PAREN_LINK.finditer(line), *_REF_PAREN_OPEN.finditer(line)]:
                out.append(Finding(f"{tf.rel}:{i + 1}",
                                   f"인용 뒤 괄호가 링크로 읽힘 — {m.group(0)[:40]} (사이에 한 칸)"))
    return GateOutput(len(files), out)


# ── V68 ──

_REF_INTERNAL_BUILTIN = r"\.\./|_card\.json"
_REF_PLACEHOLDER = re.compile(
    r"(?:\bet al\.|\bauthors\b|^Various\b|^Author\b|연구진|저자진|게재 저자|미상|연구팀|개발팀|저자팀"
    r"|공저자|다수 공저|\(인용\)|(?:^|\s)외(?=[\s.,)&]|$)|\(추정\)|& 다수|^다수\.?$"
    r"|(?:^|\s)Team\.?$)", re.I)  # 「… Team」 단체 지은이 — 시리즈 다음판 3에서 보완
# 인용 변환기(apa_cite.PLACEHOLDER)와 같은 기준의 지은이 자리표시
_AUTHOR_PLACEHOLDER = re.compile(
    r"^(?:|et al\.?|authors?|various|unknown|anonymous|n/?a|미상|저자 ?미상|연구진|저자진|게재 저자|"
    r"연구팀|개발팀|저자팀|공저자|다수|다수 공저|복수 ?저자|여러 ?저자|\(.*\)|「.*」 ?저자|[-—?])$", re.I)


def _internal_re(model: DocModel) -> re.Pattern:
    names = [re.escape(str(n)) for n in _citation_cfg(model).get("internal_files") or []]
    return re.compile("(?:" + "|".join([_REF_INTERNAL_BUILTIN, *names]) + ")")


def ref_list_issues(text: str, internal: re.Pattern) -> list[str]:
    """참고문헌 md 한 벌의 문제 — 내부 파일·지은이 자리표시·국문/영문 묶음·정렬."""
    out: list[str] = []
    sec, prev = "", None
    for ln in text.split("\n"):
        if ln.startswith("## "):
            sec, prev = ln, None
            continue
        if not ln.startswith("- "):
            continue
        e = ln[2:]
        m = re.search(r"\[(REF-\d+)\]\s*$", e)
        rid = m.group(1) if m else "?"
        lead = re.split(r"\s\(\d{4}[a-z]?\)|\s\(n\.d\.\)", e, maxsplit=1)[0].strip()
        if internal.search(e):
            out.append(f"내부 작업 파일 — {rid} {e[:40]}")
        if _REF_PLACEHOLDER.search(lead):
            out.append(f"지은이 자리표시 — {rid} {lead[:40]}")
        first = next((c for c in lead if c.isalpha()), "")
        if ("국문" in sec and not re.match(r"[가-힣]", first)) or \
                ("영문" in sec and re.match(r"[가-힣]", first)):
            out.append(f"묶음 어긋남 — {rid} {lead[:30]}")
        key = lead.split(",")[0].rstrip(". ").casefold()
        if prev is not None and key < prev:
            out.append(f"정렬 어긋남 — {rid} {lead[:30]}")
        prev = key
    return out


def _entries(tf: TreeFile) -> int:
    return sum(1 for ln in tf.text.split("\n") if ln.startswith("- "))


@gate("V68", samples=[
    Sample(sample_model(reference_md={"참고문헌.md": "## 영문\n- et al. (2020). T. [REF-001]\n"}),
           expect=1),
    Sample(sample_model(reference_md={"참고문헌.md": "## 영문\n- Kim, H. (2020). T. [REF-001]\n"}),
           expect=0),
])
def v68_reference_list(model: DocModel) -> GateOutput:
    """참고문헌 목록: 독자가 볼 수 없는 내부 파일 · 지은이 자리표시·빈칸 · 묶음과 정렬."""
    internal = _internal_re(model)
    out: list[Finding] = []
    for tf in model.reference_md:
        out += [Finding(tf.rel, msg) for msg in ref_list_issues(tf.text, internal)]
    for r in model.references:
        authors = [a for a in (r.get("authors") or []) if str(a).strip()]
        authors = [a for a in authors if not _AUTHOR_PLACEHOLDER.match(str(a).strip())]
        if not authors:
            out.append(Finding("reference_list.json",
                               f"지은이 빈칸 — {r.get('id')} {str(r.get('title') or '')[:30]}"))
    targets = sum(_entries(tf) for tf in model.reference_md) + len(model.references)
    return GateOutput(targets, out)
