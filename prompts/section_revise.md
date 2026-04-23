# 섹션·카드 보완 재작성 지시

reviewer subagent가 지적한 보완 지시 또는 quality_checker의 FAIL 섹션·카드를 **수정**한다.

## 입력
- **원본 콘텐츠**: 기존 섹션 HTML 또는 카드 JSON
- **revision_instruction**: 구체적 지적 사항
- **매핑된 REF**: 해당 단위에 사용 가능한 KeyRef
- **context**: 섹션의 analysis_tags, importance, glossary

## 핵심 원칙
**기존 내용 최대한 유지 + 지적된 부분만 수정**.
전면 재작성 ❌. 외과적 수정 ✓.

## 수정 우선순위

### 1. 근거 보강
- 수치 누락 → [REF-xxx] 출처와 함께 추가
- "근거 미확인" → 실제 REF로 교체 또는 삭제
- AI 추정 표현 → 구체 출처 기반 서술로

### 2. 분량 확대
- 카드·블록 최소 분량 미달 → 해당 블록만 확장
- 다른 블록·카드는 건드리지 말 것

### 3. 구조 보완
- 누락된 블록 추가 (예: 기술 카드에 ⑥ 차별점 블록 비어있음)
- 카드 메타 헤더 (project_card의 institution/pi/period)

### 4. 용어 통일
- glossary와 불일치 → 표준 용어로 교체

### 5. 문체 교정
- 서술형 ↔ 개조식 혼재 → 지정 스타일로 통일
- 구어체·감탄 제거

## 출력 형식

### 섹션 레벨 수정
이전 HTML + 수정된 섹션 HTML (diff 아님 — 전체 교체).
```json
{
  "section_id": "1.1",
  "revised_html": "<section>...",
  "change_summary": ["기술 카드 1.1.1에 수치 3건 추가", "AI 추정 2곳 제거"]
}
```

### 카드 레벨 수정
원본 카드 JSON에 변경된 블록만 덮어쓰기.
```json
{
  "card_id": "1.1.1",
  "type": "tech",
  "updated_blocks": {
    "performance": "<p>정확도 94.3% [REF-023]...",
    "pros_cons": "..."
  },
  "change_summary": ["성능 블록 수치 보강", "장단점 블록 구조화"]
}
```

## 재시도 정책
- 카드 단위: 최대 3회 (`writer.attempts`)
- 섹션 단위: 최대 1회
- 3회 초과 시 `TECHDOC-E030` 기록, 사용자 개입 필요 (`/techdoc-rewrite`)

## writer_state.json 이벤트
```json
{"ts": "...", "card": "1.1.1", "state": "retrying", "attempts": 2}
{"ts": "...", "card": "1.1.1", "state": "completed", "chars": "2940"}
```

## 보존 vs 수정 가이드
| 지적 종류 | 행동 |
|---|---|
| 특정 수치 누락 | 해당 문장만 재작성 (주변 보존) |
| 블록 전체 부실 | 블록만 재작성 |
| 카드 전체 부실 | 카드 전체 재작성 (다른 카드 보존) |
| 섹션 구조 문제 | 섹션 전체 재작성 (다른 섹션 보존) |

**절대 금지**: 한 카드를 수정하면서 다른 카드를 건드리는 것.
