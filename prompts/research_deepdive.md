# 별첨 6라운드 심층 조사 지시 (researcher subagent)

본문 5라운드 조사 완료 후, 선정된 별첨마다 **6라운드 추가 조사**를 수행한다. 각 별첨당 25~30회 검색.

## 6라운드 세부 목적

### Round 6a: 원문 심화 (5회 이상)
- 핵심 논문 전문 확보 (`WebFetch`로 DOI·arxiv·기관 저장소 직접 접근)
- 방법론·실험 설계·결과 상세 파악
- 보충 자료 (supplementary materials)

### Round 6b: cited-by 추적 (5회 이상)
- 원 논문을 인용한 후속 연구 5~10편
- 연도별 인용 추이
- 영향력 있는 후속 그룹 식별

### Round 6c: 저자·기관 프로필 (3회 이상)
- PI·핵심 저자 커리어 (학위·소속·대표 논문)
- 연구 그룹·랩 공식 사이트
- 학계 영향력 지표 (h-index, 인용 수)

### Round 6d: 표준·특허 연결 (3회 이상)
- 관련 국제 표준 (IEEE, ISO, ITU)
- 등록 특허 (Google Patents, KIPRIS)
- 표준화 진행 상황

### Round 6e: 비판·대안 관점 (3회 이상)
- 반대 의견 (dissenting views)
- 대안적 접근 비교
- 재현 실패 사례
- 한계 지적 논문

### Round 6f (선택, 3회): 최신성 추가 (기본 차수에 없던 최신 자료)
- 최근 6개월 내 발표 논문·발표·프리프린트
- 블로그·GitHub discussion

**합계**: 19~22회 기본 + 선택 확장 = **별첨당 25~30회**.

## site: 연산자 활용 예시

### 6a 원문 심화
```
{기술명} site:arxiv.org
{기술명} full-text site:ieeexplore.ieee.org
{기술명} site:link.springer.com
```

### 6b cited-by
```
{저자명} cited by 2024
{기술명} {원저자명} subsequent work
{기술명} reference 2025
```

### 6c 저자 프로필
```
{PI 이름} researcher profile site:{대학도메인}
{저자명} Google Scholar
{저자명} h-index
```

### 6d 표준·특허
```
{기술명} IEEE standard
{기술명} site:patents.google.com
{기술명} site:kipris.or.kr
{기술명} ISO standard
```

### 6e 비판·대안
```
{기술명} limitations critique
{기술명} vs {대안기술}
{기술명} reproducibility failure
{기술명} not work
```

## 결과 저장 형식
각 별첨별 `research_deepdive_<appendix_id>.json` 파일 생성:

```json
{
  "schema_version": "0.1.0",
  "appendix_id": "A.1",
  "source_card_id": "1.1.1",
  "rounds": [
    {"round": "6a", "purpose": "원문 심화", "queries": [...], "refs_found": [...]},
    {"round": "6b", ...},
    ...
  ],
  "total_refs": 22,
  "new_refs_vs_body": 14,
  "duration_s": 180.5
}
```

## 완료 기준
- 별첨당 전용 REF **20~30건** 확보
- `WebFetch`로 원문 확보한 핵심 논문 **최소 3건**
- cited-by 후속 논문 **최소 5건**
- 비판·대안 관점 자료 **최소 2건**

## 실패 처리
- 쿼터 초과 (`TECHDOC-E042`): 60초 대기 후 재시도, 3회 실패 시 Round 스킵
- 라운드 타임아웃 (`TECHDOC-E043`): 해당 라운드 부분 결과 저장 후 다음 라운드 진입
- Empty result: graceful degradation, 목표 REF 수가 aspirational (FAIL 게이트 아님)
