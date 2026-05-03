"""MkDocs 정적 사이트 옵션 — vault에 mkdocs.yml 자동 생성 (D 하이브리드)."""

from __future__ import annotations

from pathlib import Path

MKDOCS_TEMPLATE = """\
site_name: TechDoc Knowledge Wiki
docs_dir: .
site_dir: ../site
theme:
  name: material
  features:
    - navigation.instant
    - navigation.sections
    - navigation.expand
    - search.suggest
    - search.highlight
    - content.code.copy
  palette:
    - scheme: default
      primary: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - tables
  - footnotes
"""


def write_mkdocs_yml(vault_dir: Path) -> Path:
    """vault에 mkdocs.yml 작성. 기존 파일 있으면 보존 (사용자 커스터마이징 보호)."""
    target = vault_dir / "mkdocs.yml"
    if not target.exists():
        target.write_text(MKDOCS_TEMPLATE, encoding="utf-8")
    return target
