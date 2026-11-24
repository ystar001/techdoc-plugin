"""build_release 앞단 점검 — 발행 체크리스트 자동화 (findings F108, 개선 순환 B2).

판 번호 네 곳·CHANGELOG 최신 판 일치, 닫힘/부분 대응 마커 위생, 공개 경계,
발행 커밋 지정(--commit, git worktree)을 시험한다. 실제 설치본·홈 폴더는 건드리지 않는다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import build_release
from scripts.build_release import main, preflight

GOOD_CHANGELOG = """# Changelog

## [Unreleased]

## [1.2.0] — 2026-11-24

### Added

- 새 기능 (findings F10, F11)
- F12 부분 대응 — 나머지는 다음 판

### Note

- 참고

## [1.1.0] — 2026-07-01

### Fixed

- **F5** 고침
"""


def make_plugin(root: Path, version: str = "1.2.0", changelog: str = GOOD_CHANGELOG,
                versions: dict | None = None) -> Path:
    """네 곳에 판 번호를 둔 가짜 플러그인."""
    v = {"plugin": version, "market": version, "init": version, "pyproject": version}
    v.update(versions or {})
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "techdoc-plugin", "version": v["plugin"]}), encoding="utf-8")
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": "m", "plugins": [{"name": "techdoc-plugin", "version": v["market"]}],
    }), encoding="utf-8")
    (root / "techdoc_core").mkdir()
    (root / "techdoc_core" / "__init__.py").write_text(
        f'"""코어."""\n\n__version__ = "{v["init"]}"\n', encoding="utf-8")
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "techdoc-plugin"\nversion = "{v["pyproject"]}"\n', encoding="utf-8")
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "a.py").write_text("# 일반 코드\n", encoding="utf-8")
    return root


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    return make_plugin(tmp_path / "repo" / "techdoc-plugin")


@pytest.fixture
def words(tmp_path: Path) -> Path:
    p = tmp_path / "words.txt"
    p.write_text("# 낱말\nSecretSeries\n", encoding="utf-8")
    return p


# ── 판 번호 ─────────────────────────────────────────────────────────────────


def test_preflight_ok(plugin, words):
    errors, _ = preflight(plugin, words_path=words)
    assert errors == []


def test_version_mismatch_fails_f108(tmp_path, words):
    """F108 — 판 번호가 네 곳 중 한 곳이라도 어긋나면 실패."""
    root = make_plugin(tmp_path / "p", versions={"market": "1.1.0"})
    errors, _ = preflight(root, words_path=words)
    assert any("marketplace.json" in e for e in errors)


def test_init_version_mismatch_fails(tmp_path, words):
    root = make_plugin(tmp_path / "p", versions={"init": "1.0.9"})
    errors, _ = preflight(root, words_path=words)
    assert any("__version__" in e for e in errors)


def test_changelog_latest_mismatch_fails(tmp_path, words):
    """CHANGELOG 최신 판 제목이 plugin.json 판과 다르면 실패."""
    root = make_plugin(tmp_path / "p", version="1.3.0")
    errors, _ = preflight(root, words_path=words)
    assert any("CHANGELOG" in e for e in errors)


def test_unreleased_with_content_fails(tmp_path, words):
    """[Unreleased]에 내용이 있으면 발행 판에 미발행 변경이 섞인다 — 실패."""
    cl = GOOD_CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\n- 아직 안 낸 것\n")
    root = make_plugin(tmp_path / "p", changelog=cl)
    errors, _ = preflight(root, words_path=words)
    assert any("Unreleased" in e for e in errors)


# ── 마커 위생 ───────────────────────────────────────────────────────────────


def test_partial_and_closed_marker_conflict_fails_f108(tmp_path, words):
    """F108 — 같은 카드가 발행 판에서 닫힘 마커와 「부분 대응」을 함께 가지면 실패."""
    cl = GOOD_CHANGELOG.replace("(findings F10, F11)", "(findings F10, F11, F12)")
    root = make_plugin(tmp_path / "p", changelog=cl)
    errors, _ = preflight(root, words_path=words)
    assert any("F12" in e and "부분 대응" in e for e in errors)


def test_closed_in_two_versions_fails_f108(tmp_path, words):
    """F108 — 이미 이전 판에서 닫힌 카드를 다시 닫힘 마커로 적으면 실패."""
    cl = GOOD_CHANGELOG.replace("(findings F10, F11)", "(findings F10, F11, F5)")
    root = make_plugin(tmp_path / "p", changelog=cl)
    errors, _ = preflight(root, words_path=words)
    assert any("F5" in e and "1.1.0" in e for e in errors)


def test_marker_in_note_section_not_closing(tmp_path, words):
    """Note 하위절의 언급은 닫힘으로 보지 않는다(sync_findings와 같은 규칙)."""
    cl = GOOD_CHANGELOG.replace("- 참고", "- 참고 (findings F5)")
    root = make_plugin(tmp_path / "p", changelog=cl)
    errors, _ = preflight(root, words_path=words)
    assert errors == []


def test_private_lint_missing_warns(plugin, words, monkeypatch):
    """private 린트 경로가 없으면 조용히 넘기지 않고 경고."""
    monkeypatch.delenv("TECHDOC_FINDINGS_LINT", raising=False)
    _, warnings = preflight(plugin, words_path=words)
    assert any("TECHDOC_FINDINGS_LINT" in w for w in warnings)


def test_private_lint_marker_warning_fails(plugin, words, monkeypatch, tmp_path):
    """private 린트가 마커 위생 경고를 내면 실패, 다른 경고는 안내만."""
    fake = tmp_path / "fake_lint.py"
    fake.write_text(
        "print('  [LINT] F7: 닫힘 마커가 여러 판에 있음 [\\'1.2.0\\', \\'1.1.0\\']')\n"
        "print('  [LINT] 중복 후보: 열린 카드 3장이 `x.py`을 가리킴')\n"
        "print('lint — 경고 2건')\n", encoding="utf-8")
    monkeypatch.setenv("TECHDOC_FINDINGS_LINT", str(fake))
    errors, warnings = preflight(plugin, words_path=words)
    assert any("F7" in e for e in errors)
    assert any("중복 후보" in w for w in warnings)


# ── 공개 경계 ───────────────────────────────────────────────────────────────


def test_missing_words_file_warns_f108(plugin, tmp_path):
    """F108 — 낱말 목록이 없으면 건너뛰지 않고 경고한다."""
    errors, warnings = preflight(plugin, words_path=tmp_path / "none.txt")
    assert errors == []
    assert any("낱말 목록" in w for w in warnings)


def test_new_boundary_hit_fails_f108(plugin, words):
    """F108 — 공개 경계 새 검출이 있으면 실패."""
    (plugin / "scripts" / "b.py").write_text("# SecretSeries 전용\n", encoding="utf-8")
    errors, _ = preflight(plugin, words_path=words)
    assert any("공개 경계" in e for e in errors)


def test_boundary_baseline_excludes(plugin, words, tmp_path):
    (plugin / "scripts" / "b.py").write_text("# SecretSeries 전용\n", encoding="utf-8")
    base = tmp_path / "base.txt"
    base.write_text("scripts/b.py: SecretSeries: # SecretSeries 전용\n", encoding="utf-8")
    errors, _ = preflight(plugin, words_path=words, baseline_path=base)
    assert errors == []


# ── main ────────────────────────────────────────────────────────────────────


def test_main_preflight_failure_builds_nothing(tmp_path, words):
    root = make_plugin(tmp_path / "p", versions={"pyproject": "0.0.1"})
    out = tmp_path / "dist"
    rc = main(["--plugin-root", str(root), "--output", str(out),
               "--boundary-words", str(words)])
    assert rc != 0
    assert not out.exists() or not any(out.iterdir())


def test_main_skip_preflight_warns(tmp_path, words, capsys):
    root = make_plugin(tmp_path / "p", versions={"pyproject": "0.0.1"})
    out = tmp_path / "dist"
    rc = main(["--plugin-root", str(root), "--output", str(out), "--skip-preflight"])
    assert rc == 0
    assert (out / "techdoc-plugin-v1.2.0.zip").exists()
    assert "skip-preflight" in capsys.readouterr().err


def test_main_ok_builds(plugin, words, tmp_path):
    out = tmp_path / "dist"
    rc = main(["--plugin-root", str(plugin), "--output", str(out),
               "--boundary-words", str(words)])
    assert rc == 0
    assert (out / "techdoc-plugin-v1.2.0.zip").exists()


# ── --commit (git worktree) ─────────────────────────────────────────────────


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="git 없음")
def test_commit_option_builds_from_worktree_f108(plugin, words, tmp_path, capsys):
    """F108 — --commit <sha>는 그 커밋의 작업 트리에서 만들고, worktree는 치운다."""
    repo = plugin.parent
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "판 1.2.0")
    sha = _git(repo, "rev-parse", "HEAD")
    # 작업 트리는 다음 판으로 앞서 있음(커밋 안 함, 판 번호도 어긋남)
    (plugin / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n', encoding="utf-8")

    out = tmp_path / "dist"
    rc = main(["--plugin-root", str(plugin), "--output", str(out),
               "--boundary-words", str(words), "--commit", sha[:7]])
    assert rc == 0
    assert (out / "techdoc-plugin-v1.2.0.zip").exists()
    worktrees = _git(repo, "worktree", "list")
    assert len(worktrees.splitlines()) == 1     # 임시 worktree 정리됨
    printed = capsys.readouterr().out
    assert sha in printed                       # 전체 해시로 안내
    assert "subtree split" in printed and "--target" in printed


def test_read_versions_locations(plugin):
    vs = build_release.read_versions(plugin)
    assert set(vs) == {"plugin.json", "marketplace.json", "__version__", "pyproject.toml"}
    assert set(vs.values()) == {"1.2.0"}
