"""프로젝트 설정 `techdoc.project.yaml` (v1.11 — 설계 D1·D3.2).

층 선택(kind·domain·series)·번호 꼴·경로·게이트 끄기/면제/수준 덮어쓰기·게이트별 추가 설정을
한 파일에서 받는다. 파일이 없으면 플러그인 출력 관례의 기본값으로 돈다(하위 호환).

**겹침 순서**(v1.11-c, E18): 본체 기본 → 문서 종류 묶음(`kind.yaml`) → 프로젝트 파일. 뒤가 이긴다.
- 표(dict)는 키마다 재귀로 겹친다(`extra`·`gates.level`·`expects`) — 프로젝트가 적은 키만 바뀐다.
- 그 밖(문자열·수·목록 — `gates.off`, `extra.*`의 목록)은 **통째로 교체**한다. 목록을 이어 붙이지
  않는다: 프로젝트가 목록을 적으면 그 목록이 전부다.
- 문서 종류 묶음 위치: 플러그인 `bundles/kinds/<kind>/`(공개 종류), 프로젝트 `kind_dir:`(비공개 종류).
  묶음이 없으면 본체 기본으로 돌고 `warnings`에 한 줄 남긴다.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

import yaml

from techdoc_core.bundles.loader import core_bundle_dir, kinds_bundle_dir, read_kind_bundle
from techdoc_core.bundles.schema import GateSpec, Level

CONFIG_NAME = "techdoc.project.yaml"
SECTION_STYLES = ("arabic", "roman", "letter_middle")
# 문서 종류 이름(설계 D7). 묶음이 아직 없는 종류도 이름은 정해져 있다 — 오타를 잡으려는 목록
KNOWN_KINDS = ("tech_report", "methodology", "tech_encyclopedia", "adoption_guide", "policy_report")
_LEVELS = get_args(Level)

# ── extra.* 형식 — 게이트가 읽는 키만(모르는 키는 그대로 둔다) ──
_STR_LIST = "문자열 목록"
_STR = "문자열"
_POS_INT = "1 이상 정수"
_INT_MAP = "{이름: 0 이상 정수} 표"
_DICT = "표(dict)"
_BOOL = "참·거짓"
EXTRA_SHAPES: dict[str, dict[str, str]] = {
    "citation": {"internal_files": _STR_LIST, "nonprimary_ok": _DICT,
                 "card_ref_list_pattern": _STR, "group_authors_ok": _STR_LIST,
                 "group_author_fields": _STR_LIST},
    "code_namespace": {"pattern": _STR, "allow": _STR_LIST},
    "leak": {"file_patterns": _STR_LIST, "allow": _STR_LIST, "card_fields": _STR_LIST,
             "plan_docs": _STR_LIST},
    "check_quality": {"size_thresholds": _INT_MAP},
    "verify_cards": {"thresholds": _INT_MAP},
    "terms": {"abbr_rule_sentence": _STR},
    "repeat": {"allow_heads": _STR_LIST, "block_heads": _STR_LIST, "max_repeats": _POS_INT,
               "frame_heads": _POS_INT, "frame_chapters": _POS_INT},
    "prose": {"meta_words": _STR_LIST, "guide_words": _STR_LIST,
              "overview_prefixes": _STR_LIST, "markers": _DICT,
              "selfref_nouns": _STR_LIST, "selfref_verbs": _STR_LIST},
    "caption": {"skip_table_titles": _STR_LIST, "standard_table_words": _STR_LIST,
                "chart_axis_types": _STR_LIST, "chart_axis_keys": _DICT},
    "structure": {"peer_doc_names": _STR_LIST, "peer_prefix": _STR_LIST, "qs_jargon": _STR_LIST,
                  "intro_exempt_titles": _STR_LIST, "folder_names": _STR_LIST,
                  "appendix_letters": _STR, "conclusion_titles": _STR_LIST,
                  "conclusion_split_groups": _BOOL, "summary_retired_fields": _STR_LIST,
                  "summary_limits": _INT_MAP},
}


@dataclass
class Paths:
    cards: Path
    render_tree: Path
    references: Path
    draft: Path  # md 직접 저작 원고 — 있으면 산문 게이트가 렌더 트리 대신 본다(시리즈 규칙)
    outline: Path  # final_outline.json — 문서 구조 선언(아직 안 쓴 별첨도 실재로, V2)
    image_license: Path  # 이미지 라이선스 대장(V7)


@dataclass
class ProjectConfig:
    root: Path
    paths: Paths
    kind: str = "tech_report"
    kind_dir: Path | None = None  # 비공개 문서 종류 묶음 — 없으면 플러그인 bundles/kinds/<kind>
    domain: Path | None = None
    series: Path | None = None
    numbering: dict = field(default_factory=lambda: {"section": "arabic", "appendix": "letter"})
    gates_off: list[str] = field(default_factory=list)
    exempt: dict[str, dict] = field(default_factory=dict)  # "<cid>|<sec>" → {gates, why}
    level_overrides: dict[str, str] = field(default_factory=dict)
    expects: dict[str, str] = field(default_factory=dict)  # 게이트 id → ">=1"(문서 종류 묶음)
    extra: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _default_paths(root: Path) -> Paths:
    out = root / "output"
    return Paths(cards=out / "cards", render_tree=out / "render" / "tree",
                 references=out / "reference_list.json", draft=out / "draft",
                 outline=out / "final_outline.json",
                 image_license=out / "assets" / "images" / "LICENSE.tsv")


def default_config(root: Path) -> ProjectConfig:
    """본체 기본만 — 문서 종류 묶음을 겹치지 않은 설정(겹친 것은 load_config)."""
    return ProjectConfig(root=Path(root), paths=_default_paths(Path(root)))


def _opt_path(root: Path, value) -> Path | None:
    if not value:
        return None
    p = Path(value)
    return p if p.is_absolute() else (root / p)


def deep_merge(base: dict, over: Mapping) -> dict:
    """표는 키마다 재귀로 겹치고, 그 밖(값·목록)은 over가 통째로 이긴다. base는 바꾸지 않는다."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def kind_dir(cfg: ProjectConfig) -> Path:
    """문서 종류 묶음 디렉토리 — 프로젝트 `kind_dir`가 있으면 그것, 없으면 플러그인 묶음."""
    return cfg.kind_dir if cfg.kind_dir is not None else kinds_bundle_dir() / cfg.kind


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _shape_ok(shape: str, v) -> bool:
    if shape == _STR_LIST:
        return isinstance(v, list) and all(isinstance(x, str) for x in v)
    if shape == _STR:
        return isinstance(v, str)
    if shape == _POS_INT:
        return _is_int(v) and v >= 1
    if shape == _INT_MAP:
        return isinstance(v, dict) and all(_is_int(x) and x >= 0 for x in v.values())
    if shape == _BOOL:
        return isinstance(v, bool)
    return isinstance(v, dict)


