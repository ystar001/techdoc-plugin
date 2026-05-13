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


def test_table_block_simple():
    from scripts.notion.blocks import markdown_to_blocks

    md = "| H1 | H2 |\n|---|---|\n| a | b |\n| c | d |"
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "table"
    tbl = blocks[0]["table"]
    assert tbl["table_width"] == 2
    assert tbl["has_column_header"] is True
    rows = tbl["children"]
    assert len(rows) == 3  # header + 2 data rows
    assert rows[0]["table_row"]["cells"][0][0]["text"]["content"] == "H1"


def test_image_block_external_url():
    from scripts.notion.blocks import markdown_to_blocks

    md = "![설명](https://example.com/x.png)"
    blocks = markdown_to_blocks(md)
    assert blocks[0]["type"] == "image"
    assert blocks[0]["image"]["external"]["url"] == "https://example.com/x.png"


def test_image_local_path_becomes_placeholder():
    """로컬 경로 이미지는 paragraph + WARN으로 fallback (v1.2.0)."""
    from scripts.notion.blocks import markdown_to_blocks

    md = "![차트](./figures/chart.png)"
    blocks = markdown_to_blocks(md)
    assert blocks[0]["type"] == "paragraph"
    text = blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
    assert "차트" in text or "chart.png" in text


def test_ref_mention_when_keyref_id_known():
    """[REF-023]이 본문에 있고 keyref_id_map에 매핑이 있으면 mention block."""
    from scripts.notion.blocks import markdown_to_blocks

    keyref_id_map = {"REF-023": "notion-row-id-xyz"}
    md = "이 기술의 정확도는 94.3% [REF-023]에 따르면."
    blocks = markdown_to_blocks(md, keyref_id_map=keyref_id_map)
    para = blocks[0]
    assert para["type"] == "paragraph"
    rich = para["paragraph"]["rich_text"]
    # rich_text는 여러 요소로 분리됨: text + mention + text
    mention_items = [r for r in rich if r.get("type") == "mention"]
    assert len(mention_items) == 1
    assert mention_items[0]["mention"]["page"]["id"] == "notion-row-id-xyz"


def test_ref_mention_falls_back_to_plain_text():
    """매핑 없으면 [REF-023]을 plain text로 유지."""
    from scripts.notion.blocks import markdown_to_blocks

    blocks = markdown_to_blocks("내용 [REF-099].", keyref_id_map={})
    rich = blocks[0]["paragraph"]["rich_text"]
    full_text = "".join(r.get("text", {}).get("content", "") for r in rich if r.get("type") == "text")
    assert "[REF-099]" in full_text


def test_block_conversion_preserves_heading_level_for_reversibility():
    """v2 호환 원칙 #2: 변환 가역성. H2·H3가 명확히 구분 보존."""
    from scripts.notion.blocks import markdown_to_blocks

    h2_blocks = markdown_to_blocks("## H2 제목")
    h3_blocks = markdown_to_blocks("### H3 제목")
    assert h2_blocks[0]["type"] == "heading_2"
    assert h3_blocks[0]["type"] == "heading_3"


def test_code_language_preserved_for_reversibility():
    """v2 호환 원칙 #2: code 블록 언어 그대로 보존."""
    from scripts.notion.blocks import markdown_to_blocks

    blocks = markdown_to_blocks("```rust\nfn main() {}\n```")
    assert blocks[0]["code"]["language"] == "rust"
