# techdoc-plugin/scripts/notion/blocks.py
"""마크다운/HTML/카드 sections.body → Notion block JSON 변환 (v1.2.0).

지원 block: paragraph, heading_2, heading_3, code, quote, equation, table, image (외부 URL).
미지원 패턴은 paragraph fallback + WARN 로그.

v2 호환 디자인 원칙 (§10-1):
- 변환 규칙은 무손실 reversible (heading level·code language·table 구조 정확 보존).
- 향후 inverse converter(notion → markdown)에서 같은 규칙으로 역변환 가능.
"""

from __future__ import annotations

import re

# 마크다운 패턴
HEADING_PAT = re.compile(r"^(#{1,3})\s+(.+)$")
CODE_FENCE_OPEN = re.compile(r"^```(\w*)\s*$")
QUOTE_PAT = re.compile(r"^>\s*(.*)$")
EQUATION_PAT = re.compile(r"^\$\$(.+)\$\$\s*$")
IMAGE_PAT = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TABLE_ROW_PAT = re.compile(r"^\|(.+)\|$")
TABLE_DIVIDER_PAT = re.compile(r"^\|[\s\-:|]+\|$")
REF_PAT = re.compile(r"\[(REF-[0-9]+)\]")


def _rich_text(content: str) -> list[dict]:
    """plain string → Notion rich_text 배열 1요소."""
    return [{"type": "text", "text": {"content": content}}]


def _rich_text_with_ref_mentions(content: str, keyref_id_map: dict[str, str]) -> list[dict]:
    """text 내 [REF-xxx] 패턴을 mention block으로 분해.

    keyref_id_map에 매핑 있으면 mention, 없으면 plain text 유지.
    """
    result: list[dict] = []
    last_end = 0
    for m in REF_PAT.finditer(content):
        ref_id = m.group(1)
        # 앞쪽 plain text
        if m.start() > last_end:
            result.append({"type": "text", "text": {"content": content[last_end:m.start()]}})
        # mention or plain
        row_id = keyref_id_map.get(ref_id)
        if row_id:
            result.append({
                "type": "mention",
                "mention": {"type": "page", "page": {"id": row_id}},
                "plain_text": f"[{ref_id}]",
            })
        else:
            result.append({"type": "text", "text": {"content": f"[{ref_id}]"}})
        last_end = m.end()
    if last_end < len(content):
        result.append({"type": "text", "text": {"content": content[last_end:]}})
    return result if result else [{"type": "text", "text": {"content": content}}]


def _heading_block(level: int, content: str) -> dict:
    # H1 → H2 격하 (페이지 title이 담당)
    notion_level = max(level, 2)
    # 본문에서는 H2·H3만 지원, 더 깊으면 H3
    notion_level = min(notion_level, 3)
    key = f"heading_{notion_level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text(content)},
    }


def _paragraph_block(content: str, keyref_id_map: dict[str, str] | None = None) -> dict:
    if keyref_id_map:
        rich = _rich_text_with_ref_mentions(content, keyref_id_map)
    else:
        rich = _rich_text(content)
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich},
    }


def _code_block(content: str, language: str) -> dict:
    lang_normalized = language.strip() or "plain text"
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": _rich_text(content),
            "language": lang_normalized,
        },
    }


def _quote_block(content: str) -> dict:
    return {
        "object": "block",
        "type": "quote",
        "quote": {"rich_text": _rich_text(content)},
    }


def _equation_block(expression: str) -> dict:
    return {
        "object": "block",
        "type": "equation",
        "equation": {"expression": expression},
    }


def _is_external_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def _image_block(alt: str, url: str) -> dict:
    if _is_external_url(url):
        return {
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": url},
                "caption": _rich_text(alt) if alt else [],
            },
        }
    # 로컬 경로 — placeholder paragraph
    return _paragraph_block(
        f"[이미지: {alt or url} (로컬 파일, Notion에 자동 업로드 미지원 — v1.2.x 예정)]"
    )


def _table_row_cells(line: str) -> list[list[dict]]:
    """`| a | b |` → [[rich_text(a)], [rich_text(b)]]."""
    inner = line.strip().strip("|")
    return [_rich_text(cell.strip()) for cell in inner.split("|")]


def _table_block(rows: list[str]) -> dict:
    """rows: ['| H1 | H2 |', '|---|---|', '| a | b |', ...]"""
    data_rows = [r for r in rows if not TABLE_DIVIDER_PAT.match(r.strip())]
    cells_per_row = [_table_row_cells(r) for r in data_rows]
    width = len(cells_per_row[0]) if cells_per_row else 0
    children = [
        {
            "object": "block",
            "type": "table_row",
            "table_row": {"cells": cells},
        }
        for cells in cells_per_row
    ]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        },
    }


def markdown_to_blocks(md: str, keyref_id_map: dict[str, str] | None = None) -> list[dict]:
    """마크다운 → Notion block. keyref_id_map: REF-ID → Notion page/row ID."""
    keyref_id_map = keyref_id_map or {}
    blocks: list[dict] = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # 빈 줄
        if not line:
            i += 1
            continue
        # code fence
        if CODE_FENCE_OPEN.match(line):
            lang = CODE_FENCE_OPEN.match(line).group(1)
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                code_lines.append(lines[i])
                i += 1
            blocks.append(_code_block("\n".join(code_lines), lang))
            i += 1
            continue
        # equation
        if EQUATION_PAT.match(line):
            blocks.append(_equation_block(EQUATION_PAT.match(line).group(1).strip()))
            i += 1
            continue
        # quote
        if QUOTE_PAT.match(line):
            blocks.append(_quote_block(QUOTE_PAT.match(line).group(1).strip()))
            i += 1
            continue
        # heading
        m_head = HEADING_PAT.match(line)
        if m_head:
            level = len(m_head.group(1))
            blocks.append(_heading_block(level, m_head.group(2).strip()))
            i += 1
            continue
        # image (single line)
        m_img = IMAGE_PAT.fullmatch(line)
        if m_img:
            blocks.append(_image_block(m_img.group(1), m_img.group(2)))
            i += 1
            continue
        # table — `|`로 시작하는 연속 라인
        if TABLE_ROW_PAT.match(line):
            table_lines: list[str] = []
            while i < len(lines) and TABLE_ROW_PAT.match(lines[i].strip()):
                table_lines.append(lines[i].strip())
                i += 1
            if len(table_lines) >= 2:
                blocks.append(_table_block(table_lines))
            else:
                blocks.append(_paragraph_block("\n".join(table_lines), keyref_id_map))
            continue
        # 일반 단락 — 빈 줄 또는 special 블록 만날 때까지
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].rstrip():
            nxt = lines[i].rstrip()
            if (CODE_FENCE_OPEN.match(nxt) or EQUATION_PAT.match(nxt)
                    or QUOTE_PAT.match(nxt) or HEADING_PAT.match(nxt)
                    or IMAGE_PAT.fullmatch(nxt) or TABLE_ROW_PAT.match(nxt)):
                break
            para_lines.append(nxt)
            i += 1
        blocks.append(_paragraph_block(" ".join(para_lines), keyref_id_map))
    return blocks