def validate_extra(extra) -> None:
    """게이트가 읽는 `extra.*` 키의 형을 본다 — 틀리면 키 이름을 담은 ValueError.

    예: `repeat.allow_heads: "결론"`(문자열 — 목록이어야 함), `repeat.max_repeats: 0`(1 이상이어야
    함 — 예전에는 조용히 기본 3이 됐다), `check_quality.size_thresholds: {S: "많이"}`.
    """
    if not isinstance(extra, dict):
        raise ValueError(f"extra는 표(dict)여야 함: {type(extra).__name__}")
    for group, keys in EXTRA_SHAPES.items():
        if group not in extra or extra[group] is None:
            continue
        g = extra[group]
        if not isinstance(g, dict):
            raise ValueError(f"extra.{group}는 표(dict)여야 함: {g!r}")
        for key, shape in keys.items():
            if key in g and g[key] is not None and not _shape_ok(shape, g[key]):
                raise ValueError(f"extra.{group}.{key}는 {shape}여야 함: {g[key]!r}")


def _read_kind(cfg: ProjectConfig) -> dict | None:
    """문서 종류 묶음 읽기 — 없으면 None과 경고 한 줄(모르는 kind는 그 경고로 갈음)."""
    directory = kind_dir(cfg)
    bundle = read_kind_bundle(directory) if directory.is_dir() else None
    if bundle is None and (cfg.kind in KNOWN_KINDS or cfg.kind_dir is not None):
        cfg.warnings.append(f"문서 종류 묶음이 없음 — 본체 기본으로 돈다: {cfg.kind} ({directory})")
    return bundle


def _levels(raw, where: str) -> dict[str, str]:
    levels = {str(k): str(v) for k, v in (raw or {}).items()}
    bad = {k: v for k, v in levels.items() if v not in _LEVELS}
    if bad:
        raise ValueError(f"{where} 값은 {_LEVELS} 중 하나: {bad}")
    return levels


