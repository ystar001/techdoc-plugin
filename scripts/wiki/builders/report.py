"""Reports/<title>.md 빌더 — 보고서 MOC (Map of Content)."""

from __future__ import annotations

from scripts.wiki.filename import sanitize_name
from scripts.wiki.frontmatter import parse_frontmatter, split_page
from scripts.wiki.markers import replace_ai_region


def build_report_moc(document: dict, existing_page: str | None) -> str:
    title = document.get("title", "untitled")
    metadata = document.get("metadata", {})

    fm = {
        "type": "report",
        "title": title,
        "domain": metadata.get("domain", ""),
        "generated": metadata.get("date", ""),
        "techdoc_version": metadata.get("techdoc_version", ""),
        "sections": len(document.get("sections", [])),
        "techdoc_auto": True,
    }

    parts = [f"# {title} — MOC\n"]
    parts.append("## 기술 카드\n")
    for c in document.get("tech_cards", []):
        name = c.get("name", "")
        safe = sanitize_name(name)
        parts.append(f"- [{name}](../Tech/{safe}.md) — 중요도 {c.get('importance', '?')}")
    parts.append("\n## 연구·프로젝트 카드\n")
    for c in document.get("project_cards", []):
        name = c.get("name", "")
        safe = sanitize_name(name)
        parts.append(f"- [{name}](../Projects/{safe}.md)")
    parts.append("\n## 제품 카드\n")
    for c in document.get("product_cards", []):
        name = c.get("name", "")
        safe = sanitize_name(name)
        parts.append(f"- [{name}](../Products/{safe}.md)")
    parts.append("\n## 별첨\n")
    for a in document.get("tech_appendices", []):
        a_name = a.get("name", "")
        parts.append(f"- {a_name} (별첨)")
    for a in document.get("project_appendices", []):
        a_name = a.get("name", "")
        parts.append(f"- {a_name} (별첨)")

    ai_body = "\n".join(parts) + "\n"
    if existing_page is None:
        return replace_ai_region(split_page(fm, ""), ai_body)
    _, body = parse_frontmatter(existing_page)
    return replace_ai_region(split_page(fm, body), ai_body)
