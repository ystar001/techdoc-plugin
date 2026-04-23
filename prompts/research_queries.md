# 특화 쿼리 템플릿 (5라운드 본문 + 6라운드 별첨)

researcher subagent가 라운드별로 사용하는 쿼리 패턴. `{기술}`·`{섹션주제}`·`{기관명}` 등은 런타임 치환.

## 본문 조사 — 5라운드 × 섹션당 21회

### Round 1: 광범위 (섹션당 6회)
주제 지형 파악. site 연산자 없이 일반 검색.
```
{섹션주제} 동향
{섹션주제} overview
{섹션주제} 기술 현황
{섹션주제} 2024 trends
{섹션주제} market size
{섹션주제} 글로벌 현황
```

### Round 2: 대학 타깃 (섹션당 5회)
`prompts/research_sites.md`의 학술 도메인 사용.
```
{기술} site:arxiv.org
{기술} site:ieeexplore.ieee.org
{기술} site:dl.acm.org
{기술} site:mit.edu OR site:stanford.edu
{기술} 대학 연구팀 논문
```

### Round 3: 기업 R&D (섹션당 4회)
```
{기술} site:research.google OR site:ai.meta.com
{기술} {기업명} whitepaper
{제품명} technical specification
{기술} patent site:patents.google.com
```

### Round 4: 전문연구기관 (섹션당 3회)
```
{기술} site:etri.re.kr OR site:kist.re.kr
{기술} site:fraunhofer.de OR site:csiro.au
{기술} 출연연 연구보고서
```

### Round 5: 인용·최신성 (섹션당 3회)
```
{기술} {연도: 최근1년}
{저자명 from Round 2} cited by
{기술} latest research 2025
```

## 별첨 조사 — Round 6 (별첨당 25~30회)
별첨 선정된 카드별로 심화. 자세한 내용은 `prompts/research_deepdive.md` 참조.

## 구체 사례 패턴 (REQ-013, REQ-014 충족)

### 수치·성능 확보
```
{기술} X% improvement research
{기술} benchmark {대상}
{기술} performance comparison
{기술} case study {기관명}
{기술} {연도} results
```

### 프로젝트·연구 확보
```
{기술} project {기관명}
{기술} research program {자금원}
{기술} PI {이름}
{기술} 2020-2025 project
```

### 제품·현장 도입 확보
```
{제품명} field trial
{제품명} deployment case
{제품명} customer review
{제품명} installation {지역}
```

## 쿼리 변형 기법

### 동의어·변형
- 한국어 ↔ 영어 ("정밀농업" ↔ "precision agriculture")
- 약어 ↔ 풀이름 ("IoT" ↔ "Internet of Things")
- 최신 용어 ↔ 전통 용어

### 지역·언어 확장
- 동아시아 (한·영·일·중)
- 유럽 (영·독·불)
- 글로벌 기구 (FAO·OECD) 영어

### 시기 명시
- `{기술} 2024 2025` (최근 2년)
- `{기술} decade review` (10년 회고)
- `{기술} roadmap 2030` (미래 전망)

## 쿼리 품질 자체 검증
- [ ] 단순 반복 아님 (매 쿼리 변형 있음)
- [ ] site: 연산자 최소 12회 (21회 중)
- [ ] 영어 쿼리 50% 이상
- [ ] 구체성 (특정 기관·제품·연도 포함)

## 금지 패턴
- 지나치게 일반적인 "스마트농업" 단독 쿼리
- `how to...` 같은 튜토리얼성 검색
- 포럼·Q&A 사이트 타깃 (Reddit·Quora 등 — 신뢰도 낮음)
