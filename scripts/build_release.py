"""배포용 ZIP 아카이브 생성.

buildscript that packages the plugin into a distributable archive.
불필요한 파일 (캐시·빌드·테스트 결과) 자동 제외.

빌드 전에 발행 체크리스트를 자동 점검한다(findings F108, 개선 순환 B2) — 하나라도
실패하면 아무것도 만들지 않고 종료 코드 1:
  ① 판 번호 네 곳(plugin.json·marketplace.json·__version__·pyproject.toml)과
     CHANGELOG 최신 판 제목 `## [X.Y.Z]` 일치, `[Unreleased]`에 내용 없음
  ② CHANGELOG 발행 판 절의 마커 위생 — 같은 카드가 닫힘 마커와 「부분 대응」을 함께
     갖거나, 이전 판에서 이미 닫힌 카드를 다시 닫으면 실패. 환경 변수
     `TECHDOC_FINDINGS_LINT`가 private `sync_findings.py`를 가리키면 그 `--lint`도 돌린다
     (없으면 경고 — 공개 플러그인은 private 저장소에 기대지 않는다)
  ③ 공개 경계 새 검출 0 — 낱말 목록이 없으면 건너뛰지 않고 경고

사용법:
    python -m scripts.build_release                    # 현재 plugin.json 버전으로 dist/ 생성
    python -m scripts.build_release --output ./releases
    python -m scripts.build_release --commit <sha>     # 그 커밋의 작업 트리에서(git worktree)
    python -m scripts.build_release --boundary-words ../.boundary_words.txt
    python -m scripts.build_release --skip-preflight   # 점검 생략(비상용, 경고 출력)
    python -m scripts.build_release --version 0.1.1    # 버전 오버라이드 (임시)
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from scripts.check_public_boundary import _read_lines, scan


# 배포에서 제외할 패턴
EXCLUDE_PATTERNS = (
    # Python 빌드·캐시
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".egg-info",
    "*.pyc",
    "*.pyo",
    # 개발 산출물
    "output/",
    "demo_output/",
    "test_output/",
    "backups/",
    "dist/",
    "build/",
    ".coverage",
    "htmlcov/",
    # IDE·OS
    ".vscode",
    ".idea",
    ".DS_Store",
    "Thumbs.db",
    # 환경·시크릿
    ".env",
    ".env.local",
    # Git
    ".git",
    ".gitignore",  # dist에는 필요 없음 (설치 후 git repo 불필요)
)

# 명시적으로 포함할 경로 (패턴에 우선)
INCLUDE_ROOTS = (
    "bundles",
    ".claude-plugin",
    "agents",
    "commands",
    "prompts",
    "scripts",
    "techdoc_core",
    "pyproject.toml",
    "README.md",
    "CHANGELOG.md",
    "REQUIREMENTS_TRACEABILITY.md",
    "INSTALL.md",
    "USAGE.md",
)


def should_exclude(path: Path) -> bool:
    """경로가 제외 패턴과 일치하면 True."""
    for pat in EXCLUDE_PATTERNS:
        if pat.endswith("/"):
            # 디렉토리 이름이 경로 안에 포함되는지
            pat_clean = pat.rstrip("/")
            if pat_clean in path.parts:
                return True
        elif pat.startswith("*."):
            # 확장자 매칭
            if path.suffix == pat[1:]:
                return True
        elif pat in path.parts:
            # 정확한 디렉토리·파일명
            return True
    return False


def collect_files(plugin_root: Path) -> list[Path]:
    """배포 대상 파일 수집."""
    collected: list[Path] = []

    for root in INCLUDE_ROOTS:
        root_path = plugin_root / root
        if not root_path.exists():
            continue

        if root_path.is_file():
            if not should_exclude(root_path):
                collected.append(root_path)
        else:
            for f in root_path.rglob("*"):
                if f.is_file() and not should_exclude(f):
                    collected.append(f)

    return sorted(collected)


def compute_sha256(file_path: Path) -> str:
    """파일 SHA-256 해시."""
    h = hashlib.sha256()
    with file_path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_version(plugin_root: Path) -> str:
    """plugin.json에서 버전 읽기."""
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"plugin.json not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data.get("version", "0.0.0")


# ── 발행 앞단 점검 (findings F108, 개선 순환 B2) ──────────────────────────────

_INIT_VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.M)
_PYPROJECT_VERSION_RE = re.compile(r"""^version\s*=\s*["']([^"']+)["']""", re.M)
# CHANGELOG 판 제목 — sync_findings와 같은 꼴
_CHANGELOG_VERSION_RE = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]", re.M)
_UNRELEASED_RE = re.compile(r"^##\s*\[Unreleased\][^\n]*$", re.M | re.I)
_ANY_H2_RE = re.compile(r"^##\s", re.M)
_SUBSECTION_RE = re.compile(r"^###\s+(.+)$", re.M)
# 닫힘 마커: 줄머리 `- **FNN**` 또는 `findings FNN(, FMM…)` — sync_findings와 같은 규칙
_CLOSED_BOLD_RE = re.compile(r"^\s*-\s*\*\*F(\d+)\*\*", re.M)
_CLOSED_LIST_RE = re.compile(r"findings\s+(F\d+(?:\s*,\s*F\d+)*)")
# 닫힘으로 인정하는 하위절(Note·Compatibility 등의 언급은 닫힘이 아님)
_CLOSED_HEADINGS = ("added", "fixed", "changed", "removed")
# 「F54·F57·F77은 이번에 부분 대응」「F82 부분 대응」 — 부분 대응 앞에 붙은 카드 번호 목록
_PARTIAL_RE = re.compile(r"(F\d+(?:\s*[·,/와과및]\s*F\d+)*)[^\n.()]{0,20}?부분\s*대응")
# private sync_findings --lint 결과 중 마커 위생 경고(발행을 막음)
_LINT_MARKER_HINTS = ("닫힘 마커가 여러 판", "CHANGELOG가 닫는 카드가 findings에 없음",
                      "테스트에 F")

FINDINGS_LINT_ENV = "TECHDOC_FINDINGS_LINT"


def read_versions(plugin_root: Path) -> dict[str, str]:
    """판 번호 네 곳 → {위치: 판}. 읽지 못한 곳은 빈 문자열."""
    out: dict[str, str] = {}
    cp = plugin_root / ".claude-plugin"
    with contextlib.suppress(OSError, ValueError):
        out["plugin.json"] = str(
            json.loads((cp / "plugin.json").read_text(encoding="utf-8")).get("version", ""))
    out.setdefault("plugin.json", "")
    market = ""
    with contextlib.suppress(OSError, ValueError, AttributeError):
        data = json.loads((cp / "marketplace.json").read_text(encoding="utf-8"))
        for ent in data.get("plugins", []):
            if ent.get("name") == "techdoc-plugin":
                market = str(ent.get("version", ""))
                break
    out["marketplace.json"] = market
    init = ""
    with contextlib.suppress(OSError):
        m = _INIT_VERSION_RE.search(
            (plugin_root / "techdoc_core" / "__init__.py").read_text(encoding="utf-8"))
        init = m.group(1) if m else ""
    out["__version__"] = init
    pyp = ""
    with contextlib.suppress(OSError):
        m = _PYPROJECT_VERSION_RE.search(
            (plugin_root / "pyproject.toml").read_text(encoding="utf-8"))
        pyp = m.group(1) if m else ""
    out["pyproject.toml"] = pyp
    return out


def _changelog_sections(text: str) -> list[tuple[str, str]]:
    """[(판, 절 본문)] — 최신이 앞."""
    ms = list(_CHANGELOG_VERSION_RE.finditer(text))
    out = []
    for i, m in enumerate(ms):
        nxt = _ANY_H2_RE.search(text, m.end())
        end = nxt.start() if nxt else len(text)
        if i + 1 < len(ms):
            end = min(end, ms[i + 1].start())
        out.append((m.group(1), text[m.end():end]))
    return out


def _closing_regions(section: str):
    """닫힘 마커를 셀 영역 — 첫 ### 앞 + Added/Fixed/Changed/Removed 하위절만."""
    heads = list(_SUBSECTION_RE.finditer(section))
    if not heads:
        yield section
        return
    yield section[: heads[0].start()]
    for i, h in enumerate(heads):
        if h.group(1).strip().lower().startswith(_CLOSED_HEADINGS):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(section)
            yield section[h.end():end]


