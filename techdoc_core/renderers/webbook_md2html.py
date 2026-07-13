"""markdown → HTML 변환 + [REF-NNNN] 인용 앵커화 (순수 함수, LLM 0회).

웹북 렌더러(webbook.py)가 카드 markdown을 페이지 HTML로 변환할 때 사용한다.
자식 프로젝트의 `webbook/md2html.py`를 plugin으로 승격 (F52).

핵심:
  md_to_html(md, refs_href) -> (html_body, h2_toc)
    - python-markdown(tables·sane_lists·attr_list·toc·fenced_code)로 본문 변환
    - ```mermaid 코드블록을 변환 전 보호 → <pre class="mermaid">로 치환 (F48).
      webbook.js가 mermaid로 렌더 — node.textContent를 읽으므로 내용을 HTML 이스케이프.
    - $$…$$·$…$ 수식을 변환 전 placeholder로 보호 → 변환 후 원본 복원 (F38).
      python-markdown이 밑줄(아래첨자)을 emphasis로 훼손하는 것을 방지, MathJax가 렌더.
    - 표를 <div class="table-wrap">로 감싸 모바일 가로 스크롤 지원.
    - [REF-NNNN]·bare REF-NNNN(3~4자리)를 참고문헌 페이지 앵커로 치환.
    - H2 헤딩 목록을 (id, name)로 추출 → 페이지 내 TOC.
"""
from __future__ import annotations

import html as _html
import re

import markdown

# [REF-001] 또는 bare REF-001 (3~4자리). 앞에 #, =, ", 영숫자·/·- 가 오면 제외
# (이미 삽입된 href="#REF-…"·data-ref 속성 내부 오탐 방지 — 안전망 lookbehind).
_REF_TOKEN = re.compile(r'(?<![\w#="/-])(\[)?REF-(\d{3,4})(\])?')


def linkify_refs(html: str, refs_href: str) -> str:
    """HTML 문자열의 인용 토큰을 참고문헌 페이지 앵커로 치환.

    bracket 유무 보존: [REF-004]→[REF-004], REF-004→REF-004.
    """
    def repl(m: re.Match) -> str:
        lb = m.group(1) or ""
        num = m.group(2)
        rb = m.group(3) or ""
        rid = f"REF-{num}"
        visible = f"{lb}{rid}{rb}"
        return f'<a class="ref" data-ref="{rid}" href="{refs_href}#{rid}">{visible}</a>'

    return _REF_TOKEN.sub(repl, html)


# ```mermaid … ``` 펜스 블록 (변환 전 직접 추출·보호)
_MERMAID_FENCE = re.compile(r"^[ \t]*```[ \t]*mermaid[ \t]*\n(.*?)\n[ \t]*```[ \t]*$", re.M | re.S)
_MM_TOKEN = "MMDBLOCK{}MMDEND"


def _protect_mermaid(md: str) -> tuple[str, list[str]]:
    """```mermaid 블록을 placeholder 단락으로 치환하고 원본 코드를 보관."""
    codes: list[str] = []

    def repl(m: re.Match) -> str:
        codes.append(m.group(1).strip())
        return "\n" + _MM_TOKEN.format(len(codes) - 1) + "\n"

    return _MERMAID_FENCE.sub(repl, md), codes


def _restore_mermaid(html: str, codes: list[str]) -> str:
    """placeholder → <pre class="mermaid"> (코드는 HTML 이스케이프 — mermaid는 textContent 사용)."""
    for i, code in enumerate(codes):
        token = _MM_TOKEN.format(i)
        block = f'<pre class="mermaid">{_html.escape(code)}</pre>'
        html = html.replace(f"<p>{token}</p>", block).replace(token, block)
    return html


# 수식 보호 (F38) — python-markdown이 $$…$$·$…$ 내부의 _(아래첨자)·*·\\ 를
# emphasis/이스케이프로 훼손하지 않도록 변환 전 추출·보관 후 복원(MathJax가 브라우저에서 렌더).
_DISPLAY_MATH = re.compile(r"\$\$.+?\$\$", re.S)
_INLINE_MATH = re.compile(r"(?<!\\)\$(?!\$)(?:\\.|[^$\n\\])+?(?<!\\)\$(?!\$)")
_MATH_TOKEN = "MATHBLK{}MATHEND"


def _protect_math(md: str) -> tuple[str, list[str]]:
    """$$…$$(디스플레이) → $…$(인라인) 순으로 placeholder 치환, 원본 보관."""
    store: list[str] = []

    def repl(m: re.Match) -> str:
        store.append(m.group(0))
        return _MATH_TOKEN.format(len(store) - 1)

    md = _DISPLAY_MATH.sub(repl, md)  # 먼저 $$…$$ (모든 이중 $ 소비)
    md = _INLINE_MATH.sub(repl, md)  # 남은 단일 $…$
    return md, store


def _restore_math(html: str, store: list[str]) -> str:
    """placeholder → 원본 수식(그대로). 디스플레이는 <p>token</p>도 복원."""
    for i, raw in enumerate(store):
        token = _MATH_TOKEN.format(i)
        html = html.replace(f"<p>{token}</p>", raw).replace(token, raw)
    return html


def _wrap_tables(html: str) -> str:
    """<table>을 가로 스크롤 래퍼로 감싼다 (모바일 오버플로 방지)."""
    return html.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )


def _extract_h2_toc(md_obj: markdown.Markdown) -> list[tuple[str, str]]:
    """toc 확장이 만든 toc_tokens에서 level-2 헤딩만 (id, name)로 평탄화."""
    toc: list[tuple[str, str]] = []
    for tok in getattr(md_obj, "toc_tokens", []) or []:
        _walk_toc(tok, toc)
    return toc


def _walk_toc(tok: dict, acc: list[tuple[str, str]]) -> None:
    if tok.get("level") == 2:
        acc.append((tok.get("id", ""), tok.get("name", "")))
    for ch in tok.get("children", []) or []:
        _walk_toc(ch, acc)


def md_to_html(md: str, refs_href: str = "") -> tuple[str, list[tuple[str, str]]]:
    """markdown → (html_body, h2_toc).

    refs_href: 페이지에서 참고문헌 페이지까지의 상대 경로
               (예: '../참고문헌/index.html').
    """
    protected, mm_codes = _protect_mermaid(md or "")
    protected, math_store = _protect_math(protected)
    md_obj = markdown.Markdown(
        extensions=["tables", "sane_lists", "attr_list", "toc", "fenced_code"],
        output_format="html5",
    )
    html = md_obj.convert(protected)
    if refs_href:
        html = linkify_refs(html, refs_href)
    html = _restore_math(html, math_store)
    html = _restore_mermaid(html, mm_codes)
    html = _wrap_tables(html)
    toc = _extract_h2_toc(md_obj)
    return html, toc