def load_config(root: Path, path: Path | None = None) -> ProjectConfig:
    """설정 읽기 — 본체 기본 → 문서 종류 묶음 → 프로젝트 파일(뒤가 이김, 모듈 설명의 겹침 규칙).

    path가 없으면 root/techdoc.project.yaml, 그것도 없으면 본체 기본 + 문서 종류 묶음.
    """
    root = Path(root)
    cfg_path = Path(path) if path else root / CONFIG_NAME
    data = {}
    if cfg_path.is_file():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    cfg = default_config(root)
    cfg.kind = str(data.get("kind", cfg.kind))
    cfg.kind_dir = _opt_path(root, data.get("kind_dir"))
    cfg.domain = _opt_path(root, data.get("domain"))
    cfg.series = _opt_path(root, data.get("series"))

    numbering = {**cfg.numbering, **(data.get("numbering") or {})}
    if numbering["section"] not in SECTION_STYLES:
        raise ValueError(f"numbering.section은 {SECTION_STYLES} 중 하나: {numbering['section']!r}")
    cfg.numbering = numbering

    paths = data.get("paths") or {}
    for key in ("cards", "render_tree", "references", "draft", "outline", "image_license"):
        if paths.get(key):
            setattr(cfg.paths, key, _opt_path(root, paths[key]))

    if cfg.kind not in KNOWN_KINDS:
        cfg.warnings.append(f"모르는 문서 종류 kind: {cfg.kind} (알려진 것: {', '.join(KNOWN_KINDS)})")
    kind = _read_kind(cfg) or {"level": {}, "off": [], "extra": {}, "expects": {}}

    gates = data.get("gates") or {}
    # YAML 1.1(PyYAML)은 키 `off`를 불리언 False로 읽는다 — 두 꼴 모두 받는다
    has_off = "off" in gates or False in gates
    off = gates.get("off", gates.get(False)) if has_off else kind["off"]
    cfg.gates_off = [str(g) for g in off or []]  # 목록 — 프로젝트가 적으면 통째로 교체
    exempt = gates.get("exempt") or {}
    bad_keys = [k for k in exempt if not isinstance(k, str)]
    if bad_keys:
        # YAML은 1.10·1.1을 숫자 1.1 하나로 접는다 — 카드 id는 따옴표로 감싸야 한다
        raise ValueError(f"gates.exempt의 카드 id는 따옴표로 감싸야 함(\"1.10|sec2\"): {bad_keys}")
    cfg.exempt = {}
    for key, val in exempt.items():
        # 원본 형식: "<카드id>|<섹션키>" 또는 "<카드id>": {gates: [...], why: "사유"}
        if not isinstance(val, dict) or not str(val.get("why") or "").strip():
            raise ValueError(f"gates.exempt[{key}]: 면제 사유(why) 필요 — 면제는 침묵이 아니라 기록")
        cfg.exempt[key] = {"gates": [str(g) for g in val.get("gates") or []],
                           "why": str(val["why"])}
    cfg.level_overrides = {**_levels(kind["level"], "문서 종류 묶음 gates.level"),
                           **_levels(gates.get("level"), "gates.level")}
    cfg.expects = {**kind["expects"],
                   **{str(k): str(v) for k, v in (data.get("expects") or {}).items()}}
    project_extra = data.get("extra") or {}
    validate_extra(kind["extra"])
    validate_extra(project_extra)
    cfg.extra = deep_merge(kind["extra"], project_extra)
    for name in ("domain", "series"):
        p = getattr(cfg, name)
        if p is not None and not p.is_dir():
            cfg.warnings.append(f"{name} 묶음 경로가 없음 — 그 층 게이트가 빠짐: {p}")
    return cfg


def validate_gate_ids(cfg: ProjectConfig, known: set[str] | Mapping[str, GateSpec]) -> None:
    """설정이 부르는 게이트 id 중 모르는 것을 cfg.warnings에 더한다(조용한 무시 금지).

    `known`이 {id: GateSpec}이면 면제가 먹지 않는 게이트(`exemptable: false`)에 적은 면제도 경고한다.
    """
    seen: list[str] = []
    named = [*cfg.gates_off, *cfg.level_overrides, *cfg.expects]
    for ent in cfg.exempt.values():
        named.extend(ent["gates"])
    for gid in named:
        if gid not in known and gid not in seen:
            seen.append(gid)
            cfg.warnings.append(f"모르는 게이트 id: {gid}")
    if not isinstance(known, Mapping):
        return
    for key, ent in cfg.exempt.items():
        for gid in ent["gates"]:
            spec = known.get(gid)
            if spec is not None and not getattr(spec, "exemptable", True):
                cfg.warnings.append(f"면제가 먹지 않는 게이트(exemptable: false)에 적은 면제: "
                                    f"{gid} @ {key} — 이 지적은 그대로 남는다")


def layer_dirs(cfg: ProjectConfig) -> list[tuple[str, Path | None]]:
    """load_gate_specs 입력 — 본체 → 문서 종류 → 분야 → 시리즈 → 프로젝트."""
    core = core_bundle_dir()
    kdir = kind_dir(cfg)
    project_dir = cfg.root / ".techdoc"
    return [
        ("core", core),
        ("kind", kdir if kdir.is_dir() else None),
        ("domain", cfg.domain),
        ("series", cfg.series),
        ("project", project_dir if project_dir.is_dir() else None),
    ]
