"""차트 생성 — Claude가 생성한 명세 JSON → matplotlib 이미지.

명세 JSON 포맷:
    {
      "id": "fig_1_2",
      "type": "bar" | "line" | "pie" | "radar" | "comparison",
      "title": "스마트 관개 기술별 물 절감률 비교",
      "x_label": "...",
      "y_label": "...",
      "data": {...},
      "is_appendix": false
    }

사용법:
    python -m scripts.generate_chart --spec ./output/chart_spec.json -o ./output/figures/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 백엔드 고정 (headless)
import matplotlib.pyplot as plt  # noqa: E402

from techdoc_core.schemas import format_error


# 한글 폰트 시도 (Windows는 맑은 고딕, macOS는 AppleGothic, Linux는 NanumGothic)
def _configure_korean_font():
    candidates = ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic",
                  "NanumBarunGothic", "DejaVu Sans"]
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


_configure_korean_font()


def render_bar(ax, spec: dict) -> None:
    data = spec.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = data.get("colors") or ["#1E3A5C", "#2D6A9F", "#0891B2", "#059669", "#D97706"]
    ax.bar(labels, values, color=colors[:len(labels)])
    if spec.get("x_label"):
        ax.set_xlabel(spec["x_label"])
    if spec.get("y_label"):
        ax.set_ylabel(spec["y_label"])


def render_line(ax, spec: dict) -> None:
    data = spec.get("data", {})
    x = data.get("x", [])
    series = data.get("series", [])  # [{"name": "A", "y": [...]}, ...]
    for s in series:
        ax.plot(x, s["y"], label=s.get("name", ""), marker="o", linewidth=2)
    if series and any(s.get("name") for s in series):
        ax.legend()
    if spec.get("x_label"):
        ax.set_xlabel(spec["x_label"])
    if spec.get("y_label"):
        ax.set_ylabel(spec["y_label"])


def render_pie(ax, spec: dict) -> None:
    data = spec.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")


def render_radar(ax, spec: dict) -> None:
    """레이더 차트 (별첨용 성능 비교)."""
    import numpy as np
    data = spec.get("data", {})
    categories = data.get("categories", [])
    series = data.get("series", [])  # [{"name": ..., "values": [...]}]

    n = len(categories)
    if n < 3:
        return
    angles = [i / n * 2 * 3.14159265 for i in range(n)]
    angles += angles[:1]

    for s in series:
        vals = s["values"] + s["values"][:1]
        ax.plot(angles, vals, label=s.get("name", ""), linewidth=2)
        ax.fill(angles, vals, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    if series:
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))


def render_comparison(ax, spec: dict) -> None:
    """가로 비교 막대 (grouped bar)."""
    import numpy as np
    data = spec.get("data", {})
    categories = data.get("categories", [])
    groups = data.get("groups", [])  # [{"name": ..., "values": [...]}]

    n_groups = len(groups)
    n_cats = len(categories)
    width = 0.8 / max(1, n_groups)
    x_idx = np.arange(n_cats)

    for i, g in enumerate(groups):
        offset = (i - (n_groups - 1) / 2) * width
        ax.bar(x_idx + offset, g["values"], width=width, label=g.get("name", ""))

    ax.set_xticks(x_idx)
    ax.set_xticklabels(categories)
    if groups:
        ax.legend()


RENDERERS = {
    "bar": render_bar,
    "line": render_line,
    "pie": render_pie,
    "radar": render_radar,
    "comparison": render_comparison,
}


def generate_figure(spec: dict, output_dir: Path) -> Path:
    """명세 → PNG 파일 생성."""
    chart_type = spec.get("type", "bar")
    renderer = RENDERERS.get(chart_type)
    if renderer is None:
        raise ValueError(format_error("TECHDOC-E050", f"Unknown chart type: {chart_type}"))

    fig_size = (10, 6) if spec.get("is_appendix") else (8, 5)
    if chart_type == "radar":
        fig, ax = plt.subplots(figsize=fig_size, subplot_kw=dict(polar=True))
    else:
        fig, ax = plt.subplots(figsize=fig_size)

    renderer(ax, spec)

    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=13, pad=14)

    if chart_type != "pie" and chart_type != "radar":
        ax.grid(True, linestyle="--", alpha=0.3)

    plt.tight_layout()

    chart_id = spec.get("id", "fig_unnamed")
    out_path = output_dir / f"{chart_id}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def generate_from_specs(specs_path: Path, output_dir: Path) -> list[dict]:
    """specs 파일 (단일 dict 또는 list) → 여러 PNG."""
    data = json.loads(specs_path.read_text(encoding="utf-8"))
    specs = data if isinstance(data, list) else [data]

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for spec in specs:
        try:
            png_path = generate_figure(spec, output_dir)
            results.append({
                "id": spec.get("id"),
                "type": spec.get("type"),
                "path": str(png_path),
                "is_appendix": spec.get("is_appendix", False),
                "status": "ok",
            })
        except (ValueError, KeyError) as e:
            results.append({
                "id": spec.get("id"),
                "status": "error",
                "error": str(e),
            })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate charts from JSON specs")
    ap.add_argument("--spec", required=True, help="chart_spec.json (list 또는 단일 dict)")
    ap.add_argument("-o", "--output", default="./output/figures", help="PNG 출력 디렉토리")
    args = ap.parse_args()

    results = generate_from_specs(Path(args.spec), Path(args.output))
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"생성: {ok}/{len(results)}")
    for r in results:
        mark = "OK" if r["status"] == "ok" else "FAIL"
        tag = " [appendix]" if r.get("is_appendix") else ""
        print(f"  {mark}: {r.get('id')}{tag}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
