---
description: TechDoc Plugin을 GitHub Releases 최신 버전으로 갱신 (수동 트리거)
allowed-tools: Bash
argument-hint: "[--check] [--force]"
---

# /techdoc-update — TechDoc Plugin 온라인 업데이트

GitHub Releases(`ystar001/techdoc-plugin`, public)에서 최신 zip을 받아 plugin 디렉토리를 자동 갱신합니다. LLM 호출 없이 결정론적 후처리.

## 옵션

- `--check`: 체크만, 실제 적용 안 함. 새 버전 발견 시 CHANGELOG 미리보기 표시.
- `--force`: 동일 버전이어도 강제 재설치 (디버깅·복구용).
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
- **`GitHub API 응답 오류 status=404`**: 아직 GitHub Releases에 게시된 release가 없는 상태입니다 (정상). v1.1.0 이상이 게시된 후 사용 가능.
- **`GitHub API 응답 오류` (그 외)**: 네트워크 또는 GitHub 일시적 장애. 잠시 후 재시도.
- **`릴리스에 zip 자산이 없습니다`**: GitHub Releases에 zip이 첨부되지 않은 release. 개발자에게 보고.
