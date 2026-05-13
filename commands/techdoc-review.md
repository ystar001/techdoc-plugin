---
description: Step 8 - reviewer subagent가 도메인별(tech/market/policy) 카드·별첨 검토 후 보완 재작성 오케스트레이션
allowed-tools: Bash, Read, Write, Agent
argument-hint: "--input FILE --refs FILE [--domain tech|market|policy] [-o OUTPUT]"
---

# /techdoc-review — 도메인 전문가 검토 + 보완

reviewer subagent가 판단하고 writer subagent가 외과적으로 수정합니다.

## 입력 분석
- `--input FILE` (필수, document_draft.json 또는 document_final.json)
- `--refs FILE` (필수, reference_list.json)
- `--domain tech|market|policy` (기본: tech)
- `-o DIR` (기본: `./output`)

## 실행 흐름

### 0. Phase A — 결정론적 품질 검사 (v1.1.3+)

domain reviewer 호출 전에 `scripts.check_quality`로 23지표 자동 측정. self-model 카드 레이아웃도 자동 감지(F5+F8 연계).

```bash
python -m scripts.check_quality -i "$OUTPUT_DIR" -o "$OUTPUT_DIR/quality_report.json"
```

산출: `$OUTPUT_DIR/quality_report.json` (mode·overall·total_fail·issues 포함).
exit 2면 FAIL 우선 해소(Phase B 진입 전 `/techdoc-rewrite`로 카드 보강).

### 1. Reviewer 호출 (단일 subagent, 도메인별)

```
[reviewer]
도메인: tech
Document: ./output/document_draft.json
ReferenceList: ./output/reference_list.json
검토 범위: all (섹션·카드·별첨)
출력: ./output/domain_review.json

참조 프롬프트: prompts/review_tech.md, tech_depth.md, _shared/no_ai_inference.md

작업:
  각 섹션·카드·별첨을 도메인 관점에서 평가 (overall_depth_score 0~10).
  보완 필요 항목에 구체적 revision_instruction 작성.
  Cross-phase 테마 (여러 카드 공통 문제) 탐지.
  출력: domain_review.json
```

Reviewer는 **판단만**. 실제 수정은 writer가 수행.

### 2. Review 결과 분석

```bash
python -c "
import json
r = json.load(open('$OUTPUT_DIR/domain_review.json', encoding='utf-8'))
s = r['summary']
print(f'overall: {s[\"overall_score\"]}/10')
print(f'보완 필요: {s[\"status_counts\"].get(\"보완 필요\", 0)}건')
print(f'High severity: {s[\"severity_counts\"].get(\"high\", 0)}건')
"
```

### 3. 보완 대상 선별

`status == "보완 필요"` 이면서 `severity == "high"` 우선. medium·low는 사용자 선택.

### 4. Writer 호출 (revise 모드, 병렬 가능)

high severity 카드 수에 따라 writer 1~3개 호출:

```
[writer-revise]
모드: revise
대상 ID: "1.1.1" (카드 ID) 또는 "A.2" (별첨 ID)
revision_instruction: "principle 블록 400자 추가..."
기존 Document: ./output/document_draft.json
ReferenceList: ./output/reference_list.json

참조 프롬프트: prompts/section_revise.md, tech_card.md (또는 해당 타입)

작업:
  해당 카드·별첨만 수정. 다른 카드는 건드리지 말 것.
  writer_state.json 이벤트 update (attempts 증가).
  변경 사항 summary 반환.
```

### 5. Document 업데이트

writer가 수정한 카드·별첨을 document_draft.json에 merge. 변경 로그 별도 기록.

```bash
# 변경 이력 파일
python -c "
import json
from datetime import datetime
log = {'ts': datetime.now().isoformat(), 'domain': '$DOMAIN', 'revisions': [...]}
open('$OUTPUT_DIR/revision_log.json', 'a', encoding='utf-8').write(json.dumps(log, ensure_ascii=False) + '\n')
"
```

## 도메인 여러 개 실행

tech + market + policy 모두 받으려면:
```
/techdoc-review --input ... --domain tech
/techdoc-review --input ... --domain market
/techdoc-review --input ... --domain policy
```

각각 domain_review_{tech,market,policy}.json에 저장.

## Low severity 처리

기본: 무시 (사용자에게 보고만).
`--apply-low` 플래그 시 모두 반영.

## 출력 요약

```
[techdoc-review 완료] (5분 32초)
- 도메인: tech
- 검토 카드: 72개, 별첨 5개
- 전체 점수: 7.4/10
- 보완 필요: 11건 (high 3, medium 6, low 2)
- 재작성 적용: 9건 (high 3 + medium 6)
- 저수준 2건: 미적용 (--apply-low 로 강제)
- Cross-phase 테마: "프로젝트 카드 meta 헤더 누락 3건" (researcher 재조사 권장)

파일:
  $OUTPUT_DIR/domain_review.json
  $OUTPUT_DIR/document_draft.json (업데이트)
  $OUTPUT_DIR/revision_log.jsonl

다음 단계:
  최종 검증: python -m scripts.check_quality --input document_draft.json
  렌더링: /techdoc-render --input document_draft.json
```
