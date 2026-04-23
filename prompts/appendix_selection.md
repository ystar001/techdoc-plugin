# 별첨 자동 선정 로직

본문 카드 중에서 **별첨으로 심층분석할 대상 3~7개**를 자동 선정한다.

## 선정 단계

### 1단계: 후보 필터링
- `importance == "high"` 카드만 후보
- `len(ref_ids) >= 3` 조건 (근거 충분성)
- `key_numbers`·`key_metrics` 필드 존재

### 2단계: 스코어링 (4축)
각 후보 카드를 다음 4축으로 점수화 (각 0~10점):

| 축 | 의미 | 측정 |
|---|---|---|
| **ref_count** | 확보된 REF 수 | `len(ref_ids)` / 기대치 정규화 |
| **cross_ref_count** | 여러 섹션 걸친 중요도 | 해당 카드의 기술·프로젝트를 다루는 섹션 수 |
| **key_metrics_count** | 구체 수치 다양성 | `key_numbers` 필드 항목 수 |
| **category_tier** | 소스 카테고리 등급 | 학술·기업R&D > 정부·국제기구 > 뉴스 |

총점 = 4축 평균. 최대 10점.

### 3단계: 상위 N개 선정
- 기본: 점수 상위 **3~7개** (문서 길이 비례)
- 섹션당 1개 이내 (한 섹션에서 2개 이상 별첨 금지)
- 사용자 `--deep-dive-auto N` 옵션으로 N 지정 가능

## 사용자 수동 지정

### 카드 ID 직접 지정
```
/techdoc "제목" --deep-dive-ids "1.1.1,2.3.2"
```

### 이름 검색 지정
```
/techdoc "제목" --deep-dive "LoRa-Mesh,SMART-IRRI-2024"
```

### 생략
```
/techdoc "제목" --no-deep-dive
```

## 별첨 ID 부여 규칙
- 선정 순서대로 `A`, `B`, `C`, ...
- 형식: `부록 A.1`, `부록 B.1` (1은 고정, 단일 블록)
- `source_card_id`: 원본 카드 ID 유지 (예: `1.1.1`)

## 출력 형식
```json
{
  "selected": [
    {"id": "A.1", "source_card_id": "1.1.1", "type": "tech",
     "name": "LoRa-Mesh Precision Irrigation",
     "score": 8.7, "importance": "high",
     "reasons": ["refs=5 (tier1)", "cross-ref in 3 sections", "key_metrics=8"]},
    ...
  ],
  "candidates_total": 12,
  "selected_count": 5
}
```

## 재실행·수정
`/techdoc-deepdive <card_id>` 로 개별 별첨 추가·교체 가능. 자동 선정에서 제외된 카드도 수동으로 별첨화 가능.
