# techdoc-plugin/tests/test_notion_blocks.py
"""Notion block 변환 회귀."""

from __future__ import annotations

import pytest


def test_paragraph_block():
    from scripts.notion.blocks import markdown_to_blocks

    blocks = markdown_to_blocks("이것은 단순한 문단입니다.")
    assert len(blocks) == 1
    b = blocks[0]
    assert b["object"] == "block"
    assert b["type"] == "paragraph"
    assert b["paragraph"]["rich_text"][0]["text"]["content"] == "이것은 단순한 문단입니다."


def test_heading_2_block():
    from scripts.notion.blocks import markdown_to_blocks

    blocks = markdown_to_blocks("## 큰 제목")
    assert blocks[0]["type"] == "heading_2"
    assert blocks[0]["heading_2"]["rich_text"][0]["text"]["content"] == "큰 제목"


def test_heading_3_block():
    from scripts.notion.blocks import markdown_to_blocks

    blocks = markdown_to_blocks("### 작은 제목")
    assert blocks[0]["type"] == "heading_3"


def test_h1_is_demoted_to_h2():
    """H1는 페이지 title이 담당 — body에서는 H2로 격하."""
    from scripts.notion.blocks import markdown_to_blocks

    blocks = markdown_to_blocks("# 본문 제목")
    assert blocks[0]["type"] == "heading_2"


def test_multiple_paragraphs():
    from scripts.notion.blocks import markdown_to_blocks

    md = "첫 단락.\n\n둘째 단락."
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 2
    assert all(b["type"] == "paragraph" for b in blocks)


def test_code_block_with_language():
    from scripts.notion.blocks import markdown_to_blocks

    md = "```python\ndef hello():\n    pass\n```"
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "python"
    assert "def hello" in blocks[0]["code"]["rich_text"][0]["text"]["content"]


def test_code_block_without_language_defaults_to_plain():
    from scripts.notion.blocks import markdown_to_blocks

    md = "```\nplain text code\n```"
    blocks = markdown_to_blocks(md)
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] in ("plain text", "plain_text", "plaintext")


def test_quote_block():
    from scripts.notion.blocks import markdown_to_blocks

    md = "> 이것은 인용문입니다."
    blocks = markdown_to_blocks(md)
    assert blocks[0]["type"] == "quote"
    assert blocks[0]["quote"]["rich_text"][0]["text"]["content"] == "이것은 인용문입니다."


def test_equation_block_dollar_dollar():
    from scripts.notion.blocks import markdown_to_blocks

    md = "$$E = mc^2$$"
    blocks = markdown_to_blocks(md)
    assert blocks[0]["type"] == "equation"
    assert blocks[0]["equation"]["expression"] == "E = mc^2"
