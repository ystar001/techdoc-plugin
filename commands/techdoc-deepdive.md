---
description: 별첨 심층분석 - 카드 ID 지정해 별첨 작성 또는 재작성. researcher 6라운드 + writer appendix 모드 연계
allowed-tools: Bash, Read, Write, Agent
argument-hint: "<card-id> [--instruction \"지시\"] [--skip-research] [-o OUTPUT]"
---

# /techdoc-deepdive — 별첨 심층분석 개별 작성

특정 카드에 대해 **별첨 심층분석**을 생성·재생성. 파이프라인 전체 실행과 무관하게 사후 추가 가능.

## 입력 분석
`$ARGUMENTS` 첫 인자: 원본 카드 ID (예: `1.1.1`) 또는 별첨 ID (예: `A.3`)
- `--instruction "..."` (옵션)
- `--skip-research` (옵션, 기존 research_deepdive_*.json 재사용)
- `-o DIR` (기본: `./output`)

## 실행 흐름

### 1. 카드 타입·메타 확인

```bash
python -c "
import json
doc = json.load(open('$OUTPUT_DIR/document_draft.json', encoding='utf-8'))
target = '$CARD_ID'
card = None
ctype = None
for key, t in [('tech_cards', 'tech'), ('project_cards', 'project')]:
    for c in doc.get(key, []):
        if c['id'] == target:
            card = c
            ctype = t
            break
if not card:
    # 별첨 ID로 들어온 경우 source_card_id 역추적
    for a in doc.get('tech_appendices', []) + doc.get('project_appendices', []):
        if a['id'] == target:
            target = a['source_card_id']
            # card 재검색
if card:
    print(f'target_card: {target}, type: {ctype}, importance: {card[\"importance\"]}')
else:
    print('ERROR: card not found')
"
```

제품 카드(product)는 별첨 대상 아님. tech 또는 project만.

### 2. Researcher 6라운드 (skip 옵션 없으면)

```
[researcher-deepdive]
모드: deepdive
별첨 카드 ID: $CARD_ID
문서 유형: (document metadata에서)
기존 본문 REF: $OUTPUT_DIR/reference_list.json 에서 해당 카드 ref_ids
출력: ./output/research_deepdive_$CARD_ID.json + KeyRef 추가

참조 프롬프트: prompts/research_deepdive.md

작업:
  6a 원문 심화 (5회, WebFetch 필수)
  6b cited-by 추적 (5회)
  6c 저자·기관 프로필 (3회)
  6d 표준·특허 (3회)
  6e 비판·대안 관점 (3회)
  6f 최신성 (선택 3회)
  별첨 전용 REF 20~30건 확보
```

소요 시간: **5~10분** (별첨 하나당).

### 3. Writer 별첨 모드

```
[writer-appendix]
모드: appendix
별첨 대상: {"id": "A.X", "source_card_id": "$CARD_ID", "type": "tech|project", "name": "..."}
별첨 REF: ./output/research_deepdive_$CARD_ID.json + reference_list.json
Style: (document metadata에서)

참조 프롬프트: prompts/appendix_tech.md 또는 appendix_project.md
              + tech_depth.md + _shared/{citation_rules,no_ai_inference,style_*}.md

작업:
  기술 별첨: 10블록, 15k~40k자 (권장 20k~25k)
  프로젝트 별첨: 11블록, 20k~50k자 (권장 25k~30k)
  MathJax 수식, Mermaid 다이어그램, matplotlib 차트 포함
  writer_state.appendices 엔트리 업데이트
  출력: ./output/appendices/appendix_<ID>.json
```

소요 시간: **8~15분** (별첨 하나당).

### 4. Document 업데이트

```bash
python -c "
import json
doc = json.load(open('$OUTPUT_DIR/document_draft.json', encoding='utf-8'))
new_app = json.load(open('$OUTPUT_DIR/appendices/appendix_${APP_ID}.json', encoding='utf-8'))

# tech_appendices 또는 project_appendices에 추가·교체
key = 'tech_appendices' if new_app['type'] == 'tech' else 'project_appendices'
existing = [a for a in doc.get(key, []) if a['id'] == new_app['id']]
if existing:
    idx = doc[key].index(existing[0])
    doc[key][idx] = new_app
else:
    doc.setdefault(key, []).append(new_app)

json.dump(doc, open('$OUTPUT_DIR/document_draft.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
"
```

### 5. 차트·다이어그램 후처리

별첨의 `diagrams` 배열에 ChartGenerator 명세가 있으면:
```bash
python -m scripts.generate_chart \
  --spec "$OUTPUT_DIR/appendices/appendix_${APP_ID}_charts.json" \
  -o "$OUTPUT_DIR/figures/"
```

## 재작성 (별첨 ID 지정)

`/techdoc-deepdive A.1 --skip-research --instruction "벤치마크 블록에 IEEE 802.11ax 추가"`
- 기존 research_deepdive_*.json 재사용
- writer만 appendix 모드로 재호출
- 해당 별첨만 교체

## 출력 요약

```
[techdoc-deepdive 완료] (12분 38초)
- 대상 카드: 1.1.1 (LoRa-Mesh Precision Irrigation, tech, high)
- 생성된 별첨: A.1
- 별첨 분량: 24,512자 (15~35페이지 범위 내)
- 10블록 충족률: 10/10
- 추가 REF: 24건 (전용 수집)
- 시각화: MathJax 수식 3, Mermaid 2, matplotlib 2

파일:
  $OUTPUT_DIR/research_deepdive_1.1.1.json
  $OUTPUT_DIR/appendices/appendix_A.1.json
  $OUTPUT_DIR/document_draft.json (업데이트, tech_appendices에 추가)
```
