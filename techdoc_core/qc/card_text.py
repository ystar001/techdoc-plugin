"""카드에서 렌더에 실리는 글을 꺼낸다 — 시리즈 build_revision_spec의 두 헬퍼를 옮김 (v1.11).

원본 모듈은 openpyxl·시리즈 경로 상수가 딸려 와서 통째로 가져오지 않는다. 카드 스키마
네 변형(sections dict·blocks dict·blocks list, 본문 키 body·content·narrative)을 받는다.
"""
from __future__ import annotations

# blocks가 dict인 카드에서 본문이 아닌 메타 키
BLOCKS_META_KEYS = frozenset({
    "document_guide", "doc_guide", "guide", "document_anchor",
    "meta", "meta_info", "header", "preface", "overview_anchor",
    "self_check", "self_check_meta", "writing_meta", "section_guide", "cross_references",
})


def _s(v) -> str:
    """글이 아닌 값(숫자·None·목록)이 섞인 카드 하나가 게이트를 문서 전체에서 죽이지 않게 글로."""
    if v is None:
        return ""
    return v if isinstance(v, str) else str(v)


def sections_of(card: dict) -> list[tuple[str, str, str]]:
    """(섹션 키, 표제, 본문) 목록 — 표제·본문은 늘 str(타입이 어긋난 값은 글로 바꾼다)."""
    out: list[tuple[str, str, str]] = []
    secs = card.get("sections")
    if not isinstance(secs, dict) and isinstance(card.get("blocks"), dict):
        secs = {k: v for k, v in card["blocks"].items() if k not in BLOCKS_META_KEYS}
    if isinstance(secs, dict):
        for k, v in secs.items():
            if isinstance(v, dict):
                title = v.get("title") or v.get("heading") or ""
                body = v.get("body") or v.get("content") or v.get("narrative") or ""
                if not body:
                    body = "\n\n".join(x for kk, x in v.items()
                                       if kk not in ("title", "heading") and isinstance(x, str))
                out.append((_s(k), _s(title), _s(body)))
            else:
                out.append((_s(k), "", str(v)))  # 원본 그대로(None → "None")
    elif isinstance(card.get("blocks"), list):
        for i, b in enumerate(card["blocks"], 1):
            if isinstance(b, dict):
                out.append((_s(b.get("block_id", f"blk{i}")), _s(b.get("title", "")),
                            _s(b.get("body", "") or b.get("content", "") or b.get("text", ""))))
    return out


def card_level_fields(card: dict) -> list[tuple[str, str, str]]:
    """섹션 밖이지만 렌더에 실리는 필드 — quick_summary·section_overview·scope_note."""
    out: list[tuple[str, str, str]] = []
    qs = card.get("quick_summary")
    if isinstance(qs, dict):
        vals: list[str] = []
        for v in qs.values():
            if isinstance(v, str):
                vals.append(v)
            elif isinstance(v, list):
                vals += [str(x) for x in v if isinstance(x, str)]
        txt = "\n".join(vals)
        if txt.strip():
            out.append(("quick_summary", "[핵심요약]", txt))
    elif isinstance(qs, str) and qs.strip():
        out.append(("quick_summary", "[핵심요약]", qs))
    so = card.get("section_overview")
    if isinstance(so, str) and so.strip():
        out.append(("section_overview", "[절 개요]", so))
    sn = card.get("scope_note")
    if isinstance(sn, str) and sn.strip():
        out.append(("scope_note", "[범위 메모]", sn))
    return out


def card_texts(card: dict) -> list[tuple[str, str, str]]:
    """게이트가 보는 카드 글 전부 = 카드 수준 필드 + 섹션 (원본 check_v2.texts와 같은 순서)."""
    return card_level_fields(card) + sections_of(card)
