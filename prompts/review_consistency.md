# 형식 일관성 검토 (reviewer subagent, domain=consistency)

표기·약어·기관명·참고문헌·glossary **형식 일관성**을 검토. 내용 정확성·분석 깊이는 tech/market/policy 도메인이 담당하므로 consistency reviewer는 **표기 표준 준수**에만 집중한다. 기준은 `terminology_rules.md`·`abbreviation_rules.md`·`reference_format.md`.

## 검토 대상
- 섹션 HTML (본문)
- 기술 카드 (7블록)
- 프로젝트 카드 (7블록 + 메타)
- 제품 카드 (6블록)
- 별첨 (약어 목록·참고문헌 포함)

## 검토 항목

### 1. 약어 풀이 누락
- 카드 내 첫 등장 약어에 `정식명(ABBR)` 풀이가 있는가 (정착 약어 50선 제외).
- 같은 약어가 1표기(`standard_form`)로 고정됐는가 — `IoT`/`IOT`/`iot` 변형 혼용 금지.

### 2. 기관명 비일관
- 같은 기관이 프로젝트 전체에서 1형태로 표기되는가 (`미국 농무부(USDA)` → 이후 일관).
- 첫 등장 시 `한글 정식명(영문약어)` 형식 준수.

### 3. 외래어 변형
- 국립국어원 표기법 위반 변형(`데이타`·`알고리듬`·영문 slug 단독)이 남아 있는가.
- `outline.glossary` 표준 용어가 본문에 일관 사용되는가.

### 4. 참고문헌 양식 위반
- 말미 목록이 APA 7th 양식인가 (저자 `성, 이니셜.`·연도·제목·출처·DOI).
- 영문/국문 분리·정렬, `[REF-NNN]` ID 부착 여부.
- 본문 인용이 `[REF-xxx]` 형식인가.

### 5. glossary 미준수
- glossary 표준형과 본문 표기가 어긋난 항목.
- glossary가 비어 있으면 WARN (`extract_glossary` 재실행 권장) — FAIL 아님.

## 출력 형식

`review_tech.md`와 **동일 스키마**(`target_id`·`status`·`issues[]`·`revision_instruction`):

```json
{
  "target_id": "1.1.1",
  "target_type": "tech_card",
  "status": "적합" | "보완 필요",
  "issues": [
    {
      "severity": "high" | "medium" | "low",
      "block": "principle",
      "problem": "IoT가 첫 등장인데 풀이 누락. 이후 'IOT' 변형 1회 혼용.",
      "suggestion": "principle 첫 등장에 '사물인터넷(IoT)' 풀이 추가. 'IOT'→'IoT' 표기 통일."
    }
  ],
  "revision_instruction": "약어 IoT 첫 등장 풀이 추가 + 표기 IoT로 통일."
}
```

## 집계 출력
```json
{
  "domain": "consistency",
  "section_reviews": [...],
  "card_reviews": [...],
  "appendix_reviews": [...],
  "overall_score": 8.1,
  "total_issues": 12,
  "high_severity": 1
}
```

## 형식 일관성 체크리스트
- [ ] 약어 첫 등장 풀이 누락 0 (정착 50선 제외)
- [ ] 같은 약어 1표기로 고정 (대소문자 변형 없음)
- [ ] 기관명 프로젝트 내 1형태
- [ ] 외래어 표준안 위반 변형 0
- [ ] 참고문헌 APA 7th 양식 + 영문/국문 분리
- [ ] glossary 표준형과 본문 표기 일치

## 중요 규칙
- **FAIL 게이트 아님**: `status`로 보완 필요만 표시. 실제 수정은 writer가 수행.
- **형식만 검토**: 내용 정확성·분석 깊이는 다른 도메인 소관. 여기서는 표기 표준 준수만 본다.
- **구체적 suggestion**: 어느 블록의 어떤 표기를 무엇으로 바꿀지 명시.
