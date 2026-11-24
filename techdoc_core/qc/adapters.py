"""입력 어댑터 — 카드·렌더 트리·참고문헌을 DocModel로 (v1.11).

경로는 설정(paths)에서 온다. 시리즈 규칙: `_`로 시작하는 폴더의 카드는 빼고,
렌더 트리에서 이름에 「참고문헌」이 든 md는 reference_md로 따로, `_`로 시작하는 파일은 뺀다.
참고문헌 md가 없으면 `render/*_full.md`의 「# 참고문헌」 절을 쓴다. draft는 따로 읽는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from techdoc_core.qc.config import ProjectConfig, layer_dirs
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


def _read_md(p: Path, label: str, errors: list[str]) -> str | None:
    """UTF-8이 아닌 md는 건너뛰고 보고한다(실행 전체가 죽지 않게)."""
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(f"{label}: UTF-8이 아니라 건너뜀 — {e.reason}")
        return None


def _load_tree(tree_dir: Path, errors: list[str]) -> tuple[list[TreeFile], list[TreeFile]]:
    tree: list[TreeFile] = []
    refs: list[TreeFile] = []
    if not tree_dir.is_dir():
        return tree, refs
    for p in sorted(tree_dir.rglob("*.md")):
        rel = p.relative_to(tree_dir).as_posix()
        name = p.name
        if name.startswith("_"):
            continue
        text = _read_md(p, rel, errors)
        if text is None:
            continue
        tf = TreeFile(rel=rel, text=text)
        (refs if "참고문헌" in name else tree).append(tf)
    if not refs:
        for full in sorted(tree_dir.parent.glob("*_full.md")):
            text = _read_md(full, full.name, errors) or ""
            k = text.find("\n# 참고문헌")
            if k >= 0:
                refs.append(TreeFile(rel=f"{full.name} 참고문헌", text=text[k:]))
    return tree, refs


_DRAFT_SKIP = ("_superseded", "_merged", "_archive")


def _load_draft(draft_dir: Path, errors: list[str]) -> list[TreeFile]:
    if not draft_dir.is_dir():
        return []
    out: list[TreeFile] = []
    for p in sorted(draft_dir.glob("*.md")):
        if p.name.startswith(_DRAFT_SKIP):
            continue
        text = _read_md(p, f"draft/{p.name}", errors)
        if text is not None:
            out.append(TreeFile(rel=p.name, text=text))
    return out


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


def _load_outline(path: Path, errors: list[str]) -> dict:
    """final_outline.json — 원본처럼 읽지 못하면 빈 것으로(별첨 선언이 없을 뿐)."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        errors.append(f"{path.name}: 문서 구조 선언을 읽지 못함 — {e}")
        return {}
    return data if isinstance(data, dict) else {}


def _load_license(path: Path, errors: list[str]) -> str | None:
    """이미지 라이선스 대장(V7) — 없으면 None(이미지가 있으면 V7이 전부 잡는다, 원본과 같음)."""
    if not path.is_file():
        return None
    return _read_md(path, path.name, errors)


def build_model(root: Path, cfg: ProjectConfig) -> DocModel:
    errors: list[str] = []
    tree, ref_md = _load_tree(cfg.paths.render_tree, errors)
    return DocModel(
        root=Path(root),
        kind=cfg.kind,
        cards=_load_cards(cfg.paths.cards, errors),
        tree=tree,
        draft=_load_draft(cfg.paths.draft, errors),
        references=_load_references(cfg.paths.references, errors),
        reference_md=ref_md,
        outline=_load_outline(cfg.paths.outline, errors),
        numbering=dict(cfg.numbering),
        exempt=dict(cfg.exempt),
        image_license=_load_license(cfg.paths.image_license, errors),
        extra=dict(cfg.extra),
        load_errors=errors,
        layers=layer_dirs(cfg),
    )
