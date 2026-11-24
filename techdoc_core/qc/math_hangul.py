"""수식 안 한글의 자리 판정 — 시리즈 math_hangul.py를 옮김 (v1.11-b, V48).

  ① 「작은 한글」 — 첨자(_{…}·^{…}·_\\text{…})나 \\underbrace·\\overbrace 설명 안에 든 한글.
     TeX는 첨자를 0.707배로 그려 본문 10.5pt 수식이면 약 7.4pt — 하한 아래.
  ② 「맨 한글」 — \\text{…} 밖에 맨글로 쓴 한글. 수식 글꼴에 한글이 없어 시스템 명조로 떨어진다.

수식은 `$$…$$`와 `$…$`(통화 `\\$`·「$숫자」는 제외). 판정 로직은 원본 그대로다.
"""
from __future__ import annotations

import re

MATH = re.compile(r"\$\$(.+?)\$\$|(?<![\\$\w])\$(?!\s)([^$\n]+?)(?<!\s)\$(?![A-Za-z0-9_$])", re.S)
HANGUL = re.compile(r"[가-힣]")
CURRENCY = re.compile(r"\$(?=\d)([^$\\\n]*)(?=[$\\\n]|$)")


def scan_math(tex: str) -> list[tuple[str, str]]:
    """수식 하나 → [(종류, 조각)]. 종류는 '작은' 또는 '맨'."""
    out: list[tuple[str, str]] = []
    stack: list[dict] = []
    i, n = 0, len(tex)
    pending_script = False  # 바로 앞이 _ 또는 ^ — 다음 묶음(또는 \text)은 첨자
    while i < n:
        c = tex[i]
        # \text·\textrm·\mbox만 글자(mtext)다 — \mathrm·\operatorname은 수식 글꼴이라 명조로 떨어진다
        if tex.startswith(("\\text{", "\\textrm{", "\\mbox{"), i):
            j = tex.index("{", i)
            stack.append({"text": True, "script": pending_script})
            pending_script = False
            i = j + 1
            continue
        if c in "_^":
            pending_script = True
            i += 1
            continue
        if c == "{":
            stack.append({"text": False, "script": pending_script})
            pending_script = False
            i += 1
            continue
        if c == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if c == "\\":
            m = re.match(r"\\[A-Za-z]+", tex[i:])
            i += len(m.group(0)) if m else 2
            if not (m and m.group(0) in ("\\text",)):
                pending_script = False
            continue
        if HANGUL.match(c):
            in_text = any(s["text"] for s in stack)
            in_script = any(s["script"] for s in stack) or pending_script
            j = i
            while j < n and (HANGUL.match(tex[j]) or tex[j] in " ·"):
                j += 1
            frag = tex[i:j].strip()
            if in_script:
                out.append(("작은", frag))
            elif not in_text:
                out.append(("맨", frag))
            i = j
            pending_script = False
            continue
        if not c.isspace():
            pending_script = False if c not in "_^" else pending_script
        i += 1
    return out


def _mask_currency(md: str) -> str:
    """웹북 escape_currency와 같은 규칙 — 「$숫자」로 시작하고 다음 $·\\·줄끝까지 수식 표식(_^={})이
    없으면 통화로 보고 지운다. 백슬래시로 끝나면 수식으로 둔다. 줄 수는 그대로."""
    def rep(m: re.Match) -> str:
        end = m.end()
        if end < len(md) and md[end] == "\\":
            return m.group(0)
        if end < len(md) and md[end] == "$" and any(ch in "_^={}" for ch in m.group(1)):
            return m.group(0)
        return "\uff04" + m.group(1)  # 전각 $ — 수식 정규식이 짝짓지 않게(원본과 같은 글자)
    return CURRENCY.sub(rep, md)


def scan_md(md: str) -> list[tuple[int, str, str]]:
    """md 한 벌 → [(줄 번호, 종류, 조각)]. 코드 펜스 안은 보지 않는다."""
    md = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), md, flags=re.S)
    md = _mask_currency(md)
    res: list[tuple[int, str, str]] = []
    for m in MATH.finditer(md):
        tex = m.group(1) or m.group(2) or ""
        if HANGUL.search(tex):
            line = md.count("\n", 0, m.start()) + 1
            for kind, frag in scan_math(tex):
                res.append((line, kind, frag))
    return res