def closed_ids(section: str) -> set[int]:
    """판 절에서 닫힘 마커가 붙은 카드 번호."""
    ids: set[int] = set()
    for region in _closing_regions(section):
        ids.update(int(n) for n in _CLOSED_BOLD_RE.findall(region))
        for lm in _CLOSED_LIST_RE.finditer(region):
            ids.update(int(n) for n in re.findall(r"F(\d+)", lm.group(1)))
    return ids


def partial_ids(section: str) -> set[int]:
    """판 절에서 「부분 대응」으로 적힌 카드 번호."""
    ids: set[int] = set()
    for m in _PARTIAL_RE.finditer(section):
        ids.update(int(n) for n in re.findall(r"F(\d+)", m.group(1)))
    return ids


def check_versions(plugin_root: Path) -> tuple[list[str], str]:
    """판 번호 네 곳 + CHANGELOG 최신 판·[Unreleased] 점검 → (오류, 기준 판)."""
    errors: list[str] = []
    versions = read_versions(plugin_root)
    ref = versions.get("plugin.json", "")
    for where, v in versions.items():
        if not v:
            errors.append(f"판 번호를 읽지 못함: {where}")
        elif v != ref:
            errors.append(f"판 번호 어긋남: {where}={v} ≠ plugin.json={ref}")
    cl_path = plugin_root / "CHANGELOG.md"
    if not cl_path.is_file():
        errors.append("CHANGELOG.md 없음")
        return errors, ref
    text = cl_path.read_text(encoding="utf-8")
    sections = _changelog_sections(text)
    if not sections:
        errors.append("CHANGELOG에 판 제목 `## [X.Y.Z]`가 없음")
    elif sections[0][0] != ref:
        errors.append(f"CHANGELOG 최신 판 [{sections[0][0]}] ≠ plugin.json {ref} "
                      f"— 발행 판 제목 `## [{ref}]`를 맨 위 판으로")
    um = _UNRELEASED_RE.search(text)
    if um:
        nxt = _ANY_H2_RE.search(text, um.end())
        body = text[um.end(): nxt.start() if nxt else len(text)]
        if body.strip():
            errors.append("CHANGELOG [Unreleased]에 내용이 있음 — 미발행 변경이 발행 판에 섞인다"
                          " (판 제목으로 옮기거나 --commit으로 판 시점 커밋에서 빌드)")
    return errors, ref


