# 섹션 작성 지시 (writer subagent, 카드 기반)

writer subagent가 받는 핵심 프롬프트. 섹션 하나를 **개요 + 카드 + 종합분석 블록** 순서로 작성.

## 입력
- **섹션 정보**: id, title, subtopics, analysis_tags, estimated_length
- **매핑된 REF**: 해당 섹션 related_sections에 포함된 KeyRef 목록
- **카드 대상**: KeyRef의 technologies/projects/products 중 importance ≥ medium
- **디자인 컴포넌트**: 13종 + 카드 3종 + 별첨 2종 = 18종
- **glossary**: 용어 사전
- **이전 섹션 요약**: 연결성 유지용

## 작성 순서 (카드 기반)

### Step A: 섹션 개요 문단 (100~200자)
섹션이 다룰 기술·프로젝트·제품의 **지도**를 먼저 제시.
```html
<section id="section-1.1">
  <h2>1.1 관개 자동화 시스템</h2>
  <p class="section-overview">
    본 섹션은 정밀농업의 핵심 인프라인 관개 자동화 시스템을 다룬다.
    LoRa-Mesh 기반 분산 제어, AI 물수요 예측, 태양광 IoT 통합 3가지 핵심 기술과
    MIT CSAIL의 SMART-IRRI-2024, 농진청 AI관개 실증사업 2개 대표 프로젝트,
    그리고 상용 제품 AgriLink X2를 순차적으로 살펴본다.
  </p>
```

### Step B: 기술 카드 3~5개 (병렬 작성 가능)
`prompts/tech_card.md` 템플릿 따라 카드 HTML 생성.
중요도별 분량 적용 (`prompts/card_length_rules.md`).

### Step C: 프로젝트 카드 2~3개
`prompts/project_card.md` 템플릿.

### Step D: 제품 카드 1~2개
`prompts/product_card.md` 템플릿.

### Step E: 종합 분석 블록
`prompts/section_analysis.md` 템플릿.
- 비교 매트릭스
- 타임라인
- 차트 명세 JSON (ChartGenerator 전달)
- 섹션 요약 (section-summary 컴포넌트)

### Step F: 섹션 HTML 조립
순서: 개요 → 기술 카드 → 프로젝트 카드 → 제품 카드 → 종합 분석

### Step G: 표기 일관성 검증
조립한 섹션에 표기 표준을 적용·점검한다. 상세 규칙은 신설 3종 프롬프트 참조:
- `prompts/terminology_rules.md` — 학술용어·약어·기관명·제품명·외래어·단위·표현부호 7항.
- `prompts/abbreviation_rules.md` — 약어 첫 등장 풀이·정착 약어 50선·`standard_form` 1표기.
- `prompts/reference_format.md` — 말미 참고문헌 APA 7th 양식.

점검 항목:
- `outline.glossary` 표준 용어가 본문에 **일관 사용**되는지(변형 표기 없음).
- 약어 첫 등장 풀이 누락 없는지, 같은 약어 1표기로 고정됐는지.
- 기관명·외래어 변형 혼용 없는지(`데이타`/`데이터` 등).
- 단위·표현부호(`94.3%`·`~`·`·`) 일관.
- glossary가 비면 카드 내 풀이로 보완하고, `extract_glossary` 재실행을 권장.

## 공통 규칙 (모든 카드)
- 인용: `prompts/_shared/citation_rules.md`
- 문체: `prompts/_shared/style_narrative.md` 또는 `style_bullet.md`
- 분석 관점: 섹션의 `analysis_tags` 반영
- AI 추론 차단: `prompts/_shared/no_ai_inference.md`
- 용어 통일: glossary 사용

## KeyRef 직접 인용 (핵심)
KeyRef의 구조화 데이터를 **그대로 본문에 삽입**:
- `key_numbers` → 정량 수치로 인용
- `projects[].institution/pi/period/budget` → 프로젝트 카드 메타 헤더
- `products[].maker/deployed_at/price_range` → 제품 카드

