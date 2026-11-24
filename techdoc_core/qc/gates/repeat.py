"""같은 틀 되풀이 게이트 — V88 (v1.11-b 신규, F88).

원리(E17, 네 원칙 「중복성 배제」 — 품질 아래): **한 장 안에서 소표제가 같은 틀로 되풀이되면 독자는
절마다 새 내용을 기대하지 못한다.** 원본 시리즈 게이트가 없는 신규 게이트라 특정 문서의 건수에
맞춰 정하지 않는다.

- 표제: 산문(`model.prose()`)의 `##`·`###` 표제(코드 펜스 밖). 앵커 `{#…}`·굵게·인라인 코드 표시와
  번호 접두(번호 꼴 설정을 따름 — `3.2`·`II.6.1`·`2.A.7`·`(1)`)를 걷는다.
- 표제 머리: 구분 기호 「—」·「:」 앞 부분. 구분 기호가 없으면 표제 전체. 공백은 하나로 모은다.
- 장: 렌더 트리의 장 폴더(파일의 부모 폴더). 폴더 없이 놓인 파일은 번호 꼴의 절 파일 이름
  (`3.1. 제목.md`)에서 장 번호를 읽고, 그것도 없으면 파일 하나를 장으로 본다.
- 같은 머리가 장 안에서 `extra.repeat.max_repeats`(1 이상 정수, 기본 3)회를 넘으면 넘은 표제마다
  지적한다. 0·음수·정수 아님은 설정 읽기(`config.validate_extra`)에서 거절한다.
- 허용 목록 `extra.repeat.allow_heads`(프로젝트·시리즈 설정 — 예: 「사례」 장마다 같은 소표제)와
  `extra.repeat.block_heads`(문서 종류 묶음 — 렌더러가 카드마다 내는 고정 블록 표제)에 든 머리는 세지
  않는다. 둘은 합친다 — 프로젝트가 allow_heads를 적어도 문서 종류의 블록 표제는 남는다.
- **장을 가로지르는 틀**(v1.11-c, F113): 머리 하나의 장 안 횟수로는 분할마다 한 번씩 되풀이되는 틀
  (장 안 3회씩 여러 장)을 원리상 못 본다. 그래서 서로 다른 머리 `extra.repeat.frame_heads`(기본 3)개가
  같은 차례로 이어진 묶음이 `extra.repeat.frame_chapters`(기본 4)개 이상의 장에 나오면 그 틀이 나온
  장마다 지적 하나를 더 낸다. 허용 머리는 차례에서 미리 빼므로 카드 블록 표제는 틀이 되지 않는다.
- 문서 종류 tech_report 묶음(`bundles/kinds/tech_report/kind.yaml`)이 플러그인 카드 블록 표제
  (`constants.DEFAULT_SECTION_TITLES` — 「정의·범위」「원리·구조」…)를 block_heads로 싣는다(v1.11-c Task 4,
  예전에는 이 게이트의 kind 분기였다).
"""
from __future__ import annotations

import re
from collections import Counter

from techdoc_core.qc.model import DocModel
from techdoc_core.qc.numbering import ROMAN, section_file_re
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

FENCE = re.compile(r"^\s*(?:```|~~~)")
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
ANCHOR = re.compile(r"\{#[^}\n]*\}")
MARKS = re.compile(r"\*\*|__|`")
_NUM_PREFIX = {
    "arabic": r"\d+(?:[.\-]\d+)*",
    "roman": rf"(?:{ROMAN}|\d+)(?:[.\-]\d+)*",
    "letter_middle": r"\d+(?:\.[A-Z0-9]+)*",
}
SEPARATOR = re.compile(r"\s*[—:]\s*")
DEFAULT_MAX = 3
DEFAULT_FRAME_HEADS = 3  # 틀로 보는 머리 묶음의 길이
DEFAULT_FRAME_CHAPTERS = 4  # 틀이 이만큼의 장에 나오면 지적


def _style(model: DocModel) -> str:
    s = (model.numbering or {}).get("section") or "arabic"
    return s if s in _NUM_PREFIX else "arabic"


def _num_prefix_re(style: str) -> re.Pattern:
    return re.compile(rf"^(?:\(\d+\)|{_NUM_PREFIX[style]}[.)]?)\s+")


def heading_head(title: str, style: str = "arabic") -> str:
    """표제 → 머리 — 표시·번호 접두를 걷고 구분 기호(「—」·「:」) 앞만."""
    t = MARKS.sub("", ANCHOR.sub("", title)).strip()
    t = _num_prefix_re(style).sub("", t, count=1)
    parts = SEPARATOR.split(t, maxsplit=1)
    head = parts[0].strip() or t.strip()
    return re.sub(r"\s+", " ", head)


def chapter_of(rel: str, style: str = "arabic") -> str:
    """장 키 — 부모 폴더, 폴더가 없으면 절 파일 이름의 장 번호, 그것도 없으면 파일."""
    if "/" in rel:
        return rel.rsplit("/", 1)[0]
    m = section_file_re(style).match(rel)
    return f"장 {m.group(1)}" if m else rel


