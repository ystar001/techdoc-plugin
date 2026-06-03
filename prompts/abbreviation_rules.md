# 약어 풀이 정책 (Abbreviation)

writer가 카드·별첨에서 영문 약어를 다루는 표준. `terminology_rules.md §2`의 상세 규정이며, `extract_glossary`가 생성하는 `abbreviations.json` 구조와 정합한다.

---

## 1. 첫 등장 풀이 의무

- 카드 내 **첫 등장 1회**는 `정식명(ABBR)` 풀이를 붙인다. 이후 동일 약어는 약어 단독.
- 정식 형식: `한글풀이(영문풀이, ABBR)`. 한글 풀이가 통용되지 않으면 `영문풀이(ABBR)`.
- 카드 경계를 넘는 일관성은 별첨 `약어 목록(List of Abbreviations)`이 보완한다 — 카드 단위 풀이를 우선한다.

| | 예 |
|---|---|
| 올바름 | `정규화 식생지수(Normalized Difference Vegetation Index, NDVI)로 작황을 추정한다. … 이후 NDVI 단독.` |
| 잘못됨 | `NDVI로 작황을 추정한다. (첫 등장인데 풀이 누락)` |

## 2. 정착 약어 50선 (풀이 생략 허용)

본문 빈도가 높고 한국어권에서 통용되는 아래 약어는 풀이를 생략해도 된다. 단, 카드 핵심 주제어인 경우에는 첫 등장 풀이를 권장한다.

```
AI · ML · DL · CNN · RNN · LSTM · GNN · ViT · LLM · VLM
NDVI · LAI · SAR · GPS · RTK · IoT · LPWAN · LoRa · UAV · UAS
API · CLI · GUI · SDK · OSS · HTTP · JSON · YAML · SQL · URL
USDA · NRCS · NIFA · RDA · KMA · MAFRA · FAO · OECD · EU · ISO
IPCC · W3C · DOI · PRD · REQ · MIT · BSD · 5G · IoT · DBMS
```

정착 약어가 아닌 약어는 §1의 풀이 의무 대상이다.

## 3. standard_form — 같은 약어 1표기

- 한 약어는 프로젝트 전체에서 **단일 표기**(`standard_form`)로 고정한다.
- 대소문자 변형 금지: `IoT`/`IOT`/`iot` 중 하나로 통일(권장: 원어 정착 표기 `IoT`).
- 풀이 페어(`korean`/`english`)도 빈도 1위 형태로 고정한다 — `extract_glossary.decide_standard_form`이 빈도 1위 페어를 표준형으로 선정한다.

| | 예 |
|---|---|
| 올바름 | `IoT` 일관 사용 |
| 잘못됨 | `IoT 센서 … 이후 IOT 게이트웨이 … 다시 iot 노드 (3변형 혼용)` |

## 4. glossary / abbreviations.json 연동

- `extract_glossary`는 KeyRef·카드 본문에서 약어 빈도(`find_abbreviations`)와 풀이 페어(`find_explanation_pairs`)를 추출해 `outline.glossary`를 채운다(`abbreviations.json` 동등 구조).
- glossary 구조: `{ABBR: {"korean": "...", "english": "...", "standard_form": "..."}}` 또는 단순 `{ABBR: "한글풀이"}`.
- writer는 glossary에 표준형이 있으면 그것을 따른다. glossary가 비어 있으면 `extract_glossary`가 `WARN: glossary 비어 있음`을 출력하므로, 수동 보강 또는 카드 내 풀이로 보완한다.
- 검토 시 `review_consistency.md`가 풀이 누락·표기 변형을 점검한다.
