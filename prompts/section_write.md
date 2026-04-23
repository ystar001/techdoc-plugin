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
- [ ] 블록 필드 모두 채움 (tech 7 / project 7 / product 6)
- [ ] [REF-xxx] 인용 최소 5건
- [ ] 최소 분량 (중요도별)
- [ ] AI 추정 < 30%

미달 시 해당 카드 재작성 (최대 3회). 그래도 미달이면 `writer_state.failed` 기록 + `TECHDOC-E030`.
