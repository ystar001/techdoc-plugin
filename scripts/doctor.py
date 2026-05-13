"""환경 진단 — 설치 직후 첫 실행 권장.

검증 항목:
  - Python 버전 (>=3.10)
  - 필수 의존성 (pydantic, rapidfuzz, matplotlib, jinja2, rich)
  - 한글 폰트 가용성 (matplotlib)
  - 선택 의존성 (playwright, python-docx) — 없으면 PDF/DOCX 비활성
  - techdoc_core 디자인 템플릿 5종 존재
  - 공통 CSS (_shared) 존재

사용법:
    python -m scripts.doctor
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


class DoctorResult:
    def __init__(self):
        self.checks: list[dict] = []
        self.fatal = 0
        self.warnings = 0
        self.ok_count = 0

    def add(self, name: str, status: str, detail: str = "", fix: str = ""):
        self.checks.append({"name": name, "status": status, "detail": detail, "fix": fix})
        if status == "FAIL":
            self.fatal += 1
        elif status == "WARN":
            self.warnings += 1
        elif status == "OK":
            self.ok_count += 1

    def print_summary(self):
        print("=" * 70)
        print(f"{'Check':<35}{'Status':<10}{'Detail'}")
        print("-" * 70)
        for c in self.checks:
            mark = {"OK": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}.get(c["status"], c["status"])
            detail = c["detail"][:30] if c["detail"] else ""
            print(f"{c['name']:<35}{mark:<10}{detail}")
        print("-" * 70)
        print(f"  OK: {self.ok_count}, WARN: {self.warnings}, FAIL: {self.fatal}")
        print("=" * 70)

        # 수정 제안
        suggestions = [c for c in self.checks if c["fix"]]
        if suggestions:
            print("\n수정 제안:")
            for c in suggestions:
                print(f"  [{c['name']}] {c['fix']}")


def check_python_version(r: DoctorResult) -> None:
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        r.add("Python version", "FAIL",
              detail=f"{major}.{minor} (need >=3.10)",
              fix="Python 3.10 이상 설치")
    else:
        r.add("Python version", "OK", detail=f"{major}.{minor}.{sys.version_info.micro}")


def check_import(r: DoctorResult, module: str, required: bool, fix_hint: str = "") -> None:
    try:
        importlib.import_module(module)
        r.add(f"import {module}", "OK")
    except ImportError:
        status = "FAIL" if required else "WARN"
        r.add(f"import {module}", status,
              detail="not installed",
              fix=fix_hint or f"pip install {module}")


def check_korean_font(r: DoctorResult) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import font_manager
    except ImportError:
        r.add("Korean font", "FAIL", detail="matplotlib not available",
              fix="pip install matplotlib")
        return

    candidates = ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    found = [n for n in candidates if n in available]

    if found:
        r.add("Korean font", "OK", detail=found[0])
    else:
        r.add("Korean font", "WARN",
              detail="no Korean font",
              fix="Pretendard 또는 NanumGothic 설치 (matplotlib 한글 표시용)")


def check_techdoc_core(r: DoctorResult) -> None:
    try:
        import techdoc_core
        r.add("techdoc_core", "OK", detail=f"v{techdoc_core.__version__}")
    except ImportError:
        r.add("techdoc_core", "FAIL",
              detail="not installed",
              fix="cd techdoc-plugin && pip install -e .")


def check_design_templates(r: DoctorResult) -> None:
    try:
        from techdoc_core.constants import DESIGN_TEMPLATE_DIR
    except ImportError:
        r.add("design templates", "FAIL",
              detail="techdoc_core not importable",
              fix="pip install -e . 먼저 실행")
        return

    expected = ["tech_report", "business_plan", "policy_report",
                "research_report", "education_material"]
    missing = []
    for name in expected:
        p = DESIGN_TEMPLATE_DIR / name / "config.json"
        if not p.exists():
            missing.append(name)

    if missing:
        r.add("design templates (5종)", "FAIL",
              detail=f"missing: {','.join(missing)}",
              fix="plugin 재설치")
    else:
        r.add("design templates (5종)", "OK", detail="all present")

    shared = DESIGN_TEMPLATE_DIR / "_shared"
    for fname in ("cards.css", "appendix.css"):
        if not (shared / fname).exists():
            r.add(f"_shared/{fname}", "FAIL", detail="missing", fix="plugin 재설치")


def check_playwright_chromium(r: DoctorResult) -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        r.add("playwright (PDF)", "WARN",
              detail="not installed",
              fix="pip install techdoc-plugin[pdf] — HTML/MD만 생성 가능")
        return

    # Chromium 바이너리 확인 시도
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            if browser_path and Path(browser_path).exists():
                r.add("playwright chromium", "OK")
            else:
                r.add("playwright chromium", "WARN",
                      detail="browser missing",
                      fix="playwright install chromium")
    except Exception as e:
        r.add("playwright chromium", "WARN",
              detail=str(e)[:30],
              fix="playwright install chromium")


def check_output_dir(r: DoctorResult, output_dir: str = "./output") -> None:
    """output 디렉토리 Write 권한 사전 점검 (F6 방어)."""
    from scripts.preflight import check_write_permission

    p = Path(output_dir)
    if p.exists() and not p.is_dir():
        r.add(f"output dir ({output_dir})", "FAIL",
              detail="not a directory",
              fix=f"rm {output_dir}")
        return

    ok, reason = check_write_permission(p)
    if ok:
        r.add(f"output dir ({output_dir})", "OK", detail="Write preflight 통과")
    else:
        r.add(f"output dir ({output_dir})", "FAIL",
              detail=reason,
              fix=f"권한 확인 후 재시도 (POSIX: chmod +w {output_dir})")


def main() -> int:
    ap = argparse.ArgumentParser(description="TechDoc environment doctor")
    ap.add_argument("--output", default="./output", help="output 디렉토리 (확인용)")
    args = ap.parse_args()

    r = DoctorResult()

    check_python_version(r)
    check_import(r, "pydantic", required=True)
    check_import(r, "rapidfuzz", required=True)
    check_import(r, "matplotlib", required=True)
    check_import(r, "yaml", required=True, fix_hint="pip install pyyaml")
    check_import(r, "jinja2", required=True)
    check_import(r, "rich", required=True)
    check_import(r, "httpx", required=True)
    check_import(r, "fitz", required=False,
                 fix_hint="pip install pymupdf — 사용자 제공 PDF 참고 자료 처리용")
    check_techdoc_core(r)
    check_design_templates(r)
    check_korean_font(r)
    check_playwright_chromium(r)
    check_import(r, "docx", required=False,
                 fix_hint="pip install techdoc-plugin[docx] — DOCX 생성 시")
    check_output_dir(r, args.output)

    r.print_summary()
    return 0 if r.fatal == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
