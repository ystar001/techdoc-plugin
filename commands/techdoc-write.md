---
description: Step 5 - writer subagent × 3 병렬로 섹션 개요·카드(기술 7·프로젝트 7·제품 6 블록)·종합분석 작성. writer_state.json 카드 단위 resume
allowed-tools: Bash, Read, Write, Agent
argument-hint: "--outline FILE --refs FILE [--style 서술형|개조식] [-o OUTPUT] [--single-call <call_id>]"
---

# /techdoc-write — 섹션 작성 (카드 기반)

3개 writer subagent를 **병렬**로 호출해 섹션을 카드 기반 구조로 작성합니다.

## 입력 분석
`$ARGUMENTS`에서 추출:
- `--outline FILE` (필수, final_outline.json 경로)
- `--refs FILE` (필수, reference_list.json 경로)
- `--style 서술형|개조식` (기본: 서술형)
- `-o DIR` (기본: `./output`)

## 사전 점검

### 1. Outline + RefList 로드 검증
```bash
python -c "
import json
o = json.load(open('$OUTLINE_FILE', encoding='utf-8'))
r = json.load(open('$REFS_FILE', encoding='utf-8'))
print(f'sections={len(o[\"sections\"])}, refs={r[\"total_refs\"]}, usable={r[\"usable_refs\"]}')
"
```

### 2. writer_state.json 초기화
```bash
python -c "
import json
from datetime import datetime
from pathlib import Path
state = {
  'schema_version': '0.1.0',
  'pipeline_started_at': datetime.now().isoformat(),
  'pipeline_updated_at': datetime.now().isoformat(),
  'section_states': {},
  'appendices': [],
  'events': []
}
Path('$OUTPUT_DIR/writer_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
print('writer_state.json initialized')
"
```

### 3. 디자인 CSS 준비
```bash
python -m scripts.select_design --title "$(python -c "import json; print(json.load(open('$OUTLINE_FILE', encoding='utf-8'))['title'])")" --css > "$OUTPUT_DIR/design.css"
```

## 섹션 범위 분할 (researcher와 동일 규칙)

outline 섹션 수에 따라:
- ≤ 3: writer 1개
- 4~6: 2개 (A: 절반, B: 나머지)
- ≥ 7: 3개 (A: 1~4, B: 5~7, C: 8~)

## Writer × 3 병렬 호출 (한 메시지 안에서)

각 subagent 프롬프트:
```
[writer-A]
모드: section
섹션 그룹: A
섹션 ID 목록: ["1.1", "1.2", "1.3", "1.4"]
Outline: ./output/final_outline.json (draft_outline.json 없으면 그것)
ReferenceList: ./output/reference_list.json
Style: 서술형
Glossary: {outline.glossary}
출력 디렉토리: ./output/

참조 프롬프트: prompts/section_write.md, tech_card.md, project_card.md, product_card.md,
              section_analysis.md, card_length_rules.md, tech_depth.md,
              _shared/{citation_rules,style_narrative,analysis_tags,no_ai_inference}.md

작업:
  각 섹션마다 개요 + 기술 카드 3~5 + 프로젝트 카드 2~3 + 제품 카드 1~2 + 종합분석 블록 작성.
  writer_state.json에 카드 단위 이벤트 실시간 기록.
  각 카드 자체 검증 후 미달 시 재작성 (최대 3회).
  출력: ./output/sections/section_<id>.json 파일들
```

## 완료 후 병합

3개 writer가 만든 `sections/section_*.json` 파일들을 하나의 `document_draft.json`으로 병합:

```bash
python -c "
import json
from pathlib import Path
from techdoc_core.models import Document, DocumentSection, TechCard, ProjectCard, ProductCard

section_files = sorted(Path('$OUTPUT_DIR/sections').glob('section_*.json'))
doc = Document(title='', subtitle='', sections=[], tech_cards=[], project_cards=[], product_cards=[])

# TODO: 각 section 파일 파싱 + merge
# writer subagent가 반환한 JSON 포맷에 맞춰 구성
"
```

정확한 병합 로직은 writer subagent가 반환하는 JSON 형식과 일치시켜야 함. 구현 시 fixtures 테스트 필요.

## 진행 모니터링 (선택)

별도 터미널·탭에서:
```
/techdoc-monitor $OUTPUT_DIR
```

메인 세션은 작성 동안 **subagent 완료 대기**. 각 subagent는 writer_state.json에 카드 단위 이벤트 emit.

## 실패 처리

- 카드 3회 재시도 실패 → `writer_state.failed` + `TECHDOC-E030` 기록 → 경고 출력, 계속 진행
- 섹션 전체 실패 → 해당 섹션만 누락 상태로 document_draft.json 저장, 사용자에게 `/techdoc-rewrite` 권장

## 출력 요약

```
[techdoc-write 완료] (12분 08초)
- Writer A (섹션 1~4): 30개 카드, 87,500자
- Writer B (섹션 5~7): 24개 카드, 69,000자
- Writer C (섹션 8~10): 18개 카드, 52,200자
- 총 72개 카드 (기술 38, 프로젝트 22, 제품 12) + 종합분석 10
- 재시도: 카드 1.2.2, 3.1.1 각 2회 → 성공
- 실패: 카드 4.3.2 (3회 재시도 후 최소 분량 미달) — /techdoc-rewrite 권장

파일:
  $OUTPUT_DIR/sections/section_*.json (10개)
  $OUTPUT_DIR/document_draft.json (병합본)
  $OUTPUT_DIR/writer_state.json (이벤트 187건)

다음 단계:
  /techdoc-review --input document_draft.json --domain tech
  (또는 품질만 빠르게) /techdoc-render --input document_draft.json
```

## `--single-call <call_id>` 모드 (F8, v1.1.2+)

자식 프로젝트가 self-model 카드 레이아웃(호출 1건 = 단일 카드 JSON)을 사용할 때, 단일 호출만 재실행할 수 있도록 지원.

### 사용법

```
/techdoc-write --single-call 6.4 --instruction "§3 동향 블록 보강, §5 한계 추가"
```

### 흐름

1. `scripts.card_layout.detect_mode`로 self-model 확인 (writer_state.json 부재 + cards/*_card.json 존재):
   ```bash
   MODE=$(python -c "from scripts.card_layout import detect_mode; from pathlib import Path; print(detect_mode(Path('$OUTPUT_DIR')))")
   ```
2. self-model이 아니면 abort — "이 인자는 self-model 레이아웃 전용입니다"
3. `output/cards/<call_id>_card.json` 로드 (없으면 신규 작성):
   ```bash
   python -c "from scripts.card_layout import load_self_model_card; from pathlib import Path; import json; print(json.dumps(load_self_model_card(Path('$OUTPUT_DIR'), '$CALL_ID')))" 2>/dev/null
   ```
4. writer subagent 1회 호출 (병렬 dispatch 없음). 모드 = `revise` (기존 카드 수정) 또는 `create` (신규).
5. 결과를 같은 경로(`output/cards/<call_id>_card.json`)에 저장.
6. `output/cards/_backup/<call_id>_card_<timestamp>_pre_write.json`에 직전 상태 백업 (있는 경우).

### 주의

이 모드는 plugin core의 writer_state.json·document_draft.json을 건드리지 않습니다. self-model을 채택한 자식 프로젝트의 호환 단편이며, 자체 검증·후속 단계(merge·render)는 자식 프로젝트 책임입니다.

writer subagent는 `prompts/_shared/card_layout_conventions.md`를 참조해 `sections.<key>.body` 단일 키 컨벤션을 따라야 합니다(F1).
