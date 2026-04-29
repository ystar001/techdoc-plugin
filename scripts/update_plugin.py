"""TechDoc Plugin 온라인 업데이트.

GitHub Releases (ystar001/techdoc-plugin)에서 최신 zip을 받아 plugin 디렉토리를 갱신.

사용법:
    python -m scripts.update_plugin            # 적용 (사용자 [y/N] 확인 후)
    python -m scripts.update_plugin --check    # 체크만
    python -m scripts.update_plugin --force    # 동일 버전이어도 강제 재설치
"""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx


class PluginError(Exception):
    """plugin 상태가 비정상일 때 발생."""


def read_current_version(plugin_root: Path) -> str:
    """plugin_root/.claude-plugin/plugin.json에서 version 읽기."""
    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        raise PluginError(f"plugin.json을 찾을 수 없습니다: {plugin_json}")
    try:
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PluginError(f"plugin.json 파싱 실패: {e}") from e
    version = data.get("version")
    if not version:
        raise PluginError("plugin.json에 version 필드가 없습니다")
    return str(version)


def _parse_version(v: str) -> tuple[int, int, int]:
    """semver 문자열을 (major, minor, patch) 정수 튜플로 파싱.

    'v1.1.0', '1.1.0' 모두 처리. pre-release suffix는 무시.
    """
    s = v.strip().lstrip("v")
    s = re.split(r"[-+]", s, maxsplit=1)[0]
    parts = s.split(".")
    if len(parts) != 3:
        raise ValueError(f"invalid semver: {v!r}")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def is_newer(latest: str, current: str) -> bool:
    """latest 가 current 보다 더 새 버전이면 True."""
    return _parse_version(latest) > _parse_version(current)


# ── GitHub Releases 조회 ──────────────────────────────────────────────────────

GITHUB_API_LATEST = "https://api.github.com/repos/ystar001/techdoc-plugin/releases/latest"


@dataclass
class Release:
    version: str
    tag_name: str
    name: str
    body: str
    published_at: str
    zip_url: str


def fetch_latest_release(transport: httpx.BaseTransport | None = None) -> Release:
    """GitHub Releases API로 최신 릴리스 메타 조회.

    transport: 테스트용 MockTransport를 주입할 때만 사용.
    """
    try:
        with httpx.Client(transport=transport, timeout=15.0) as client:
            resp = client.get(GITHUB_API_LATEST)
    except httpx.HTTPError as e:
        raise PluginError(f"GitHub API 호출 실패 (네트워크): {e}") from e

    if resp.status_code != 200:
        raise PluginError(
            f"GitHub API 응답 오류 status={resp.status_code} body={resp.text[:200]}"
        )

    payload = resp.json()
    tag = payload.get("tag_name", "")
    version = tag.lstrip("v")

    zip_url = ""
    for asset in payload.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".zip"):
            zip_url = asset.get("browser_download_url", "")
            break
    if not zip_url:
        raise PluginError("릴리스에 zip 자산이 없습니다")

    return Release(
        version=version,
        tag_name=tag,
        name=payload.get("name", ""),
        body=payload.get("body", ""),
        published_at=payload.get("published_at", ""),
        zip_url=zip_url,
    )


# ── zip 다운로드·적용 ────────────────────────────────────────────────────────


def download_zip(
    url: str,
    dest_dir: Path,
    transport: httpx.BaseTransport | None = None,
) -> Path:
    """zip URL에서 파일을 받아 dest_dir에 저장. 저장 경로 반환."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.rstrip("/").rsplit("/", 1)[-1] or "techdoc-plugin.zip"
    dest = dest_dir / filename

    try:
        with httpx.Client(transport=transport, timeout=120.0, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise PluginError(f"zip 다운로드 실패 status={resp.status_code}")
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                        f.write(chunk)
    except httpx.HTTPError as e:
        raise PluginError(f"zip 다운로드 네트워크 오류: {e}") from e

    return dest


def apply_zip(zip_path: Path, plugin_root: Path) -> None:
    """zip 파일을 plugin_root에 압축 해제. 기존 파일은 덮어쓰기, zip에 없는 파일은 보존.

    먼저 zip이 plugin 형식(.claude-plugin/plugin.json 포함)인지 검증.
    """
    if not zipfile.is_zipfile(zip_path):
        raise PluginError(f"zip 파일이 아닙니다: {zip_path}")

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        has_manifest = any(
            n.endswith(".claude-plugin/plugin.json") or n == ".claude-plugin/plugin.json"
            for n in names
        )
        if not has_manifest:
            raise PluginError("zip 형식이 잘못되었습니다 (.claude-plugin/plugin.json 없음)")

        zf.extractall(plugin_root)
