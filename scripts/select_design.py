"""문서 제목 키워드 → 디자인 타입 자동 판별.

사용법:
    python -m scripts.select_design --title "스마트농업 기술보고서"
    python -m scripts.select_design --title "..." --type tech_report  # 수동 지정
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from techdoc_core.constants import DESIGN_TEMPLATE_DIR, DESIGN_TYPE_KEYWORDS


def detect_type(title: str) -> str:
    """제목 키워드에서 디자인 타입 자동 판별 (첫 일치)."""
    for type_key, keywords in DESIGN_TYPE_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            return type_key
    return "tech_report"  # fallback


def load_design_config(type_key: str) -> dict:
    """디자인 설정 로드."""
    design_dir = DESIGN_TEMPLATE_DIR / type_key
    config_path = design_dir / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"design not found: {type_key} ({config_path})")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    cfg["_design_dir"] = str(design_dir)
    cfg["_type_key"] = type_key
    return cfg


def load_design_css(design_config: dict) -> str:
    """디자인의 CSS 파일들을 하나로 결합.

    order: _shared/cards.css + _shared/appendix.css + components.css + cover.css + print.css
    """
    design_dir = Path(design_config["_design_dir"])
    shared_dir = DESIGN_TEMPLATE_DIR / "_shared"

    parts: list[str] = []
    # 공통 CSS 먼저
    for fname in ("cards.css", "appendix.css"):
        p = shared_dir / fname
        if p.exists():
            parts.append(f"/* === _shared/{fname} === */\n{p.read_text(encoding='utf-8')}")

    # 디자인별 CSS
    for fname in ("components.css", "cover.css", "print.css"):
        p = design_dir / fname
        if p.exists():
            parts.append(f"/* === {design_config['type_key']}/{fname} === */\n{p.read_text(encoding='utf-8')}")

    # 디자인별 color palette → :root CSS 변수 주입
    colors = design_config.get("colors", {})
    if colors:
        vars_css = ":root {\n"
        for key, value in colors.items():
            vars_css += f"  --color-{key.replace('_', '-')}: {value};\n"
        vars_css += "}\n"
        parts.insert(0, f"/* === palette: {design_config.get('name', '')} === */\n{vars_css}")

    return "\n\n".join(parts)


def list_available_designs() -> list[str]:
    """사용 가능한 디자인 목록."""
    return [
        d.name for d in DESIGN_TEMPLATE_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-select design template by title")
    ap.add_argument("--title", default="", help="문서 제목 (자동 판별용)")
    ap.add_argument("--type", dest="type_key", help="수동 지정 (tech_report 등)")
    ap.add_argument("--list", action="store_true", help="사용 가능한 디자인 목록")
    ap.add_argument("--css", action="store_true", help="CSS 결합 출력 (렌더링 테스트용)")
    args = ap.parse_args()

    if args.list:
        print("Available designs:")
        for t in list_available_designs():
            print(f"  - {t}")
        return 0

    type_key = args.type_key or detect_type(args.title)
    try:
        config = load_design_config(type_key)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.css:
        print(load_design_css(config))
        return 0

    print(json.dumps({
        "type_key": type_key,
        "name": config.get("name"),
        "components_count": len(config.get("components", [])),
        "colors_primary": config.get("colors", {}).get("primary"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
