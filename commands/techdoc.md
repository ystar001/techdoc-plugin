---
description: TechDoc 통합 파이프라인 - 목차→조사→작성→검토→별첨→렌더링. 60~130분, 본문 100~150p + 별첨 85~175p
allowed-tools: Bash, Read, Write, Agent
argument-hint: "<제목> [--toc FILE] [--mode exact|enhance] [--outline FILE] [--domain tech|market|policy] [--style 서술형|개조식] [--depth quick|standard|deep] [--ref file:|url:|site:] [--deep-dive IDs] [--no-deep-dive] [-o OUTPUT] [--export-wiki <vault>] [--push-notion <parent_page_id>]"
---

# /techdoc — 전체 파이프라인 통합 실행

목차·조사·작성·검토·별첨·렌더링 전 단계 순차 실행. 13단계 중 조건에 맞게 호출.

## 입력 분석

`$ARGUMENTS`에서 추출:

**필수**:
- 제목 (첫 번째 positional)

**옵션**:
- `--toc FILE` — 사용자 목차 파일
- `--mode exact|enhance` — 목차 모드 (기본: exact)
- `--outline FILE` — 기존 outline JSON 사용 (목차 단계 스킵)
- `--domain tech|market|policy` — 도메인 검토
- `--style 서술형|개조식` — 기본 서술형
- `--depth quick|standard|deep` — 검색 깊이 (기본: standard)
- `--ref file:path | url:URL | site:URL` — 사용자 참고자료 (다중 가능)
- `--deep-dive "이름1,이름2"` — 별첨 수동 지정
- `--deep-dive-ids "1.1.1,2.3.2"` — 카드 ID로 별첨 지정
- `--deep-dive-auto N` — 자동 선정 개수
- `--no-deep-dive` — 별첨 생략
- `-o DIR` — 출력 디렉토리 (기본: `./output`)
- `--export-wiki <vault>` — 렌더링 완료 후 vault에 LLM Wiki 자동 export (D 하이브리드: 옵시디언·MkDocs·표준 마크다운 호환). `/techdoc-export-wiki --doc <output> --vault <vault> --create-vault`를 마지막 Step으로 자동 호출.
- `--push-notion <parent_page_id>` — 렌더링 완료 후 Notion 워크스페이스로 자동 publish. `NOTION_TOKEN` 환경 변수 필수. `/techdoc-export-notion --parent-page <id>`를 마지막 Step으로 자동 호출.

## 실행 흐름 (사용자 확인 포인트 포함)

### Phase 1: 환경 진단 (선택, 처음 실행 시 권장)
```bash
python -m scripts.doctor
# FAIL 있으면 중단, 사용자에게 수정 안내
```

### Phase 2: 목차 구조
```
if --outline 제공됨:
  outline_path = $OUTLINE
else:
  /techdoc-outline "제목" [옵션]
  outline_path = $OUTPUT/draft_outline.json

사용자 확인 포인트: outline 보여주고 "계속 진행? [Y/n]" (기본 Y)
```

### Phase 3: 자료 조사 (5~8분)
```
/techdoc-research --outline "$outline_path" [옵션]
산출: reference_list.json, KeyRef/*.md
```

카테고리 비율 미달 시 경고만, 계속 진행 (aspirational).

### Phase 4: 섹션 작성 (10~15분)
```
/techdoc-write --outline ... --refs ... [--style 서술형]
산출: document_draft.json (카드 포함)
writer_state.json 실시간 이벤트
```

### Phase 5: 도메인 검토 + 보완 (선택, 5~8분)
```
if --domain 제공됨:
  /techdoc-review --input document_draft.json --refs ... --domain tech
  high severity 자동 보완
```

### Phase 6: 별첨 심층분석 (20~30분)
```
if --no-deep-dive 아니면:
  별첨 대상 선정:
    --deep-dive-ids 제공: 해당 카드들
    --deep-dive 이름: 이름 매칭
    자동 (기본): prompts/appendix_selection.md 로직 (high importance 3~7개)

  각 별첨에 대해 (3개씩 병렬):
    /techdoc-deepdive <card_id>
```

