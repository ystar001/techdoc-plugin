---
description: TechDoc Plugin을 GitHub Releases 최신 버전으로 갱신 (수동 트리거)
allowed-tools: Bash
argument-hint: "[--check] [--force] [--yes] [--installed-json <path>]"
---

# /techdoc-update — TechDoc Plugin 온라인 업데이트

GitHub Releases(`ystar001/techdoc-plugin`, public)에서 최신 zip을 받아 plugin 디렉토리를 자동 갱신합니다. LLM 호출 없이 결정론적 후처리.

**갱신 대상 = installPath (F108)**: Claude Code가 실제로 읽는 폴더는 `~/.claude/plugins/installed_plugins.json`의 techdoc 항목 `installPath`입니다. 설치 캐시의 다른 판 폴더에서 실행해도 그 installPath 폴더를 갱신하고, 갱신 뒤 판을 installPath 기준으로 보고합니다. json 항목의 `version`·`lastUpdated`도 맞추며, 고치기 전 `installed_plugins.json.bak-<시각>` 백업을 남깁니다. installPath 자체는 바꾸지 않습니다(기존 폴더를 백업·적용·롤백하는 쪽이 되돌리기 쉬움). json에 techdoc 항목이 없으면 경고 후 실행 폴더를 갱신하고, installPath 폴더가 비어 있으면 엉뚱한 폴더를 고치지 않고 멈춥니다(exit 1).

## 옵션

- `--check`: 체크만, 실제 적용 안 함. 새 버전 발견 시 CHANGELOG 미리보기 표시.
- `--force`: 동일 버전이어도 강제 재설치 (디버깅·복구용).
- `--yes`(`-y`): 확인 없이 적용 (비대화식 — 스크립트·자동화용).
- `--installed-json <path>`: `installed_plugins.json` 위치 지정 (기본: `~/.claude/plugins/installed_plugins.json`, 환경 변수 `TECHDOC_INSTALLED_PLUGINS`로도 지정).
- (옵션 없음): 새 버전이 있으면 [y/N] 확인 후 적용.

## 실행

`scripts/update_plugin.py`를 모듈로 호출하세요:

```bash
cd "$CLAUDE_PROJECT_DIR" && python -m scripts.update_plugin $ARGUMENTS
```

또는 plugin이 별도 경로에 설치된 경우:

```bash
cd <plugin-install-dir> && python -m scripts.update_plugin $ARGUMENTS
```

## 출력

**최신:**
```
TechDoc Plugin v1.0.0 — 최신 버전 사용 중입니다.
```

**새 버전 발견 + 미적용 (--check):**
```
TechDoc Plugin 신규 버전 발견
  현재: v1.0.0
  최신: v1.1.0  (2026-05-15 릴리스)

CHANGELOG (v1.1.0):
  ## CHANGELOG
  - Obsidian LLM Wiki 통합
  - ...
```

**적용 진행:**
```
... (위와 같이 요약) ...
업데이트하시겠습니까? [y/N]: y
백업 생성: <installPath>/backups/2026-11-24-101500
installed_plugins.json 갱신 (백업: ~/.claude/plugins/installed_plugins.json.bak-20261124-011500)
설치 판(installPath 기준): v1.1.0 — <installPath>
완료. /reload-plugins 실행을 권장합니다.
```

## 안전 장치 (v1.1.1+)

- **SHA-256 무결성 검증**: 다운로드한 zip을 GitHub Release의 `.sha256` 자산과 대조. 불일치 시 적용 거부 후 종료 (exit 2). `.sha256` 자산이 없는 구버전 release는 경고만 출력하고 계속 진행 (역호환).
- **적용 전 자동 백업**: `<plugin_root>/backups/<YYYY-MM-DD-HHMMSS>/`에 현재 plugin 디렉토리 전체를 복사. 백업 경로는 표준출력으로 안내.
- **실패 시 자동 롤백**: zip 적용 중 예외 발생 시 직전 백업을 사용해 원상 복구. 롤백마저 실패하면 백업 경로를 안내해 수동 복원 가능.
- **수동 롤백**: `rm -rf <plugin_root>/*`(단, `backups/` 제외) 후 `cp -r <backup>/. <plugin_root>/`.

## 정책

- 자동 알림 없음 — 사용자가 명시적으로 호출해야 함.
- LLM 호출 0회.

## 트러블슈팅

- **`plugin.json을 찾을 수 없습니다`**: plugin 설치 디렉토리에서 실행하지 않은 경우. 해당 디렉토리로 cd 후 재실행.
- **`installPath 폴더에 플러그인이 없습니다`**: json이 가리키는 폴더가 지워졌거나 비어 있음. `/plugin`으로 다시 설치하거나 json의 installPath를 확인.
- **갱신했는데 옛 판이 돈다**: v1.11 이전 `update_plugin`은 실행한 폴더만 바꿨다(F108). 지금 판으로 한 번 더 실행하면 installPath 폴더가 갱신된다.
- **`GitHub API 응답 오류 status=404`**: 아직 GitHub Releases에 게시된 release가 없는 상태입니다 (정상). v1.1.0 이상이 게시된 후 사용 가능.
- **`GitHub API 응답 오류` (그 외)**: 네트워크 또는 GitHub 일시적 장애. 잠시 후 재시도.
- **`릴리스에 zip 자산이 없습니다`**: GitHub Releases에 zip이 첨부되지 않은 release. 개발자에게 보고.
