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

import json
import re
from pathlib import Path

from techdoc_core.renderers.paragraph import format_paragraphs
from techdoc_core.renderers.section_heading import section_key_to_heading
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


# ── 카드 로드·본문 추출 ──────────────────────────────────────────
def load_card(source: Path | dict) -> dict:
    """카드 source(파일 경로 또는 이미 로드된 dict) → dict."""
    if isinstance(source, dict):
        return source
    return json.loads(Path(source).read_text(encoding="utf-8"))


def card_sections_or_blocks(card: dict):
    """카드 본문 단위 (key, value) iterable. sections 우선·blocks fallback.

    self-model 0.2.0은 `sections[*]`, 일부 카드는 `blocks` 키를 쓴다.
    blocks의 메타 키(document_guide 등)는 본문에서 제외한다.
    """
    sections = card.get("sections")
    if isinstance(sections, dict) and sections:
        yield from sections.items()
        return
    blocks = card.get("blocks")
    if isinstance(blocks, dict) and blocks:
        for k, v in blocks.items():
            if k in _BLOCKS_META_KEYS:
                continue
            yield k, v
        return


def _extract_section(value) -> tuple[str, str]:
    """sections[key] 값 → (title, body)."""
    if isinstance(value, str):
        return "", value
    if isinstance(value, dict):
        title = value.get("title", "")
        body = value.get("body", "")
        if not body:
            parts = [v for k, v in value.items() if k != "title" and isinstance(v, str)]
            body = "\n\n".join(parts)
        return title, body
    return "", str(value)


def _card_title(card: dict, card_id: str) -> str:
    """카드 표시 제목 — card 'title'/'name' 우선, 없으면 card_id."""
    return (card.get("title") or card.get("name") or card_id or "").strip()


# ── 카드 → markdown 렌더링 ──────────────────────────────────────
def render_card_md(card: dict, heading_level: int = 1, card_id: str | None = None) -> str:
    """단일 카드 → markdown. 각 .md는 `# <card_id> — <title>` 으로 시작.

    섹션 키는 section_key_to_heading(F12)로 한글 헤딩, body는
    format_paragraphs(F10)로 단락 정리한다.
    """
    cid = (card_id or card_id_of(card) or "?").strip()
    title = _card_title(card, cid)
    h1 = "#" * heading_level
    h2 = "#" * (heading_level + 1)

    out = [f"{h1} {cid} — {title}".rstrip(" —"), ""]
    for key, val in card_sections_or_blocks(card):
        sec_title, body = _extract_section(val)
        formatted = format_paragraphs((body or "").strip())
        if not formatted.strip():
            continue
        out.append(f"{h2} {section_key_to_heading(key, sec_title)}")
        out.append("")
        out.append(formatted)
        out.append("")

    refs = _ref_ids(card)
    if refs:
        out.append(f"**인용 참고문헌 ({len(refs)}건).** {', '.join(refs)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_merged_md(parent_id: str, cards: list[dict | Path], heading_level: int = 1) -> str:
    """여러 split 카드(L1·L2·L3 …)를 한 .md로 병합.

    부모 제목은 첫 카드 title을 _clean_parent_title로 정리(분할 미주 제거).
    섹션 헤딩은 누적 sequential 번호(1, 2, …)로 재부여하고, 참고문헌은 통합한다.
    """
    h1 = "#" * heading_level
    h2 = "#" * (heading_level + 1)

    first = load_card(cards[0])
    parent_title = _clean_parent_title(_card_title(first, parent_id))
    out = [f"{h1} {parent_id} — {parent_title}".rstrip(" —"), ""]

    sec_counter = 0
    all_refs: list[str] = []
    for c in cards:
        card = load_card(c)
        for key, val in card_sections_or_blocks(card):
            sec_title, body = _extract_section(val)
            formatted = format_paragraphs((body or "").strip())
            if not formatted.strip():
                continue
            heading = section_key_to_heading(key, sec_title)
            heading_body = re.sub(r"^\d+\.\s*", "", heading)
            sec_counter += 1
            out.append(f"{h2} {sec_counter}. {heading_body}")
            out.append("")
            out.append(formatted)
            out.append("")
        all_refs.extend(_ref_ids(card))

    unique_refs = sorted(set(all_refs))
    if unique_refs:
        out.append(f"**인용 참고문헌 ({len(unique_refs)}건).** {', '.join(unique_refs)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _ref_ids(card: dict) -> list[str]:
    """카드의 references_used/refs_used → ref id 문자열 리스트."""
    refs = card.get("references_used") or card.get("refs_used") or []
    out: list[str] = []
    for r in refs:
        if isinstance(r, str):
            out.append(r)
        elif isinstance(r, dict):
            rid = r.get("id") or r.get("ref_id")
            if rid:
                out.append(rid)
    return out
