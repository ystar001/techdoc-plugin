"""Sources/REF-*.md 빌더.

reference_list.json의 한 항목 + KeyRef/<file>.md 원문 요약 → Sources/<ref_id>_<title>.md.
"""

from __future__ import annotations

from pathlib import Path

from scripts.wiki.filename import sanitize_name
from scripts.wiki.frontmatter import serialize_frontmatter, parse_frontmatter, split_page
from scripts.wiki.markers import replace_ai_region


def source_filename(reference: dict) -> str:
    """REF-XXX_<title 첫 30자>.md."""
    ref_id = reference.get("id", "REF-000")
    title_short = (reference.get("title") or "untitled")[:30]
    return f"{ref_id}_{sanitize_name(title_short)}.md"


def build_source_page(
    reference: dict,
    keyref_dir: Path,
    existing_page: str | None,
) -> str:
    """소스 페이지 생성·갱신. 기존 페이지의 사용자 메모 보존.

    Args:
        reference: reference_list.json의 한 항목 (REF dict).
        keyref_dir: KeyRef/ 디렉토리. 본문 KeyRef 원문 요약 로드용.
        existing_page: 이미 vault에 있는 페이지 텍스트. None이면 신규.
    """
    fm: dict = {
        "type": "source",
        "ref_id": reference.get("id", ""),
        "title": reference.get("title", ""),
        "authors": [reference.get("source", "")],
        "year": reference.get("year", 0),
        "url": reference.get("url", ""),
        "category": reference.get("category", ""),
        "trust": "confirmed" if reference.get("reliability") == "확인됨" else "single",
        "techdoc_auto": True,
    }

    # KeyRef 원문 요약 로드
    keyref_file = reference.get("file", "")
    keyref_text = ""
    if keyref_file:
        kr_path = keyref_dir.parent / keyref_file if "/" in keyref_file else keyref_dir / Path(keyref_file).name
        if kr_path.exists():
            keyref_text = kr_path.read_text(encoding="utf-8")

    ai_body = (
        f"## KeyRef 요약\n\n{keyref_text}\n" if keyref_text
        else "## KeyRef 요약\n\n(KeyRef 파일을 찾을 수 없습니다.)\n"
    )

    if existing_page is None:
        page = split_page(fm, "")
        return replace_ai_region(page, ai_body)

    # 기존 페이지: frontmatter는 새 fm으로 갱신, 외부 메모 + 마커 영역만 치환
    _, body = parse_frontmatter(existing_page)
    page = split_page(fm, body)
    return replace_ai_region(page, ai_body)
