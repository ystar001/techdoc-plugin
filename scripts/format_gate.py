"""서식 게이트 — self_model 카드 본문 markdown 형식 품질 측정 (LLM 0회·결정론적).

v1.11-c: 측정 코드는 `techdoc_core.qc.legacy.format_metrics`로 옮겼다 — qc 게이트 PLG-FG-*가
같은 함수를 쓴다. 이 모듈은 기존 공개 이름(`measure_format` 반환 `{"metrics","issues"}` 등)을
그대로 다시 내보내는 래퍼다.
"""

from __future__ import annotations

from techdoc_core.qc.legacy.format_metrics import (
    _MERMAID_SPECIAL,
    CONTROL_CHARS,
    INLINE_ALPHA,
    INLINE_ROMAN,
    LIST_LINE,
    MERMAID_BLOCK,
    NONBULLET_INDENT,
    NUM_RE,
    REDUNDANT_SUMMARY,
    REF_RE,
    STRICT_FAIL_METRICS,
    TOP_PLAIN,
    analyze_lists,
    count_control_chars,
    count_inline_enumeration,
    count_inline_hierarchy,
    count_mermaid_label_risk,
    count_nonbullet_indent,
    count_redundant_summary,
    count_top_plain,
    count_visual_elements,
    list_ratio_by_section,
    measure_format,
    nums,
    refs,
    render_nesting,
)

__all__ = [
    "CONTROL_CHARS", "INLINE_ALPHA", "INLINE_ROMAN", "LIST_LINE", "MERMAID_BLOCK",
    "NONBULLET_INDENT", "NUM_RE", "REDUNDANT_SUMMARY", "REF_RE", "STRICT_FAIL_METRICS",
    "TOP_PLAIN", "_MERMAID_SPECIAL", "analyze_lists", "count_control_chars",
    "count_inline_enumeration", "count_inline_hierarchy", "count_mermaid_label_risk",
    "count_nonbullet_indent", "count_redundant_summary", "count_top_plain",
    "count_visual_elements", "list_ratio_by_section", "measure_format", "nums", "refs",
    "render_nesting",
]
