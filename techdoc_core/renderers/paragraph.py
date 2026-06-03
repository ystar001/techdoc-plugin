"""단락 break 유틸 (F10).

자식 render_md.py의 순수 단락 처리 로직을 흡수한다 — 키워드 기반 break +
길이 ceiling. 메타 단락 제거(_is_meta_paragraph)는 Plan H 담당이므로 제외한다.

MD 출력 전용. 멱등(이미 분리된 단락은 무변경)하며 LLM 호출 0회·결정론적.
"""
from __future__ import annotations

import re

# 단락 시작 키워드(접속사·문단 도입구) 앞에서 break 삽입.
_PARAGRAPH_BREAK_HEAD = re.compile(
    r"([.!?])\s+(?="
    r"본 [§\w가-힣]|"
    r"본\s|"
    r"한편[,\s]|"
    r"또한[,\s]|"
    r"이러한 |"
    r"이는 |"
    r"이에 |"
    r"그러나 |"
    r"다만 |"
    r"반면 |"
    r"더불어 |"
    r"요약하면|"
    r"결론적|"
    r"\([a-z]\)\s|"
    r"\([ivx]+\)\s|"
    r"\(\d+\)\s|"
    r"\(가-힣\)\s|"
    r"PRD §|"
    r"§\d|"
    r"§[가-힣]"
    r")"
)

# 한국 학술 톤 — 한 단락이 너무 길지 않도록 강제 break 길이.
MAX_PARAGRAPH_CHARS = 800


def enforce_length(paragraph: str, max_chars: int = MAX_PARAGRAPH_CHARS) -> str:
    """한 단락이 max_chars 초과 시 마침표/물음표/느낌표 후 강제 break."""
    if len(paragraph) <= max_chars:
        return paragraph
    out = []
    buf = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        if not sentence:
            continue
        if buf and len(buf) + len(sentence) + 1 > max_chars:
            out.append(buf.strip())
            buf = sentence
        else:
            buf = (buf + " " + sentence).strip() if buf else sentence
    if buf:
        out.append(buf.strip())
    return "\n\n".join(out)


def format_paragraphs(text: str) -> str:
    """단락 break 적용 — 키워드 우선 + 길이 ceiling. 멱등."""
    if not text:
        return text
    if "\n\n" in text:
        paras = text.split("\n\n")
    else:
        text = _PARAGRAPH_BREAK_HEAD.sub(r"\1\n\n", text)
        paras = text.split("\n\n")

    cleaned = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        cleaned.append(enforce_length(p))
    return "\n\n".join(cleaned)
