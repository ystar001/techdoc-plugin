"""vault lint — 충돌 마커·끊어진 링크·고아 페이지 점검.

D 하이브리드: 본문 표준 마크다운 링크와 frontmatter wiki-style 링크 모두 검출.
"""

from __future__ import annotations

import re
from pathlib import Path

# 표준 마크다운 링크 (D 하이브리드 본문)
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")
# Wiki-style 링크 (frontmatter 또는 옵시디언 잔존)
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def lint_vault(vault: Path) -> dict:
    """vault 점검 결과를 dict로 반환 + _lint_report.md 작성."""
    issues: list[str] = []
    page_paths: dict[str, Path] = {}
    for md in vault.rglob("*.md"):
        rel = md.relative_to(vault).with_suffix("").as_posix()
        page_paths[rel] = md

    for rel, p in page_paths.items():
        text = p.read_text(encoding="utf-8")
        # 1. 충돌 마커 잔존
        if "정보 충돌 감지" in text:
            issues.append(f"[CONFLICT] {rel}: 충돌 callout 잔존")

        # 2. 끊어진 표준 마크다운 링크
        for _, target in _MD_LINK.findall(text):
            if target.startswith("http") or "Assets/" in target:
                continue
            target_rel = target.replace("../", "").replace(".md", "")
            if target_rel not in page_paths:
                issues.append(f"[BROKEN-LINK] {rel} → {target}")

        # 3. 끊어진 wiki-style 링크
        for link in _WIKILINK.findall(text):
            if link not in page_paths and not link.startswith("Assets/"):
                issues.append(f"[BROKEN-WIKI-LINK] {rel} → [[{link}]]")

    report_path = vault / "_lint_report.md"
    if issues:
        report_path.write_text(
            "# Lint Report\n\n" + "\n".join(f"- {i}" for i in issues) + "\n",
            encoding="utf-8",
        )
    else:
        report_path.write_text("# Lint Report\n\n모든 점검 통과.\n", encoding="utf-8")

    return {"issues": issues, "report": str(report_path)}
