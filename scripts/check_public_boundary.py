"""공개 경계 검사 — public 미러(techdoc-plugin/)에 비공개 낱말이 새지 않게 (v1.11-a, E12).

낱말 목록(편 이름·기관 이름 등)은 private 쪽 파일에 두고 경로로 받는다. 지금 이미 있는
검출은 baseline 파일로 묶어 두고 새 검출만 막는다. 낱말 목록이 없으면 검사를 못 한 것이므로
종료 코드 2(조용한 통과 금지). subtree push 전에 돌린다.

사용법:
    python -m scripts.check_public_boundary --words ../.boundary_words.txt \
        [--root .] [--baseline ../.boundary_baseline.txt] [--write-baseline]
"""
from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".css", ".js", ".html", ".txt", ".toml"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "node_modules"}


def scan(root: Path, words: list[str], baseline: set[str]) -> list[str]:
    """root 아래 텍스트 파일에서 낱말이 든 줄 → "<상대경로>:<줄>: <낱말>" (baseline 제외)."""
    hits: list[str] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = p.relative_to(root).as_posix()
        for i, line in enumerate(lines, 1):
            for w in words:
                key = f"{rel}:{i}: {w}"
                if w in line and key not in baseline:
                    hits.append(key)
    return hits


def _read_lines(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="공개 레포 비공개 낱말 검사")
    ap.add_argument("--root", default=".")
    ap.add_argument("--words", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()

    words_path = Path(args.words)
    if not words_path.is_file():
        print(f"낱말 목록 없음 — 검사 못 함: {words_path}", file=sys.stderr)
        return 2
    words = _read_lines(words_path)
    base_path = Path(args.baseline) if args.baseline else None
    baseline = set(_read_lines(base_path)) if base_path and base_path.is_file() else set()
    hits = scan(Path(args.root), words, baseline)
    if args.write_baseline and base_path:
        base_path.write_text("\n".join(sorted(baseline | set(hits))) + "\n", encoding="utf-8")
        print(f"baseline 기록: {len(hits)}건 추가 → {base_path}")
        return 0
    for h in hits:
        print(f"[BOUNDARY] {h}")
    print(f"새 검출 {len(hits)}건 (baseline {len(baseline)}건 제외)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
