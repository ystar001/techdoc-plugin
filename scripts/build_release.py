"""배포용 ZIP 아카이브 생성.

buildscript that packages the plugin into a distributable archive.
불필요한 파일 (캐시·빌드·테스트 결과) 자동 제외.

사용법:
    python -m scripts.build_release                    # 현재 plugin.json 버전으로 dist/ 생성
    python -m scripts.build_release --output ./releases
    python -m scripts.build_release --version 0.1.1    # 버전 오버라이드 (임시)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


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


def main() -> int:
    ap = argparse.ArgumentParser(description="Build TechDoc Plugin release archive")
    ap.add_argument("--output", default="./dist", help="출력 디렉토리 (기본: ./dist)")
    ap.add_argument("--version", help="버전 오버라이드 (기본: plugin.json 참조)")
    ap.add_argument("--plugin-root", default=".", help="플러그인 루트 (기본: 현재 디렉토리)")
    ap.add_argument("--wrapped", action="store_true",
                    help="ZIP에 techdoc-plugin/ 래퍼 폴더 포함 (기본: flat, 권장)")
    ap.add_argument("--both", action="store_true",
                    help="flat + wrapped 두 버전 모두 빌드")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root).resolve()
    if not (plugin_root / ".claude-plugin" / "plugin.json").exists():
        print(f"ERROR: not a plugin root (missing .claude-plugin/plugin.json): {plugin_root}",
              file=sys.stderr)
        return 1

    builds_to_run = []
    if args.both:
        builds_to_run = [True, False]  # flat, wrapped
    else:
        builds_to_run = [not args.wrapped]

    try:
        results = []
        for flat in builds_to_run:
            archive_path, metadata = build(plugin_root, Path(args.output), args.version, flat=flat)
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