def check_markers(plugin_root: Path, version: str) -> list[str]:
    """발행 판 절의 닫힘/부분 대응 마커 위생."""
    cl_path = plugin_root / "CHANGELOG.md"
    if not cl_path.is_file():
        return []
    sections = _changelog_sections(cl_path.read_text(encoding="utf-8"))
    current = [s for v, s in sections if v == version]
    if not current:
        return []
    errors: list[str] = []
    closed = closed_ids(current[0])
    for n in sorted(closed & partial_ids(current[0])):
        errors.append(f"F{n}: v{version}에서 닫힘 마커와 「부분 대응」이 함께 있음 "
                      "— 기대를 다 채웠을 때만 마커를 단다")
    for v, sec in sections:
        if v == version:
            continue
        for n in sorted(closed & closed_ids(sec)):
            errors.append(f"F{n}: 이미 v{v}에서 닫혔는데 v{version}에서 다시 닫힘 마커 "
                          "— 후속 개선은 마커 꼴을 쓰지 않는다")
    return errors


def run_private_lint(plugin_root: Path) -> tuple[list[str], list[str]]:
    """private sync_findings --lint (선택) → (오류, 경고)."""
    path = os.environ.get(FINDINGS_LINT_ENV, "").strip()
    if not path or not Path(path).is_file():
        why = "미설정" if not path else f"파일 없음: {path}"
        return [], [f"findings 린트 건너뜀({FINDINGS_LINT_ENV} {why}) — 로컬 마커 점검만 했다"]
    try:
        proc = subprocess.run(
            [sys.executable, path, "--lint", "--changelog", str(plugin_root / "CHANGELOG.md")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, check=False,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},  # cp949 콘솔에서도 한글 경고를 읽게
        )
    except (OSError, subprocess.SubprocessError) as e:
        return [f"findings 린트 실행 실패: {e}"], []
    errors: list[str] = []
    warnings: list[str] = []
    for line in proc.stdout.splitlines():
        if "[LINT]" not in line:
            continue
        msg = line.split("[LINT]", 1)[1].strip()
        (errors if any(h in msg for h in _LINT_MARKER_HINTS) else warnings).append(
            f"findings 린트: {msg}")
    if proc.returncode != 0:
        errors.append(f"findings 린트 종료 코드 {proc.returncode}: {proc.stderr.strip()[:200]}")
    return errors, warnings


