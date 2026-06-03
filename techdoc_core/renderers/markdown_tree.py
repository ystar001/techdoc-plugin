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


# ── 파일명·시리즈 키 ────────────────────────────────────────────
def make_filename(card_id: str, title: str, max_title_len: int = 80) -> str:
    """카드 식별자 + 제목 → 안전한 파일명 (확장자 제외).

    예) '1.1', '노지 용수·관개' → '1.1. 노지 용수·관개'.
    title이 길면 ' (' · ' — ' 앞에서 자르거나 max_title_len에서 절단한다.
    """
    if not title:
        return card_id
    short = title
    for sep in (" (", " — "):
        if sep in short:
            head = short.split(sep, 1)[0].strip()
            if 4 <= len(head) <= max_title_len:
                short = head
                break
    if len(short) > max_title_len:
        short = short[:max_title_len].rstrip() + "…"
    short = safe_dirname(short).rstrip(".")
    return f"{card_id}. {short}"


def series_key_of(card_id: str, depth: int = 1) -> str:
    """card_id → 시리즈 그룹 키.

    숫자 컴포넌트 앞 `depth`개 + (있으면) 영문 prefix로 시리즈를 구성한다.
    예: depth=1 → '1.1'·'1.2' → '1', depth=2 → 'A-1.4.L1' → 'A-1.4'.
    숫자가 없으면(예: 'A-1') prefix 전체를 키로 사용한다.
    """
    cid = parent_of(card_id.strip())
    m = re.match(r"^([A-Za-z]+-?)?(.*)$", cid)
    prefix = m.group(1) or ""
    rest = m.group(2) or ""
    nums = re.findall(r"\d+", rest)
    if not nums:
        return cid
    head = ".".join(nums[:depth])
    return f"{prefix}{head}" if prefix else head


