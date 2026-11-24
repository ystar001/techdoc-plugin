"""입력 어댑터 — 카드·렌더 트리·참고문헌을 DocModel로 (v1.11).

경로는 설정(paths)에서 온다. 시리즈 규칙: `_`로 시작하는 폴더의 카드는 빼고,
렌더 트리에서 이름에 「참고문헌」이 든 md는 reference_md로 따로, `_`로 시작하는 파일은 뺀다.
참고문헌 md가 없으면 `render/*_full.md`의 「# 참고문헌」 절을 쓴다. draft는 따로 읽는다.
self-model 카드(`cards/*_card.json`)가 없으면 standard 모드 산출물(document_draft.json 등)의
tech/project/product 카드를 읽는다(v1.11-c).
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path

from techdoc_core.qc.config import ProjectConfig, layer_dirs
from techdoc_core.qc.model import DocModel, TreeFile

CARD_JSON_ERROR = "카드 JSON을 읽지 못함"  # VC-A가 load_errors에서 이 문구로 카드 읽기 실패를 센다


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
            errors.append(f"{p.name}: {CARD_JSON_ERROR} — {e}")
            continue
        if isinstance(data, dict):
            cards[p.stem.removesuffix("_card")] = data
    return cards


# ── standard 모드 (v1.11-c) ──
# 플러그인 기본 산출물: writer_state.json + document_draft.json(또는 document_final.json,
# sections/section_*.json). 카드는 tech/project/product 목록, 본문은 blocks dict(7/7/6).
_STD_CARD_LISTS = (("tech_cards", "tech"), ("project_cards", "project"),
                   ("product_cards", "product"))
# blocks dict가 없고 블록이 카드 최상위에 펼쳐진 꼴(옛 산출물)에서 모을 키 — models.py의 7/7/6
_STD_BLOCK_KEYS = {
    "tech": ("overview", "principle", "components", "performance", "pros_cons",
             "differentiation", "references"),
    "project": ("background", "organization", "methodology", "results", "implications",
                "followup", "references"),
    "product": ("background", "features", "specifications", "deployment", "market",
                "references"),
}
# 작성기가 선언한 인용 대상 목록 — 본문 인용이 아니므로 V8의 「쓰인 REF」에 넣지 않는다
_STD_DROP = ("ref_ids",)


def _std_card(raw: dict, kind: str) -> dict:
    card = {k: v for k, v in raw.items() if k not in _STD_DROP}
    if not isinstance(card.get("blocks"), dict):
        keys = _STD_BLOCK_KEYS[kind]
        card["blocks"] = {k: card.pop(k) for k in keys if k in card}
    return card


def _std_doc_cards(doc: dict, cards: dict[str, dict], label: str, errors: list[str]) -> None:
    """Document dict(또는 섹션 파일) 하나에서 카드·절 글을 cards에 더한다."""
    for sec in doc.get("sections") or []:
        # 절 개요·종합분석(html_content)도 렌더에 실리는 글 — 카드 수준 필드(section_overview)로
        if not isinstance(sec, dict) or not str(sec.get("html_content", "")).strip():
            continue
        sid = str(sec.get("section_id") or sec.get("id") or f"section-{len(cards) + 1}")
        cards.setdefault(sid, {"title": sec.get("title", ""),
                               "section_overview": sec["html_content"]})
    for list_key, kind in _STD_CARD_LISTS:
        for i, raw in enumerate(doc.get(list_key) or [], 1):
            if not isinstance(raw, dict):
                errors.append(f"{label}: {list_key}[{i}]가 카드(dict)가 아님 — 건너뜀")
                continue
            cid = str(raw.get("id") or f"{kind}-{i}")
            if cid in cards:  # 다른 종류 카드와 번호가 겹치면 종류를 붙여 둘 다 남긴다
                cid = f"{cid}~{kind}"
            cards[cid] = _std_card(raw, kind)


def _read_json(p: Path, errors: list[str]) -> dict | None:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        errors.append(f"{p.name}: JSON을 읽지 못함 — {e}")
        return None
    return data if isinstance(data, dict) else None


def _load_standard_cards(out_dir: Path, errors: list[str]) -> tuple[dict[str, dict], dict | None]:
    """document_draft.json → document_final.json → sections/section_*.json 중 처음 있는 것.

    draft가 앞서는 까닭: review·rewrite가 draft를 고쳐 쓰고 final은 렌더 직전 승격 사본이다.
    둘째 값은 읽은 Document 원본(섹션 파일이면 목록을 이어 붙인 것) — PLG-CQ 게이트가 쓴다.
    """
    cards: dict[str, dict] = {}
    for name in ("document_draft.json", "document_final.json"):
        p = out_dir / name
        if p.is_file():
            doc = _read_json(p, errors)
            if doc is not None:
                _std_doc_cards(doc, cards, name, errors)
                return cards, doc
    merged: dict | None = None
    for p in sorted((out_dir / "sections").glob("section_*.json")):
        doc = _read_json(p, errors)
        if doc is not None:
            _std_doc_cards(doc, cards, f"sections/{p.name}", errors)
            merged = merged or {"title": doc.get("title", "")}
            for key in ("sections", "tech_cards", "project_cards", "product_cards"):
                if isinstance(doc.get(key), list):
                    merged.setdefault(key, []).extend(doc[key])
    return cards, merged


def _standard_inputs(out_dir: Path, ref_path: Path, doc: dict) -> dict:
    """standard 모드 원본 묶음 — 문서·참고문헌 목록 원본·용어집(check_quality가 읽던 것과 같은 파일)."""
    from techdoc_core.qc.legacy.doc_metrics import load_glossary

    reflist = None
    if ref_path.is_file():
        with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
            data = json.loads(ref_path.read_text(encoding="utf-8"))
            reflist = data if isinstance(data, dict) else None
    return {"doc": doc, "reference_list": reflist, "glossary": load_glossary(out_dir)}


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
    cards = _load_cards(cfg.paths.cards, errors)
    standard = None
    if not cards:  # self-model 카드가 없으면 standard 모드 산출물(카드 폴더의 부모)에서
        out_dir = cfg.paths.cards.parent
        cards, raw_doc = _load_standard_cards(out_dir, errors)
        if raw_doc is not None:
            standard = _standard_inputs(out_dir, cfg.paths.references, raw_doc)
    return DocModel(
        root=Path(root),
        kind=cfg.kind,
        cards=cards,
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
        standard=standard,
    )