### Phase 7: 최종 품질 검증
```bash
python -m scripts.check_quality \
  --input "$OUTPUT/document_draft.json" \
  --refs "$OUTPUT/reference_list.json" \
  -o "$OUTPUT/quality_report.json"
```

FAIL 있으면 사용자에게 보고 + `/techdoc-rewrite` 권장.

### Phase 8: 렌더링
```
document_draft.json → document_final.json 승격 (rename/copy)
/techdoc-render --input document_final.json --refs ... --formats html,pdf,docx,md
```

### Phase 9: Wiki export (선택, `--export-wiki <vault>` 제공 시)

```bash
/techdoc-export-wiki --doc "$OUTPUT_DIR" --vault "$VAULT_PATH" --create-vault
```

### Phase 10: Notion publish (선택, `--push-notion <id>` 제공 시)

`--push-notion <parent_page_id>` 인자가 있으면 보고서 생성 완료 후 자동으로:

```bash
python -m scripts.export_notion --doc "$OUTPUT_DIR" --parent-page "$NOTION_PARENT_PAGE"
```

`NOTION_TOKEN` 환경 변수 필수. 미설정 시 경고 출력 후 보고서 산출은 유지 (Notion push만 skip).

이 단계는 `/techdoc-export-notion` 단독 호출과 동등 — 사용자는 둘 다 가능.

## 단계 간 사용자 확인 (기본 ON)

각 Phase 종료 시 요약 표시 후 "계속? [Y/n/s(skip next)/a(all auto)]":
- `Y` (기본): 다음 단계 진입
- `n`: 중단, 사용자 검토 후 `/techdoc-resume --from <next>`로 재개
- `s`: 다음 단계 skip
- `a`: 이후 모든 단계 자동 진행

`--auto` 플래그로 처음부터 모든 확인 skip 가능.

## 예상 실행 시간

| depth | 별첨 | 총 시간 |
|---|---|---|
| quick | 없음 | 15~25분 |
| standard | 없음 | 40~60분 |
| standard | 3~7개 (기본) | **60~130분** |
| deep | 5~7개 | 100~180분 |

## 실패·중단 시

- 각 Phase 종료 후 writer_state.json 상태 저장
- 중단 시 `/techdoc-resume --from <phase>` 로 재개
- 개별 카드 실패 → 전체 중단 없이 기록 후 계속, 최종에 `/techdoc-rewrite` 권장

## 출력 요약

파이프라인 전 단계 완료 시 최종 요약:

```
[techdoc 전체 완료] (87분 42초)

목차: 10섹션, 42 subtopics, glossary 14개
자료: REF 145건 (본문 92 + 별첨 53)
  - 카테고리: 학술 34, 기업R&D 22, 연구기관 18, 기타 71
  - 해외 비율: 53%
작성: 72 카드 (기술 38, 프로젝트 22, 제품 12) + 종합분석 10
검토: tech 도메인, overall 7.4/10, 보완 9건 (자동 적용)
별첨: 5개 (기술 3 + 프로젝트 2)
  - 평균 분량: 24,800자 (권장 범위)
  - 블록 충족률: 평균 96%
차트: 28개 (본문 10 + 별첨 18)
품질: overall 4.3/5.0, FAIL 0, WARN 3

출력:
  스마트농업기술보고서_202604231430.html (2.1 MB, 287페이지)
  스마트농업기술보고서_202604231430.pdf  (7.8 MB)
  스마트농업기술보고서_202604231430.docx (3.4 MB)
  스마트농업기술보고서_202604231430.md   (518 KB)

특정 카드 재작성: /techdoc-rewrite <id>
별첨 추가·재작성: /techdoc-deepdive <card-id>
```

## 개별 명령으로 단계 호출

사용자가 원하면 단일 통합 명령 대신 단계별 명령 직접 호출 가능:
- `/techdoc-outline` → `/techdoc-research` → `/techdoc-write` → `/techdoc-review` → `/techdoc-deepdive ... ` → `/techdoc-render`

통합 명령은 이들을 순차 연결한 편의 래퍼입니다.
