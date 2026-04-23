# KeyRef 메타데이터 스키마

researcher subagent는 수집한 각 레퍼런스를 `KeyRef/<index>_<source_short>.md` 파일로 저장한다. 파일 상단에 YAML frontmatter로 구조화 데이터를 기록하며, `pydantic KeyRefSchema`로 엄격 검증된다.

## 파일 포맷

```
---
<YAML frontmatter>
---

<원문 요약 또는 원문 일부 — 한국어/영어 모두 허용, 2000자 상한>

[인용 위치 메모]
- 섹션 1.1.1에서 정확도 수치 인용 예정
- 섹션 2.3의 프로젝트 타임라인 참조
```

## 필수 필드 (schema validation 필수)

```yaml
schema_version: "0.1.0"
id: REF-023                      # REF-xxx 형식, 3자리 숫자
category: 학술                    # 정부공공|국제기구|학술|기업R&D|전문연구기관|산업시장|뉴스
source: MIT CSAIL                 # 기관·출판사·사이트
institution: MIT CSAIL            # 연구 소속 (선택)
authors: [Park, J., Smith, K.]    # 저자 리스트
year: 2024                        # 1990~2100
venue: IEEE IoT Journal           # 학회·저널·기업명 (선택)
title: "Low-power LoRa mesh for precision irrigation"
url: https://...                  # 원본 URL (WebFetch 가능한 경우)
excerpt: "..."                    # 핵심 내용 요약 (2000자 상한)
reliability: 확인됨                # 확인됨|단일출처|미확인|AI지식
related_sections: ["1.1", "2.3"]  # 본 REF가 인용될 섹션 ID
```

## 확장 메타데이터 (기술연구·카드 연결)

### key_numbers
문서에서 직접 인용 가능한 구체 수치:
```yaml
key_numbers:
  - "정확도 94.3% (기존 81% 대비 13.3%p 향상)"
  - "소비전력 0.8W (업계 평균 2.1W)"
  - "배포 규모 500 노드, 농지 12km²"
```

### technologies (카드 생성용)
본 REF에 등장하는 기술 (하나 이상):
```yaml
technologies:
  - name: "LoRa-Mesh Precision Irrigation"
    type_tag: "통신·센싱"
    key_metrics: ["정확도 94.3%", "소비전력 0.8W"]
    importance: high              # high|medium|low
  - name: "Adaptive Water Scheduling Algorithm"
    type_tag: "제어"
    importance: medium
```

### projects (카드 생성용)
본 REF에 등장하는 연구 프로젝트:
```yaml
projects:
  - name: "SMART-IRRI-2024"
    institution: "MIT CSAIL"
    pi: "Dr. Park, Junho"
    period: "2023.01-2025.12"
    budget: "$3.2M"
    sponsor: "NSF IoT-Agri"
    importance: high
```

### products (카드 생성용)
본 REF에 등장하는 제품·솔루션:
```yaml
products:
  - name: "AgriLink X2"
    maker: "AgroTech Inc."
    country: "USA"
    deployed_at: "California Central Valley, 500 nodes"
    price_range: "$500-800/node"
    importance: medium
```

## 검증 실패 처리 (schema drift)
researcher subagent가 생성한 YAML이 KeyRefSchema 검증 실패 시:
1. **1차 재생성 요청**: 실패 이유 알려주고 다시 YAML만 출력
2. **2차 실패**: 해당 REF 스킵, `TECHDOC-E022` 로그
3. 최종 `build_reflist.py`가 유효 REF만 `reference_list.json`에 포함

## 파일명 규칙
```
KeyRef/
├── index.json           # 모든 REF의 인덱스 (build_reflist.py 출력)
├── 001_농식품부_스마트농업.md
├── 002_FAO_SmartIrrigation.md
├── 023_MIT_LoRaMesh.md
└── ...
```
- `<index>_<source_short>.md`
- index는 3자리 (001~999)
- source_short는 공백·특수문자 제거, 최대 20자

## 연결 관계

### REF → 카드
카드 작성 시 `ref_ids` 배열에 포함된 REF만 인용 가능.

### REF → 별첨
별첨 작성 시 Round 6 추가 REF를 별첨 전용으로 수집 가능 (본문 REF와 중복 허용).

### 섹션 매핑
`related_sections` 필드로 섹션별 REF 커버리지 계산 (섹션당 18~22건 목표).
