---
description: 단계 단위 재실행 - research/write/review/render 중 지정 단계부터 다시 실행. 기존 산출물 자동 로드
allowed-tools: Bash, Read, Write, Agent
argument-hint: "--from research|write|review|render [--outline FILE] [-o OUTPUT]"
---

# /techdoc-resume — 단계 단위 재실행

기존 산출물을 자동 감지하고 지정 단계부터 재시작. 파이프라인 중단·크래시 복구용.

## 입력 분석
- `--from STEP` (필수, research | write | review | render)
- `--outline FILE` (옵션, 기본: `$OUTPUT/final_outline.json` 또는 `draft_outline.json`)
- `-o DIR` (기본: `./output`)

## 단계별 재실행 로직

### `--from research`
```
if $OUTPUT_DIR/research_round_*.json 존재:
  삭제 또는 백업 후 재실행
실행: /techdoc-research --outline ...
```

### `--from write`
```
사전 조건: reference_list.json, KeyRef/ 존재 확인
if $OUTPUT_DIR/sections/ 존재:
  기존 section_*.json 백업
  writer_state.json 이어받기 or 초기화
실행: /techdoc-write --outline ... --refs ...
```

### `--from review`
```
사전 조건: document_draft.json 존재
실행: /techdoc-review --input document_draft.json --refs ...
```

### `--from render`
```
사전 조건: document_draft.json 또는 document_final.json 존재
실행: /techdoc-render --input ... --refs ...
```

## 카드 단위 부분 재개 (향후 확장)

writer_state.json을 스캔해 **미완료 카드만** 재작성:
```bash
python -c "
import json
state = json.load(open('$OUTPUT_DIR/writer_state.json', encoding='utf-8'))
failed_cards = []
for sid, ss in state['section_states'].items():
    for c in ss.get('cards', []):
        if c['status'] in ('failed', 'pending'):
            failed_cards.append(c['id'])
print('재작성 대상:', failed_cards)
"
```

발견 시 `/techdoc-rewrite <id>` 연쇄 호출 (또는 자동 반복).

## 자동 감지

재실행할 단계를 명시하지 않으면 `writer_state.json`에서 마지막 상태를 찾아 자동 판단:
- research_round_*.json 없음 → `research`부터
- document_draft.json 없음 → `write`부터
- domain_review.json 없음 → `review`부터 (domain 지정 필요)
- 렌더 출력 없음 → `render`부터

## 백업 정책

단계 재실행 전 기존 파일에 `.resume-bak-<ts>` 접미사 추가:
```bash
mv "$OUTPUT_DIR/research_round_A.json" "$OUTPUT_DIR/research_round_A.resume-bak-$(date +%Y%m%d%H%M).json"
```

## 출력 요약

```
[techdoc-resume 완료]
- 재실행 단계: write
- 복구된 산출물: draft_outline.json, reference_list.json, KeyRef/ (87개)
- 재작성: 72개 카드
- 백업: sections.resume-bak-*, document_draft.resume-bak-*
```
