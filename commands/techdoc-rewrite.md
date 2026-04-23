---
description: 카드 단위 재실행 - 특정 카드 하나만 재작성. 다른 카드는 보존. writer_state.json 기반
allowed-tools: Bash, Read, Write, Agent
argument-hint: "<card-id> [--instruction \"지시문\"] [--refs REF_IDS] [-o OUTPUT]"
---

# /techdoc-rewrite — 카드 단위 재실행

특정 카드 하나 또는 별첨 하나만 다시 작성. 다른 카드는 **그대로 유지**.

## 입력 분석
`$ARGUMENTS` 첫 번째 인자: 카드 ID (예: `1.1.1`) 또는 별첨 ID (예: `A.1`)
- `--instruction "..."` (옵션, 추가 지시)
- `--refs REF-023,REF-041` (옵션, 참조 REF 교체·추가)
- `-o DIR` (기본: `./output`)

## 실행 흐름

### 1. ID 유효성 확인

`writer_state.json`에서 대상 카드 존재 여부 검증:
```bash
python -c "
import json, sys
state = json.load(open('$OUTPUT_DIR/writer_state.json', encoding='utf-8'))
target = '$CARD_ID'
found = False
for sid, ss in state['section_states'].items():
    for c in ss.get('cards', []):
        if c['id'] == target:
            print(f'Found: section={sid}, type={c[\"type\"]}, current_status={c[\"status\"]}')
            found = True
            break
    if found: break
for a in state.get('appendices', []):
    if a['id'] == target:
        print(f'Found appendix: source={a[\"source_card_id\"]}')
        found = True
if not found:
    print(f'ERROR: {target} not found', file=sys.stderr)
    sys.exit(1)
"
```

### 2. 현재 카드 백업

```bash
mkdir -p "$OUTPUT_DIR/backups"
TS=$(date +%Y%m%d%H%M)
python -c "
import json, shutil
# 현재 카드 JSON 추출 → backup
..." > "$OUTPUT_DIR/backups/card_${CARD_ID}_${TS}.json"
```

### 3. Writer subagent 호출 (revise 모드)

```
[writer-rewrite]
모드: revise
대상 ID: $CARD_ID
revision_instruction: "${INSTRUCTION:-사용자가 지정한 카드를 완전히 새로 작성}"
참조 REF: ${REFS:-기존 ref_ids 그대로}
기존 Document: ./output/document_draft.json
ReferenceList: ./output/reference_list.json

참조 프롬프트: prompts/section_revise.md + 카드 타입별 템플릿

작업:
  해당 카드만 재작성. 기존 블록 구조 유지.
  --refs 제공 시 ref_ids 교체·병합.
  writer_state.json 이벤트 append (attempts +1).
  변경 summary 반환.
```

### 4. Document 업데이트

writer가 반환한 새 카드 JSON으로 document_draft.json 해당 카드 교체:

```bash
python -c "
import json
doc = json.load(open('$OUTPUT_DIR/document_draft.json', encoding='utf-8'))
new_card = json.load(open('$OUTPUT_DIR/sections/card_${CARD_ID}_new.json', encoding='utf-8'))

# tech_cards/project_cards/product_cards 중 해당 ID 찾아 교체
for key in ('tech_cards', 'project_cards', 'product_cards'):
    for i, c in enumerate(doc.get(key, [])):
        if c['id'] == '$CARD_ID':
            doc[key][i] = new_card
            print(f'Replaced in {key}[{i}]')
            break

json.dump(doc, open('$OUTPUT_DIR/document_draft.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
"
```

### 5. 품질 재검증 (선택)

```bash
python -m scripts.check_quality \
  --input "$OUTPUT_DIR/document_draft.json" \
  --refs "$OUTPUT_DIR/reference_list.json" \
  -o "$OUTPUT_DIR/quality_report_after_rewrite.json"
```

## 롤백

`/techdoc-rewrite 1.1.1 --rollback`:
- `$OUTPUT_DIR/backups/card_1.1.1_*.json` 중 최신 버전으로 복원
- writer_state.json 이벤트 에러 로그

## 출력 요약

```
[techdoc-rewrite 완료]
- 대상: 카드 1.1.1 (tech, importance=high)
- 이전 분량: 2,847자 → 신규: 3,120자
- 변경: principle 블록 확대, 신규 REF [REF-102] 추가
- 품질 재검증: overall 7.4 → 7.8 (↑0.4)
- 백업: backups/card_1.1.1_202604231530.json

다른 카드는 그대로 보존됨. document_draft.json 갱신 완료.
```