def check_boundary(plugin_root: Path, words_path: Path | None,
                   baseline_path: Path | None) -> tuple[list[str], list[str]]:
    """공개 경계 새 검출 → (오류, 경고). 낱말 목록이 없으면 경고(조용한 통과 금지)."""
    if words_path is None or not words_path.is_file():
        return [], [f"공개 경계 낱말 목록 없음 — 경계 검사를 못 했다: {words_path} "
                    "(--boundary-words로 지정, subtree push 전 반드시 확인)"]
    words = _read_lines(words_path)
    baseline = (set(_read_lines(baseline_path))
                if baseline_path is not None and baseline_path.is_file() else set())
    hits = scan(plugin_root, words, baseline)
    return [f"공개 경계 새 검출: {key} (줄 {ln})" for key, ln in hits], []


def preflight(plugin_root: Path, words_path: Path | None = None,
              baseline_path: Path | None = None) -> tuple[list[str], list[str]]:
    """발행 체크리스트 → (오류, 경고). 오류가 하나라도 있으면 빌드하지 않는다."""
    errors, version = check_versions(plugin_root)
    warnings: list[str] = []
    errors += check_markers(plugin_root, version)
    e, w = run_private_lint(plugin_root)
    errors += e
    warnings += w
    e, w = check_boundary(plugin_root, words_path, baseline_path)
    errors += e
    warnings += w
    return errors, warnings


# ── 발행 커밋 (git worktree) ────────────────────────────────────────────────


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()


def git_context(plugin_root: Path, commit: str = "HEAD") -> tuple[Path, str, str] | None:
    """(저장소 최상위, 플러그인 접두 경로, 커밋 전체 해시). git이 아니면 None."""
    try:
        top = Path(_git(plugin_root, "rev-parse", "--show-toplevel")).resolve()
        sha = _git(plugin_root, "rev-parse", "--verify", f"{commit}^{{commit}}")
    except (OSError, subprocess.CalledProcessError):
        return None
    prefix = plugin_root.resolve().relative_to(top).as_posix()
    return top, prefix, sha


def print_publish_guide(prefix: str, sha: str, version: str, dist: Path) -> None:
    """subtree split·Release 안내 — 실행하지 않고 보여 주기만 한다."""
    pre = prefix or "."
    print("발행 안내 (실행하지 않음 — 확인 후 직접):")
    print(f"  발행 커밋(전체 해시): {sha}")
    print(f"  git tag v{version} {sha}")
    print(f"  SPLIT=$(git subtree split --prefix={pre} {sha})")
    print("  git push plugin $SPLIT:main          # 공개 main 빨리감기")
    print(f"  gh release create v{version} {dist.as_posix()}/techdoc-plugin-v{version}.zip* "
          "--repo ystar001/techdoc-plugin --target $SPLIT   # --target은 전체 해시")
    print("  뒤이어: 태그 push → /techdoc-update(installPath 갱신) → sync_findings --apply")


