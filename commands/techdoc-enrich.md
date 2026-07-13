---
description: 카드 서식 소급 개선 - 기존 카드의 내용은 보존하고 리스트·표·시각화·혼용 서식만 개선. writer_state.json 기반
allowed-tools: Bash, Read, Write, Agent
argument-hint: "<card-id> [--all] [-o OUTPUT]"
---

# /techdoc-enrich — 기존 카드 서식 소급 개선 (F25)

이미 작성된 카드의 **내용(사실·수치·[REF-xxx]·논지)은 100% 보존**하고, 서식만 개선한다:

- 병렬·순차 열거(첫째·둘째…)를 **markdown 리스트**로 (F49)
- 서술형/개조식 **혼용** 허용 — 원리는 서술, 항목은 리스트 (F24)
- 텍스트 위주 카드에 **표·그림·mermaid** 추가 권장 (F50 — 본문에 있는 데이터를 표/다이어그램으로 재구성)

`/techdoc-rewrite`의 특수형(서식 전용)이다. 사실 변경·재조사 없음.

## 입력 분석
`$ARGUMENTS` 첫 번째 인자: 카드 ID (예: `1.1` / `A-14.1`). `--all` 지정 시 전체 카드 순회.
- `-o DIR` (기본: `./output`)

## 실행 흐름

### 0. 카드 레이아웃 모드 자동 판별 (rewrite와 동일)

```bash
MODE=$(python -c "from scripts.card_layout import detect_mode; from pathlib import Path; print(detect_mode(Path('$OUTPUT_DIR')))")
echo "Detected card layout mode: $MODE"
```

- `self_model`: `output/cards/<card-id>_card.json` 직접 로드·수정·저장.
- `standard`: `writer_state.json`·`document_draft.json` 경로 (rewrite Step 1~4 재사용).
- `unknown`: rewrite와 동일 안내 후 abort.

### 1. 백업 (rewrite와 동일)

```bash
mkdir -p "$OUTPUT_DIR/cards/_backup"
TS=$(date +%Y%m%d_%H%M%S)
cp "$OUTPUT_DIR/cards/${CARD_ID}_card.json" "$OUTPUT_DIR/cards/_backup/${CARD_ID}_card_${TS}_pre_enrich.json"
```

### 2. Writer subagent 호출 (enrich 모드)

```
[writer-enrich]
모드: enrich (서식 전용)
대상 ID: $CARD_ID
참조 프롬프트: prompts/enrich_card.md + prompts/_shared/card_layout_conventions.md

작업 (엄격 준수):
  - 본문의 사실·수치·기관명·[REF-xxx]·문장 의미를 변경하지 않는다.
  - 병렬/순차 열거를 markdown 리스트(- 또는 1.)로 재구성 (F49).
  - 서술+개조 혼용 (F24) — 원리·해석은 서술 문단, 항목은 리스트.
  - 데이터 문단(수치 비교·분류·절차)은 표 또는 mermaid로 재구성하고 본문으로 해석 (F50).
  - sections dict의 body만 외과적 수정 후 같은 경로에 저장.
```

### 3. 서식 게이트 재검증

```bash
python -m scripts.check_quality "$OUTPUT_DIR/cards" 2>&1 | tail -20
# format_gate: inline_enumeration·visual_density WARNING이 줄었는지 확인
```

## 무손실 검증 (필수)

enrich 전후 본문에서 [REF-xxx] 멀티셋과 핵심 수치 토큰이 **동일**해야 한다. 마커·리스트 재구성·표 변환만 허용, 단어 삭제·추가 0.

```bash
# 백업 대비 REF 멀티셋 동일성 확인 (예시)
python -c "
import json, re, collections
def refs(p): return collections.Counter(re.findall(r'REF-\d{3,}', json.dumps(json.load(open(p, encoding='utf-8')), ensure_ascii=False)))
b = refs('$OUTPUT_DIR/cards/_backup/${CARD_ID}_card_${TS}_pre_enrich.json')
a = refs('$OUTPUT_DIR/cards/${CARD_ID}_card.json')
print('REF 멀티셋 동일:', b == a)
"
```

## 출력 요약

```
[techdoc-enrich 완료]
- 대상: 카드 1.1 (내용 보존, 서식만 개선)
- 변경: 병렬 열거 3곳 → 리스트, 데이터 문단 1곳 → 표
- format_gate: inline_enumeration 3→0, visual_density WARNING 해소
- REF 멀티셋 동일: True (무손실)
- 백업: cards/_backup/1.1_card_..._pre_enrich.json
```
