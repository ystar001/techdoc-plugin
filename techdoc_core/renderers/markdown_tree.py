"""config 기반 markdown 트리 디렉토리 빌더 (F15 + F17).

카드 JSON 디렉토리를 `routing_config`(F21)로 Part/시리즈로 분류해 디렉토리 트리 +
계층 INDEX 파일을 생성한다. 단일 컨텐츠 시리즈 폴더의 INDEX는 생략한다(F17).

자식 프로젝트 `render_md.py`의 `write_tree`(~490줄)를 schema-agnostic·config-driven
으로 일반화한 것이다. 도메인 명칭(카테고리·시리즈 라벨)은 routing_config의 선택적
필드에서 받고, 없으면 card_id 기반 generic 이름으로 폴백한다.

재사용:
  - routing_config.parse_card_id (F21) — part 버킷팅
  - renderers.paragraph.format_paragraphs (F10) — 본문 단락
  - renderers.section_heading.section_key_to_heading (F12) — 섹션 헤딩

LLM 호출 0회·결정론적.
"""
from __future__ import annotations

import re
from pathlib import Path

from techdoc_core.routing_config import (
    DEFAULT_ROUTING,
    _sort_key,
    parse_card_id,
)

# split marker(L1/L2/L3·XL1~XL5) 정리 — parent_id 도출용.
_SPLIT_MARKER_RE = re.compile(r"\.(?:L|XL)\d+$")
# 분할 미주(— 분할 1/2 · (분할 2/2) · — §N ... · (L1) 등) 정리 — 부모 제목용.
_PARENT_TITLE_CLEANERS = (
    re.compile(r"\s*[—–-]\s*분할\s*\d+/\d+\s*$"),  # noqa: RUF001
    re.compile(r"\s*\(\s*분할\s*\d+/\d+\s*\)\s*$"),
    re.compile(r"\s*[—–-]\s*§\d+\s.*$"),  # noqa: RUF001
    re.compile(r"\s*[—–-]\s*[§]?\d+(?:[~∼]\s*[§]?\d+)?\s*$"),  # noqa: RUF001
    re.compile(r"\s*\(\s*[§]?\d+(?:[~∼]\s*[§]?\d+)?\s*\)\s*$"),  # noqa: RUF001
    re.compile(r"\s*\(\s*L\d+(?:,\s*\d+\s*p)?\s*\)\s*$"),
    re.compile(r"\s*\(\s*XL\d+(?:,\s*\d+\s*p)?\s*\)\s*$"),
    re.compile(r"\s*[—–-]\s*L\d+\s*$"),  # noqa: RUF001
    re.compile(r"\s*[—–-]\s*XL\d+\s*$"),  # noqa: RUF001
)
_FORBIDDEN_CHARS_RE = re.compile(r'[<>:"/\\|?*]')
_BLOCKS_META_KEYS = {
    "document_guide", "doc_guide", "guide", "document_anchor",
    "meta", "meta_info", "header", "preface", "overview_anchor",
}


# ── card_id·parent 헬퍼 ──────────────────────────────────────────
def card_id_of(source: Path | dict | str) -> str:
    """파일 경로·카드 dict·문자열에서 card_id 추출.

    파일명 `<card_id>_card.json` 또는 dict의 `card_id`/`id` 키를 사용한다.
    """
    if isinstance(source, Path):
        name = source.name
        if name.endswith("_card.json"):
            return name[: -len("_card.json")]
        return source.stem
    if isinstance(source, dict):
        return (source.get("card_id") or source.get("id") or "").strip()
    return str(source).strip()


def parent_of(card_id: str) -> str:
    """card_id → 부모 카드 ID (split marker 제거).

    예: '1.4.L2' → '1.4', '11.1.XL3' → '11.1', 'A-14.1.L1' → 'A-14.1',
        '1.1' → '1.1' (split 없음).
    """
    return _SPLIT_MARKER_RE.sub("", (card_id or "").strip())


def safe_dirname(name: str) -> str:
    """OS 안전 디렉토리/파일 이름. 한글 그대로 + Windows 금지문자 치환."""
    return _FORBIDDEN_CHARS_RE.sub("_", name or "").strip()


def _clean_parent_title(title: str) -> str:
    """split 카드 title에서 운영 메타 미주 제거 → 부모 제목."""
    if not title:
        return title
    t = title
    for rx in _PARENT_TITLE_CLEANERS:
        t = rx.sub("", t)
    return t.strip()


def bucket_cards(
    files: list[Path], config: dict = DEFAULT_ROUTING
) -> dict[str, list[Path]]:
    """카드 파일을 part_key별로 분류 (parse_card_id 재사용, F21).

    각 버킷 내부는 card_id sort_key로 정렬한다.
    """
    buckets: dict[str, list[tuple[tuple, Path]]] = {}
    for f in files:
        cid = card_id_of(f)
        part_key, sort_key = parse_card_id(cid, config)
        buckets.setdefault(part_key, []).append((sort_key, f))
    return {k: [f for _, f in sorted(v)] for k, v in buckets.items()}


def group_by_parent(files: list[Path]) -> dict[str, list[Path]]:
    """parent_id별 그룹 (split 카드 병합). 그룹 내부는 card_id sort_key 정렬.

    삽입 순서는 parent 첫 등장 순서를 보존한다.
    """
    groups: dict[str, list[tuple[tuple, Path]]] = {}
    order: list[str] = []
    for f in files:
        cid = card_id_of(f)
        pid = parent_of(cid)
        if pid not in groups:
            groups[pid] = []
            order.append(pid)
        groups[pid].append((_sort_key(cid), f))
    return {pid: [f for _, f in sorted(groups[pid])] for pid in order}