# ── 트리 빌더 (F15 + F17) ────────────────────────────────────────
class MarkdownTreeExporter:
    """카드 JSON 디렉토리 → Part/시리즈 트리 + 계층 INDEX (F15 + F17).

    routing_config(F21)로 part 버킷팅, split 카드는 parent_id로 병합한다.
    도메인 명칭은 routing_config의 선택적 필드(part rule의 `label`,
    `series_labels`, `series_depth`)에서 받고, 없으면 part_key/card_id 기반
    generic 이름으로 폴백한다.
    """

    def __init__(self, routing_config: dict = DEFAULT_ROUTING) -> None:
        self.config = routing_config

    def _rule_for(self, part_key: str) -> dict:
        for rule in self.config.get("parts", []):
            if rule.get("key") == part_key:
                return rule
        return {}

    def _part_dir_name(self, part_key: str) -> str:
        rule = self._rule_for(part_key)
        return safe_dirname(rule.get("dir") or f"Part-{part_key}")

    def _part_label(self, part_key: str) -> str:
        rule = self._rule_for(part_key)
        return rule.get("label") or part_key

    def _series_label(self, part_key: str, skey: str) -> str:
        """시리즈 라벨 — config series_labels 매핑 우선, 없으면 skey 그대로."""
        rule = self._rule_for(part_key)
        labels = rule.get("series_labels") or {}
        hint = labels.get(skey)
        return f"{skey} {hint}" if hint else skey

    def _series_depth(self, part_key: str) -> int:
        return int(self._rule_for(part_key).get("series_depth", 1))

    def export(
        self, cards_dir: Path | str, output_dir: Path | str,
        emit_series_index: bool = False,
    ) -> dict:
        """cards_dir의 `*_card.json` → output_dir 트리. 통계 dict 반환."""
        cards_dir = Path(cards_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(cards_dir.glob("*_card.json"))
        buckets = bucket_cards(files, self.config)

        stats: dict[str, int] = {}
        # part_key -> [(skey, series_label, dirname|None, entries)]
        tree: dict[str, list[tuple]] = {}

        for part_key in self._ordered_parts(buckets):
            part_dir = output_dir / self._part_dir_name(part_key)
            part_dir.mkdir(exist_ok=True)
            depth = self._series_depth(part_key)

            # 시리즈별 그룹 (삽입 순서 보존)
            series: dict[str, list[Path]] = {}
            for f in buckets[part_key]:
                skey = series_key_of(card_id_of(f), depth)
                series.setdefault(skey, []).append(f)

            part_entries: list[tuple] = []
            count = 0
            for skey, sfiles in series.items():
                label = self._series_label(part_key, skey)
                s_dir = part_dir / safe_dirname(label)
                s_dir.mkdir(exist_ok=True)
                entries = self._emit_series(s_dir, sfiles)
                count += len(entries)
                # F17: 시리즈 폴더 INDEX는 2+ 컨텐츠 파일일 때만
                if emit_series_index and len(entries) > 1:
                    self._write_series_index(s_dir, label, entries)
                part_entries.append((skey, label, s_dir.name, entries))

            stats[part_key] = count
            self._write_part_index(part_dir, self._part_label(part_key), part_entries)
            tree[part_key] = part_entries

        self._write_cover_index(output_dir, stats, tree)
        return stats

    def _ordered_parts(self, buckets: dict[str, list[Path]]) -> list[str]:
        """config part 순서 우선, 나머지(misc 등)는 뒤에 알파벳 순."""
        ordered = [r["key"] for r in self.config.get("parts", []) if r.get("key") in buckets]
        rest = sorted(k for k in buckets if k not in ordered)
        return ordered + rest

    def _emit_series(self, s_dir: Path, sfiles: list[Path]) -> list[tuple]:
        """시리즈 폴더에 부모당 1파일 생성 → entries [(pid, title, fname)]."""
        entries: list[tuple] = []
        for pid, group in group_by_parent(sfiles).items():
            if len(group) == 1:
                card = load_card(group[0])
                title = _card_title(card, pid)
                md = render_card_md(card, heading_level=1, card_id=pid)
            else:
                cards = [load_card(g) for g in group]
                title = _clean_parent_title(_card_title(cards[0], pid))
                md = render_merged_md(pid, cards, heading_level=1)
            fname = make_filename(pid, title) + ".md"
            (s_dir / fname).write_text(md, encoding="utf-8")
            entries.append((pid, title, fname))
        return entries

    @staticmethod
    def _write_series_index(s_dir: Path, label: str, entries: list[tuple]) -> None:
        lines = [f"# {label}", "", "| 카드 | 제목 |", "|---|---|"]
        for pid, title, fname in entries:
            lines.append(f"| [{pid}]({fname}) | {title} |")
        (s_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _write_part_index(part_dir: Path, label: str, part_entries: list[tuple]) -> None:
        lines = [f"# {label}", ""]
        for _skey, slabel, dirname, entries in part_entries:
            lines.append(f"## {slabel} · {len(entries)} 문서")
            lines.append("")
            for pid, title, fname in entries:
                lines.append(f"- [{pid} — {title}]({dirname}/{fname})")
            lines.append("")
        (part_dir / "INDEX.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _write_cover_index(
        self, output_dir: Path, stats: dict[str, int], tree: dict[str, list[tuple]]
    ) -> None:
        from datetime import date

        total_files = sum(stats.values())
        cover = [
            "# 보고서 트리",
            "",
            "| 항목 | 값 |",
            "|---|---|",
            f"| 발행일 | {date.today().isoformat()} |",
            f"| 총 산출 문서 | **{total_files}건** |",
        ]
        for part_key, entries in tree.items():
            cover.append(f"| {self._part_label(part_key)} | {len(entries)} 시리즈 |")
        cover += ["| 형식 | Markdown · 트리 구조 |", "", "---", "", "# 목차", ""]

        for part_key, part_entries in tree.items():
            part_dirname = self._part_dir_name(part_key)
            cover.append(f"## {self._part_label(part_key)}")
            cover.append("")
            for _skey, slabel, dirname, entries in part_entries:
                cover.append(f"- **{slabel}**")
                for pid, title, fname in entries:
                    cover.append(f"  - [{pid} — {title}]({part_dirname}/{dirname}/{fname})")
            cover.append("")
        (output_dir / "INDEX.md").write_text("\n".join(cover).rstrip() + "\n", encoding="utf-8")
