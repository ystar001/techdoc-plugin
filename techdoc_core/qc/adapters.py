"""입력 어댑터 — 카드·렌더 트리·참고문헌을 DocModel로 (v1.11).

경로는 설정(paths)에서 온다. 시리즈 규칙: `_`로 시작하는 폴더의 카드는 빼고,
렌더 트리에서 이름에 「참고문헌」이 든 md는 reference_md로 따로, `_`로 시작하는 파일은 뺀다.
참고문헌 md가 없으면 `render/*_full.md`의 「# 참고문헌」 절을 쓴다. draft는 따로 읽는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from techdoc_core.qc.config import ProjectConfig
from techdoc_core.qc.model import DocModel, TreeFile


def _load_cards(cards_dir: Path, errors: list[str]) -> dict[str, dict]:
    cards: dict[str, dict] = {}
    if not cards_dir.is_dir():
        return cards
    for p in sorted(cards_dir.rglob("*_card.json")):
        rel_parts = p.relative_to(cards_dir).parts[:-1]
        if any(part.startswith("_") for part in rel_parts):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"{p.name}: 카드 JSON을 읽지 못함 — {e}")
            continue
        if isinstance(data, dict):
            cards[p.stem.removesuffix("_card")] = data
    return cards


def _load_tree(tree_dir: Path) -> tuple[list[TreeFile], list[TreeFile]]:
    tree: list[TreeFile] = []
    refs: list[TreeFile] = []
    if not tree_dir.is_dir():
        return tree, refs
    for p in sorted(tree_dir.rglob("*.md")):
        rel = p.relative_to(tree_dir).as_posix()
        name = p.name
        if name.startswith("_"):
            continue
        tf = TreeFile(rel=rel, text=p.read_text(encoding="utf-8"))
        (refs if "참고문헌" in name else tree).append(tf)
    if not refs:
        for full in sorted(tree_dir.parent.glob("*_full.md")):
            text = full.read_text(encoding="utf-8")
            k = text.find("\n# 참고문헌")
            if k >= 0:
                refs.append(TreeFile(rel=f"{full.name} 참고문헌", text=text[k:]))
    return tree, refs


_DRAFT_SKIP = ("_superseded", "_merged", "_archive")


def _load_draft(draft_dir: Path) -> list[TreeFile]:
    if not draft_dir.is_dir():
        return []
    return [TreeFile(rel=p.name, text=p.read_text(encoding="utf-8"))
            for p in sorted(draft_dir.glob("*.md")) if not p.name.startswith(_DRAFT_SKIP)]


def _load_references(path: Path, errors: list[str]) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{path.name}: 참고문헌 목록을 읽지 못함 — {e}")
        return []
    refs = data.get("refs") if isinstance(data, dict) else None
    return [r for r in refs or [] if isinstance(r, dict)]


def build_model(root: Path, cfg: ProjectConfig) -> DocModel:
    errors: list[str] = []
    tree, ref_md = _load_tree(cfg.paths.render_tree)
    return DocModel(
        root=Path(root),
        kind=cfg.kind,
        cards=_load_cards(cfg.paths.cards, errors),
        tree=tree,
        draft=_load_draft(cfg.paths.draft),
        references=_load_references(cfg.paths.references, errors),
        reference_md=ref_md,
        numbering=dict(cfg.numbering),
        exempt=dict(cfg.exempt),
        extra=dict(cfg.extra),
        load_errors=errors,
    )
