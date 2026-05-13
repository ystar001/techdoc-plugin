---
description: TechDoc 보고서를 Notion 워크스페이스로 publish. 페이지 계층 + KeyRef inline database. delta sync.
allowed-tools: Bash, Read
argument-hint: "--parent-page <id> [--doc <dir>] [--dry-run] [--force] [--archive-stale|--no-archive-stale]"
---

# /techdoc-export-notion — Notion publish

TechDoc 보고서 산출물을 Notion 워크스페이스로 push. mode 자동 판별(standard·self_model). idempotent — 동일 명령 재실행 시 변경분만 sync.

## 사전 준비 (최초 1회)

1. **Notion integration 생성**: https://www.notion.so/my-integrations → "New integration" → token 발급.
2. **환경 변수 설정**: `export NOTION_TOKEN=secret_xxx` (또는 OS keychain·.env).
3. **parent page 권한**: 보고서를 둘 부모 페이지에서 `...` 메뉴 → "Add connections" → 위에서 만든 integration 추가.
4. **parent page ID**: Notion에서 페이지 URL 끝의 32자 hex (예: `2f1a9b8c4d5e6f7a8b9c0d1e2f3a4b5c`).

## 실행

```bash
export NOTION_TOKEN=secret_xxx
/techdoc-export-notion --parent-page 2f1a9b8c4d5e6f7a8b9c0d1e2f3a4b5c
```

내부적으로 `python -m scripts.export_notion --doc ./output --parent-page <id>` 호출.

## 인자

| 인자 | 기본값 | 효과 |
|---|---|---|
| `--parent-page <id>` | 필수 | Notion 부모 페이지 UUID. |
| `--doc <dir>` | `./output` | 보고서 디렉토리 (mode 자동 판별). |
| `--dry-run` | off | 실제 API 호출 없이 변경 예정 항목 수만 출력. |
| `--force` | off | hash 비교 skip, 모든 페이지 강제 update. |
| `--archive-stale` | on | 이전 state에 있던 stale 항목 archive. `--no-archive-stale`로 해제. |

## 종료 코드

- `0`: 성공.
- `1`: 인증·권한·네트워크 일반 오류.
- `2`: 부분 성공 (state 일부 저장됨, 재실행으로 재개).

## 재실행 흐름

매 호출:

1. `output/notion_state.json` 로드 (parent_page_id 검증).
2. 카드 레이아웃 mode 자동 판별 (`scripts.card_layout.detect_mode`).
3. parent page 권한 사전 점검 (`notion/preflight`).
4. 섹션·별첨·KeyRef의 content hash 비교 → 변경분만 API 호출.
5. stale 항목 archive (default).
6. state 저장 (last_pushed_at 갱신).

## 충돌 대응

- **Notion 측 수동 편집은 덮어쓰여짐** (v1.2.0 단방향). 협업은 코멘트·제안 모드로.
- **parent page 변경 시도** → state 불일치로 abort. `notion_state.json` 삭제 후 새로 push 또는 Notion에서 수동 이동.

상세는 spec `docs/superpowers/specs/2026-05-13-notion-push-integration-design.md` 참조.
