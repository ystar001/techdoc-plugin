# 카드 레이아웃 컨벤션 (writer·rewrite subagent 참조)

plugin은 두 가지 카드 레이아웃을 인정합니다. 어느 쪽을 사용하든 다음 컨벤션을 따르세요.

## Standard 모드 (plugin 기본)

- 카드 = `blocks` dict, 키는 카드 type별 고정:
  - tech 7키: `overview`, `principle`, `components`, `performance`, `pros_cons`, `differentiation`, `references`
  - project 7키: `background`, `organization`, `methodology`, `results`, `implications`, `followup`, `references`
  - product 6키: `background`, `features`, `specifications`, `deployment`, `market`, `references`
- 각 키 값 = HTML fragment 문자열
- `self_check` 필드는 카드 JSON의 최상위에 위치 (Plan A — `SelfCheckResult` 스키마 참조)

## Self-model 모드 (자식 프로젝트가 채택)

`output/cards/<call_id>_card.json` 1파일 = 카드 1개. 카드 = `sections` dict.

### 본문 키 (F1 권장)

**section 객체의 본문은 반드시 `body` 키 단일 사용.** `narrative`·`content`·`blocks` 변형 금지. 변형 혼재는 후속 검증 스크립트(verify_cards.py 등)와 렌더러를 fragile하게 만듭니다.

```json
{
  "sections": {
    "<section_key>": {
      "body": "본문 텍스트 ..."
    }
  }
}
```

### Section 키 (F3 권장)

자식 프로젝트가 6개 섹션 분담 구조를 채택할 때, **다음 표준 키를 권장**합니다 (openfieldtech 사례 기반):

| 키 | 의미 |
|---|---|
| `sec1_definition_scope` | 정의·범위 |
| `sec2_principles` | 원리 |
| `sec3_trends_domestic_global` | 국내외 동향 |
| `sec4_components_methodology` | 구성요소·방법론 |
| `sec5_limitations_challenges` | 한계·도전 |
| `sec6_outlook` | 전망 |

동의 변형(`sec3_trends_international`·`sec3_trends_comparison`·`sec5_limits_challenges` 등)은 같은 의미라도 후속 매칭 코드를 fragile하게 만들므로 피하세요. 프로젝트 내내 일관된 키 1세트만 사용합니다.

### 본문 인라인 메모 금지

자체 검증·메모를 본문 텍스트에 인라인으로 부착하지 마세요 (Plan A — F4). 그런 내용은 카드의 `self_check.notes` 배열로 분리합니다.

## 어느 모드를 사용해야 하나

- plugin의 `/techdoc` 통합 파이프라인을 사용하는 경우 → Standard 모드 (자동).
- 자체 호출 1건 = 카드 1개 패턴을 사용하는 경우 → Self-model 모드 (`/techdoc-rewrite`·`/techdoc-write --single-call`에서 자동 인식).
- 두 모드를 한 프로젝트에서 혼용하지 않습니다. `output/`에 두 모드 산출물이 섞이면 plugin이 standard를 우선합니다 (`scripts.card_layout.detect_mode`).
