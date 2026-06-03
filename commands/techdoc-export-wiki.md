---
description: TechDoc 보고서 산출물을 옵시디언 vault로 변환·누적 (LLM 호출 0회, D 하이브리드)
allowed-tools: Bash
argument-hint: "--vault <경로> [--doc <output>] [--create-vault] [--lint] [--no-enhance]"
---

# /techdoc-export-wiki — Obsidian/MkDocs LLM Wiki 변환

`document_final.json` + `KeyRef/` + `figures/` + outline glossary를 표준 마크다운 wiki로 변환·누적합니다. 같은 vault에 여러 보고서를 누적하면 엔티티별 페이지가 시간이 갈수록 풍부해집니다.

**D 하이브리드 호환**: 옵시디언·VS Code·Cursor·Logseq·Foam·Dendron·MkDocs Material·Docusaurus·Hugo·Jekyll·GitHub/GitLab 마크다운 뷰어 모두 동작.

## 옵션

- `--vault <경로>` (필수) — vault 디렉토리.
- `--doc <output>` (선택) — 보고서 출력 디렉토리. 기본값: 현재 디렉토리.
- `--create-vault` (선택) — vault가 없으면 신규 생성.
- `--lint` (선택) — vault 점검만 수행 (충돌 callout 잔존·끊어진 링크).
- `--enhance` / `--no-enhance` (선택, 기본 on) — 카드 .md 후처리: "학술" 과잉 수식어 정리·메타 표시(`(확장)`·`(보강)`) 제거·긴 문단 분리·영문 slug 부분 한국어화·문서 안내 섹션. `[REF-xxx]`·수치·고유명사는 보존. AI 마커 영역만 적용(사용자 메모 무손상). `--no-enhance`로 비활성 (F18).

## 실행

```bash
cd "$CLAUDE_PROJECT_DIR" && python -m scripts.export_wiki $ARGUMENTS
```

## 산출

vault 안에 다음 카테고리별 페이지가 생성·갱신됩니다.

- `Sources/REF-*.md` — 참고문헌 (KeyRef 원문 임베드)
- `Tech/<name>.md`, `Tech/<name>_appendix.md` (별첨 시)
- `Projects/<name>.md`, `Projects/<name>_appendix.md` (별첨 시)
- `Products/<name>.md`
- `Concepts/<term>.md`
- `Reports/<title>.md` (MOC)
- `Assets/figures/<report>/` — 차트 복사
- `index.md`, `log.md` (자동 갱신)

또한 `<output>/wiki_export_report.json`에 신규/갱신/충돌 통계 기록.

## 정책

- **LLM 호출 0회** (결정론적 변환).
- **사용자 메모 보존**: `<!-- techdoc:auto-* -->` 마커 외부는 절대 손대지 않음.
- **충돌 감지**: 같은 엔티티의 핵심 사실(연도·수치·기관) 충돌 시 callout 자동 추가.
- **멱등성**: 같은 입력으로 두 번 실행 시 vault 상태 동일.
- **링크 형식**: 본문 표준 마크다운 `[text](path.md)`, frontmatter wiki-style `[[X]]` 유지 (옵시디언 Dataview 호환).

## 트러블슈팅

- **`vault 디렉토리가 없습니다`**: `--create-vault` 추가하거나 사전 mkdir.
- **`document_final.json을 찾을 수 없습니다`**: `--doc` 인자 확인 또는 `/techdoc` 미완료.
- **충돌 callout 빈번**: 같은 엔티티가 보고서마다 다른 수치를 가진 정상 변동. 사용자가 수동 정리 후 다음 export 시 사라짐.
