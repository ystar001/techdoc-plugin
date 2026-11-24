"""같은 틀 되풀이 게이트 — V88 (v1.11-b 신규, F88).

원리(E17, 네 원칙 「중복성 배제」 — 품질 아래): **한 장 안에서 소표제가 같은 틀로 되풀이되면 독자는
절마다 새 내용을 기대하지 못한다.** 원본 시리즈 게이트가 없는 신규 게이트라 특정 문서의 건수에
맞춰 정하지 않는다.

- 표제: 산문(`model.prose()`)의 `##`·`###` 표제(코드 펜스 밖). 앵커 `{#…}`·굵게·인라인 코드 표시와
  번호 접두(번호 꼴 설정을 따름 — `3.2`·`II.6.1`·`2.A.7`·`(1)`)를 걷는다.
- 표제 머리: 구분 기호 「—」·「:」 앞 부분. 구분 기호가 없으면 표제 전체. 공백은 하나로 모은다.
- 장: 렌더 트리의 장 폴더(파일의 부모 폴더). 폴더 없이 놓인 파일은 번호 꼴의 절 파일 이름
  (`3.1. 제목.md`)에서 장 번호를 읽고, 그것도 없으면 파일 하나를 장으로 본다.
- 같은 머리가 장 안에서 `extra.repeat.max_repeats`(기본 3)회를 넘으면 넘은 표제마다 지적한다.
- 허용 목록 `extra.repeat.allow_heads`(문서 종류 설정 — 예: 「사례」 장마다 같은 소표제)에 든 머리는
  세지 않는다.
"""
from __future__ import annotations

import re
from collections import Counter

from techdoc_core.qc.model import DocModel
from techdoc_core.qc.numbering import section_file_re
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

FENCE = re.compile(r"^\s*(?:```|~~~)")
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
ANCHOR = re.compile(r"\{#[^}\n]*\}")
MARKS = re.compile(r"\*\*|__|`")
_NUM_PREFIX = {
    "arabic": r"\d+(?:[.\-]\d+)*",
    "roman": r"(?:[IVX]+|\d+)(?:[.\-]\d+)*",
    "letter_middle": r"\d+(?:\.[A-Z0-9]+)*",
}
SEPARATOR = re.compile(r"\s*[—:]\s*")
DEFAULT_MAX = 3


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
    limit = int(cfg.get("max_repeats") or DEFAULT_MAX)
    seen: Counter[tuple[str, str]] = Counter()
    n = 0
    out: list[Finding] = []
    for tf in model.prose():
        chap = chapter_of(tf.rel, style)
        for i, title in headings(tf.text):
            n += 1
            head = heading_head(title, style)
            if not head or head in allow:
                continue
            seen[chap, head] += 1
            k = seen[chap, head]
            if k > limit:
                out.append(Finding(f"{tf.rel}:{i}",
                                   f"같은 틀 되풀이 — 표제 머리 「{head}」가 장 「{chap}」 안에서 "
                                   f"{k}번째({limit}회 넘음)"))
    return GateOutput(n, out)