def build(plugin_root: Path, output_dir: Path, version: str | None = None,
          flat: bool = True) -> tuple[Path, dict]:
    """배포 아카이브 생성.

    Args:
        flat: True면 ZIP 최상위에 `.claude-plugin/`이 바로 오도록 (래퍼 폴더 없음).
              Claude Code `/plugin marketplace add` 표준. 기본값.
              False면 `techdoc-plugin/` 래퍼 폴더 포함 (수동 배치용).

    Returns:
        (archive_path, metadata_dict)
    """
    ver = version or read_version(plugin_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = "" if flat else "-wrapped"
    archive_name = f"techdoc-plugin-v{ver}{suffix}.zip"
    archive_path = output_dir / archive_name

    files = collect_files(plugin_root)
    if not files:
        raise RuntimeError("No files collected — check INCLUDE_ROOTS")

    total_size = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in files:
            rel = f.relative_to(plugin_root)
            arcname = rel if flat else Path("techdoc-plugin") / rel
            zf.write(f, arcname=str(arcname))
            total_size += f.stat().st_size

    archive_size = archive_path.stat().st_size
    sha256 = compute_sha256(archive_path)

    # 메타데이터·체크섬 파일
    metadata = {
        "name": "techdoc-plugin",
        "version": ver,
        "archive": archive_name,
        "archive_size_bytes": archive_size,
        "archive_size_human": f"{archive_size / 1024:.1f} KB",
        "raw_size_bytes": total_size,
        "raw_size_human": f"{total_size / 1024:.1f} KB",
        "compression_ratio": round((1 - archive_size / total_size) * 100, 1),
        "file_count": len(files),
        "sha256": sha256,
    }

    meta_path = output_dir / f"techdoc-plugin-v{ver}.metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    # SHA256 체크섬 파일 (단독)
    checksum_path = output_dir / f"{archive_name}.sha256"
    checksum_path.write_text(f"{sha256}  {archive_name}\n", encoding="utf-8")

    return archive_path, metadata


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Build TechDoc Plugin release archive")
    ap.add_argument("--output", default="./dist", help="출력 디렉토리 (기본: ./dist)")
    ap.add_argument("--version", help="버전 오버라이드 (기본: plugin.json 참조)")
    ap.add_argument("--plugin-root", default=".", help="플러그인 루트 (기본: 현재 디렉토리)")
    ap.add_argument("--wrapped", action="store_true",
                    help="ZIP에 techdoc-plugin/ 래퍼 폴더 포함 (기본: flat, 권장)")
    ap.add_argument("--both", action="store_true",
                    help="flat + wrapped 두 버전 모두 빌드")
    ap.add_argument("--commit",
                    help="이 커밋의 작업 트리에서 빌드(git worktree, 끝나면 치움). 기본: 현재 작업 트리")
    ap.add_argument("--boundary-words",
                    help="공개 경계 낱말 목록 (기본: <plugin-root>/../.boundary_words.txt)")
    ap.add_argument("--boundary-baseline",
                    help="공개 경계 baseline (기본: <plugin-root>/../.boundary_baseline.txt)")
    ap.add_argument("--skip-preflight", action="store_true",
                    help="발행 앞단 점검 생략 — 비상용, 경고를 크게 낸다")
    args = ap.parse_args(argv)

    plugin_root = Path(args.plugin_root).resolve()
    if not (plugin_root / ".claude-plugin" / "plugin.json").exists():
        print(f"ERROR: not a plugin root (missing .claude-plugin/plugin.json): {plugin_root}",
              file=sys.stderr)
        return 1

    words = (Path(args.boundary_words) if args.boundary_words
             else plugin_root.parent / ".boundary_words.txt")
    baseline = (Path(args.boundary_baseline) if args.boundary_baseline
                else plugin_root.parent / ".boundary_baseline.txt")
    output = Path(args.output).resolve()

    if not args.commit:
        ctx = git_context(plugin_root)
        rc = _build_and_report(plugin_root, output, args, words, baseline)
        if rc == 0 and ctx:
            print("주의: 현재 작업 트리에서 빌드했다 — 커밋 안 된 변경이 있으면 발행 커밋과 다르다. "
                  "master가 다음 판까지 앞섰으면 --commit <판 커밋>을 쓴다.")
            print_publish_guide(ctx[1], ctx[2], read_version(plugin_root), output)
        return rc

    ctx = git_context(plugin_root, args.commit)
    if ctx is None:
        print(f"ERROR: --commit {args.commit}을(를) 찾지 못함(git 저장소·커밋 확인)", file=sys.stderr)
        return 1
    top, prefix, sha = ctx
    with tempfile.TemporaryDirectory(prefix="techdoc-release-",
                                     ignore_cleanup_errors=True) as tmp:
        wt = Path(tmp) / "wt"
        try:
            _git(top, "worktree", "add", "--detach", str(wt), sha)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: git worktree add 실패: {e.stderr.strip()}", file=sys.stderr)
            return 1
        try:
            build_root = wt / prefix if prefix else wt
            print(f"발행 커밋 {sha}의 작업 트리에서 빌드: {build_root}")
            rc = _build_and_report(build_root, output, args, words, baseline)
            version = read_version(build_root) if rc == 0 else ""
        finally:
            with contextlib.suppress(OSError, subprocess.CalledProcessError):
                _git(top, "worktree", "remove", "--force", str(wt))
            with contextlib.suppress(OSError, subprocess.CalledProcessError):
                _git(top, "worktree", "prune")
    if rc == 0:
        print_publish_guide(prefix, sha, args.version or version, output)
    return rc


def _build_and_report(plugin_root: Path, output: Path, args: argparse.Namespace,
                      words: Path, baseline: Path) -> int:
    """앞단 점검 → 빌드 → 요약 출력. 점검 실패면 아무것도 만들지 않는다."""
    if args.skip_preflight:
        print("!" * 70, file=sys.stderr)
        print("경고: --skip-preflight — 판 번호·마커 위생·공개 경계 점검을 건너뛴다. "
              "이 ZIP을 그대로 발행하지 말 것.", file=sys.stderr)
        print("!" * 70, file=sys.stderr)
    else:
        errors, warnings = preflight(plugin_root, words_path=words, baseline_path=baseline)
        for w in warnings:
            print(f"[경고] {w}", file=sys.stderr)
        if errors:
            for e in errors:
                print(f"[실패] {e}", file=sys.stderr)
            print(f"발행 앞단 점검 실패 {len(errors)}건 — 빌드하지 않음", file=sys.stderr)
            return 1
        print(f"발행 앞단 점검 통과 (경고 {len(warnings)}건)")

    builds_to_run = []
    if args.both:
        builds_to_run = [True, False]  # flat, wrapped
    else:
        builds_to_run = [not args.wrapped]

    try:
        results = []
        for flat in builds_to_run:
            archive_path, metadata = build(plugin_root, output, args.version, flat=flat)
            results.append((archive_path, metadata, flat))
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    for archive_path, metadata, flat in results:
        variant = "flat" if flat else "wrapped"
        print("=" * 70)
        print(f"Release archive ({variant}): {archive_path}")
        print("=" * 70)
        print(f"  Version:          {metadata['version']}")
        print(f"  Files:            {metadata['file_count']}")
        print(f"  Raw size:         {metadata['raw_size_human']}")
        print(f"  Archive size:     {metadata['archive_size_human']} "
              f"(압축률 {metadata['compression_ratio']}%)")
        print(f"  SHA-256:          {metadata['sha256']}")
        print(f"  Metadata: {archive_path.parent / (archive_path.stem + '.metadata.json')}")
        print(f"  Checksum: {archive_path}.sha256")
        if flat:
            print("  구조: ZIP 루트에 .claude-plugin/ 바로 (/plugin marketplace add 권장)")
        else:
            print("  구조: ZIP 루트에 techdoc-plugin/ 래퍼 (수동 배치용)")
        print()

    print("팀원 설치 안내 → INSTALL.md 참조")

    return 0


if __name__ == "__main__":
    sys.exit(main())