def headings(text: str):
    """(줄번호, 표제 글) — `##`·`###`, 코드 펜스 밖."""
    infence = False
    for i, ln in enumerate(text.split("\n"), 1):
        if FENCE.match(ln):
            infence = not infence
            continue
        if infence:
            continue
        m = HEADING.match(ln)
        if m:
            yield i, m.group(2)


def _cfg(model: DocModel) -> dict:
    return (model.extra or {}).get("repeat") or {}


_FRAME = "".join(f"## {i}. 무엇을 정하나 — 항목 {i}\n\n본문.\n\n" for i in range(1, 5))


@gate("V88", samples=[
    Sample(sample_model(tree={"3장/3.1. 가.md": _FRAME}), expect=1),
    Sample(sample_model(tree={"3장/3.1. 가.md": _FRAME},
                        extra={"repeat": {"allow_heads": ["무엇을 정하나"]}}), expect=0),
    Sample(sample_model(tree={"3장/3.1. 가.md": "## 1. 배경\n\n## 2. 방법\n\n## 3. 결과\n"}), expect=0),
])
def v88_repeated_frame(model: DocModel) -> GateOutput:
    """같은 틀 되풀이 — 한 장 안에서 같은 표제 머리가 기준(기본 3회)을 넘게 되풀이됨."""
    style = _style(model)
    cfg = _cfg(model)
    allow = {re.sub(r"\s+", " ", str(a).strip()) for a in cfg.get("allow_heads") or [] if str(a).strip()}
    # 문서 종류 묶음의 고정 블록 표제 — 표제 머리 규칙(번호·구분 기호)을 거친 꼴로 비교
    allow |= {heading_head(str(t), style) for t in cfg.get("block_heads") or [] if str(t).strip()}
    limit = DEFAULT_MAX if cfg.get("max_repeats") is None else int(cfg["max_repeats"])
    seen: Counter[tuple[str, str]] = Counter()
    n = 0
    out: list[Finding] = []
    seq: dict[str, list[tuple[str, str]]] = {}  # 장 → [(머리, 위치)] 차례대로(허용 머리 뺌)
    for tf in model.prose():
        chap = chapter_of(tf.rel, style)
        for i, title in headings(tf.text):
            n += 1
            head = heading_head(title, style)
            if not head or head in allow:
                continue
            seq.setdefault(chap, []).append((head, f"{tf.rel}:{i}"))
            seen[chap, head] += 1
            k = seen[chap, head]
            if k > limit:
                out.append(Finding(f"{tf.rel}:{i}",
                                   f"같은 틀 되풀이 — 표제 머리 「{head}」가 장 「{chap}」 안에서 "
                                   f"{k}번째({limit}회 넘음)"))
    out += cross_chapter_frames(seq, cfg)
    return GateOutput(n, out)


def cross_chapter_frames(seq: dict[str, list[tuple[str, str]]], cfg: dict) -> list[Finding]:
    """장을 가로지르는 표제 틀(F113) — 서로 다른 머리 k개(`frame_heads`, 기본 3)가 같은 차례로 이어진
    묶음이 `frame_chapters`(기본 4)개 이상의 장에 나오면, 그 틀이 나온 장마다 지적 하나.

    머리 하나의 장 안 횟수(위)로는 분할마다 한 번씩 되풀이되는 틀(장 안 3회씩 여러 장)을 못 본다.
    허용 머리(`allow_heads`·`block_heads`)는 차례에서 미리 뺐으므로 문서 종류의 카드 블록 표제는 틀이
    되지 않는다.
    """
    k = int(cfg.get("frame_heads") or DEFAULT_FRAME_HEADS)
    need = int(cfg.get("frame_chapters") or DEFAULT_FRAME_CHAPTERS)
    grams: dict[str, dict[tuple[str, ...], str]] = {}  # 장 → {틀: 첫 위치}
    for chap, items in seq.items():
        found: dict[tuple[str, ...], str] = {}
        for j in range(len(items) - k + 1):
            g = tuple(h for h, _ in items[j:j + k])
            if len(set(g)) == k and g not in found:
                found[g] = items[j][1]
        grams[chap] = found
    count = Counter(g for found in grams.values() for g in found)
    frequent = {g for g, c in count.items() if c >= need}
    out: list[Finding] = []
    for chap, found in grams.items():
        hit = [g for g in found if g in frequent]
        if not hit:
            continue
        heads: list[str] = []
        for g in hit:
            heads += [h for h in g if h not in heads]
        shown = " → ".join(heads[:6]) + (" …" if len(heads) > 6 else "")
        n_ch = max(count[g] for g in hit)
        out.append(Finding(found[hit[0]],
                           f"같은 틀 되풀이 — 표제 머리 틀 「{shown}」이 {n_ch}개 장에 걸쳐 나옴"
                           f"(장 「{chap}」, 기준 {need}장)"))
    return out
