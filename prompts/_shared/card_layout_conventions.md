# 카드 레이아웃 컨벤션 (writer·rewrite subagent 참조)

plugin은 두 가지 카드 레이아웃을 인정합니다. 어느 쪽을 사용하든 다음 컨벤션을 따르세요.

## Standard 모드 (plugin 기본)

- 카드 = `blocks` dict, 키는 카드 type별 고정:
  - tech 7키: `overview`, `principle`, `components`, `performance`, `pros_cons`, `differentiation`, `references`
  - project 7키: `background`, `organization`, `methodology`, `results`, `implications`, `followup`, `references`
  - product 6키: `background`, `features`, `specifications`, `deployment`, `market`, `references`
- 각 키 값 = HTML fragment 문자열
- `self_check` 필드는 카드 JSON의 최상위에 위치 (Plan A — `SelfCheckResult` 스키마 참조)

## Self-model 모드 (자식 프로젝트, v0.2.0 엄격 표준)

`output/cards/<card_id>_card.json` 1파일 = 카드 1개. 카드 = `sections` dict.
구 0.1.0 카드는 `python -m scripts.migrate output/`로 0.2.0 변환 후 사용한다.

### 카드 식별자 (F13 — 강제)

- `card_id`: split marker 포함 단일 식별자 (예: `A-14.1.L1`, `D1.L2`).
- `parent_id`: 부모·시리즈 ID (예: `14.1`). split 없는 카드는 빈 문자열.
- 구 `section_id`/`appendix_id` 이중 필드는 금지 — migrate가 통합한다.

### 제목 (F14 — 강제)

- `title`: 정제된 학술 제목만 (`농업 데이터 표준`).
- `split_summary`: 운영 미주(`분할 1/3`·`§1~§3`·`(L1, 10p)`)는 이 필드로 분리. 본 제목에 인라인 금지.

### 섹션 키 (F3 — 강제: 위치만)

- 섹션 키는 **위치만** `sec1`~`sec6`. 서술명·동의 변형(`sec3_trends_international` 등) 금지.
- 서술 헤딩은 각 섹션의 `title` 필드에 (위치 기본값: sec1 정의·범위 / sec2 원리·구조 / sec3 국내외 동향 / sec4 구성요소·방법론 / sec5 한계·도전 / sec6 전망).

```json
{
  "card_id": "A-14.1.L1",
  "parent_id": "14.1",
  "title": "농업 데이터 표준",
  "split_summary": "분할 1/3",
  "sections": {
    "sec1": {"title": "정의·범위", "body": "본문 ..."},
    "sec3": {"title": "국내외 동향", "body": "본문 ..."}
  }
}
```

### 본문 키 (F1 — 강제)

- 각 섹션 본문은 단일 `body` 키. `narrative`·`content`·`blocks` 변형 금지(migrate가 흡수).

### 본문 인라인 메모 금지 (F4)

- 자체 검증·운영 메모를 본문에 인라인 부착 금지. `self_check.notes` 배열로 분리.

## 어느 모드를 사용해야 하나

- plugin의 `/techdoc` 통합 파이프라인을 사용하는 경우 → Standard 모드 (자동).
- 자체 호출 1건 = 카드 1개 패턴을 사용하는 경우 → Self-model 모드 (v0.2.0 엄격 표준 — 위 규약 준수, `/techdoc-rewrite`·`/techdoc-write --single-call`에서 자동 인식).
- 두 모드를 한 프로젝트에서 혼용하지 않습니다. `output/`에 두 모드 산출물이 섞이면 plugin이 standard를 우선합니다 (`scripts.card_layout.detect_mode`).