## 출력
각 카드는 독립 JSON 객체. 섹션 HTML은 카드 HTML들을 조합.
```json
{
  "section_id": "1.1",
  "overview_html": "<section>...",
  "tech_cards": [{...}, {...}],
  "project_cards": [{...}],
  "product_cards": [{...}],
  "analysis_html": "<section class='section-analysis'>..."
}
```

## writer_state.json 업데이트
카드 시작/완료마다 이벤트 emit + 상태 기록:
```json
{"ts": "...", "section": "1.1", "card": "1.1.1", "state": "writing", "chars": "1200/2500"}
{"ts": "...", "section": "1.1", "card": "1.1.1", "state": "completed", "chars": "2847", "elapsed_s": 82.3}
```

## 자체 검증 (카드별)

검증 결과는 **카드 JSON의 `self_check` 필드 1곳에만 기록**한다. 본문(`body`·`narrative`·`content`·`blocks`) 텍스트 안에 "AI 추정 표현 0%", "자가진단", "[REF-xxx] N건 이상 확인" 같은 자체 검증 메모를 **인라인으로 부착하지 말 것**. 사이즈(S·L1·L2·L3) 무관하게 동일한 키를 사용한다.

### F11 — 운영 메타·시그너처 본문 인라인 금지

다음 시그너처는 **본문 어디에도 인라인 금지**. 자체 검증·운영 메타는 `self_check`(writer) 또는 `self_review`(reviewer 메타) 필드로만 기록한다. 본문은 독자를 향한 기술·연구·제품 서술만 담는다.

- **"학술" 과잉 수식어 반복**: `학술 프레임워크`·`학술 baseline`·`학술 심층 분석`·`학술 정의`·`학술 시리즈` 류. → `프레임워크`·`기준선`·`심층 분석`·`정의`로 쓰고 근거는 `[REF-xxx]`로 표시.
- **"1발 PASS·풀 단조·압축 0회" 류 운영 목표**: `1발 PASS`·`풀 단조 100%`·`압축 0회`·`자가검증 N건`·`AI 추정 0%` 같은 작성 공정 지표.
- **"PRD §REQ-xxx 정합" 류 메타**: `PRD §REQ-012 정합`·`요구사항 충족`·`(보강)`·`(re-write)`·`(분할 N/M)` 같은 작업 상태·요구사항 추적 표시.
- **"본 풀 N건 전수 인용" 류 정책 메모**: `본 풀 38건 전수 인용`·`전 REF 소진`·`인용 풀 100% 활용` 같은 인용 정책 자기 보고.

위 내용이 필요하면 `self_check.notes`(writer) 또는 reviewer의 `self_review` 메타로만 기록하고, 본문 텍스트에서는 제거한다.

검증 항목:
- `blocks_filled` (bool): tech 7 / project 7 / product 6 블록을 모두 채웠는가
- `refs_count` (int): [REF-xxx] 인용 건수 (최소 5건 권장)
- `min_length_ok` (bool): 카드 사이즈별 최소 분량 충족
- `ai_inference_below_threshold` (bool): AI 추정 표현 < 30%
- `no_unverified_markers` (bool): 본문에 [근거 미확인] 잔존 없음
- `notes` (list[str]): 자유 메모 (선택). 본문과 반드시 분리.

출력 예 (카드 JSON 끝에 부착):

```json
{
  "id": "1.1.1",
  "type": "tech",
  "name": "LoRa-Mesh",
  "blocks": { "...": "..." },
  "self_check": {
    "blocks_filled": true,
    "refs_count": 6,
    "min_length_ok": true,
    "ai_inference_below_threshold": true,
    "no_unverified_markers": true,
    "notes": []
  }
}
```

미달 시 해당 카드 재작성 (최대 3회). 그래도 미달이면 `writer_state.failed` 기록 + `TECHDOC-E030`. `self_check` 자체가 누락된 카드는 WARN 처리(역호환 — 기존 카드 호환 유지).
