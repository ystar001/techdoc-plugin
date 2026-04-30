"""index.md 빌더 — vault의 카테고리별 카탈로그 자동 생성."""

from __future__ import annotations

from pathlib import Path

from scripts.wiki.markers import replace_ai_region


def build_index(vault_dir: Path, existing_index: str | None) -> str:
    categories = ["Sources", "Tech", "Projects", "Products", "Concepts", "Reports"]
    parts = ["# Wiki Index\n"]
    for cat in categories:
        cat_dir = vault_dir / cat
        if not cat_dir.exists():
            continue
        pages = sorted([p for p in cat_dir.iterdir() if p.is_file() and p.suffix == ".md"])
        if not pages:
            continue
        parts.append(f"## {cat}\n")
        for p in pages:
            # 표준 마크다운 링크: index.md는 vault root, 카테고리 페이지는 vault/<cat>/<file>
            parts.append(f"- [{p.stem}]({cat}/{p.name})")
        parts.append("")
    ai_body = "\n".join(parts) + "\n"
    base = existing_index if existing_index else "# Wiki Index\n"
    return replace_ai_region(base, ai_body)
