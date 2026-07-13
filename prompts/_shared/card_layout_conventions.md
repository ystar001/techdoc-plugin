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

## 서식·다이어그램 저작 규칙 (F39·F41·F24·F50)

두 모드 공통. 처음부터 아래대로 저작해야 render·gate에서 깨지지 않는다.
(`check_quality`/`format_gate`가 위반을 결정론적으로 측정한다.)

### 구조 데이터 표현 (F41)

- **구조 데이터**(매핑·비교·규약·계층 목록)는 **표 또는 리스트**로 작성한다. 산문 한 문단에
  녹여 넣지 않는다.
- **코드블록**(```` ``` ````)은 **진짜 의사코드·함수 signature·JSON·if/else 규칙**에만 쓴다.
  표기 규약·매핑표·비교표·ASCII 트리(`├─└─`)를 코드블록에 넣지 않는다 — 표/리스트/flowchart로.
- **병렬 열거**("첫째 …, 둘째 …, 셋째 …")는 **불릿 리스트**로 쪼갠다. 도입 문장("핵심은 세
  가지다")과 결론·전환 문장은 리스트 밖 별도 문단으로 보존한다.
- 인라인 가짜 계층번호 `(i)/(ii)/(a-1)`·상위 평문 라벨 `(a)(b)(c)`로 계층을 흉내내지 않는다.
  계층은 **중첩 md 리스트(2단계 이상 4칸 들여쓰기)**로 표현한다.

### mermaid 라벨 인용 (F39)

특수문자(공백·`·`·괄호·숫자로 시작하는 토큰)가 든 라벨은 **반드시 따옴표로 감싼다**. 안 그러면
mermaid parse가 실패해 그림이 통째로 안 나온다.

- subgraph 제목: `subgraph id["사과·감귤"]` (raw `subgraph 사과·감귤` 금지)
- 엣지 라벨: `A -->|"TAW=1000(θFC-θWP)Zr"| B` (raw `-->|…(…)…|` 금지)
- xychart 축: `x-axis ["기초선", "2026목표"]` (숫자머리 토큰 인용)
- 줄바꿈은 `<br/>`로 — mermaid는 리터럴 `\n`을 해석하지 않는다.

### 서식 혼용 (F24)

서술형과 개조식은 **상호배제가 아니다**. 한 카드 안에서 논문형 서술 문단과 불릿 리스트를
**자유롭게 혼용**한다(문서 style이 `혼합형`일 때 특히). 원리·배경·해석은 서술 문단으로,
병렬·순차 항목(요건·단계·비교·구성요소)은 리스트로 표현한다. "서술형이라 리스트를 쓰면 안
된다"는 오해로 열거를 산문에 뭉치지 말 것.

### 시각화 밀도 (F50)

문서는 텍스트 위주가 되지 않도록 **시각 요소를 적극 사용**한다.

- 섹션/카드당 **최소 1개** 시각 요소(표·그림·차트·mermaid)를 목표로 한다. 특히 본문이 긴
  카드(3000자 이상)는 시각 요소 없이 산문만으로 채우지 않는다.
- 수치·비교·분류·절차·구조는 **표 또는 다이어그램**으로 먼저 제시하고 본문으로 해석한다.
- 카드의 `figures`(`{path, caption}`)·`diagrams`(`{mermaid, caption}`) 필드를 적극 채운다.
- `check_quality` format_gate의 `visual_density`가 밀도 부족을 WARNING으로 표시한다.

### 정형 사양 블록 (F32 — 방법론·표준 카드)

SW 정형화 대상(함수·상태벡터·파라미터)을 담는 방법론·표준 카드는 산문 대신 **구조화 `formal_blocks`**를 채운다. render가 본문 정형 박스로 출력하고 CSV/JSON Schema로 추출한다.

```json
"formal_blocks": {
  "function_spec": [{"name": "...", "signature": "f(x) -> R", "io": "...", "unit": "...", "range": "...", "default": "...", "source": "§..."}],
  "param_table": {"columns": ["param", "value", "unit", "source"], "rows": [["Kc", "1.15", "-", "REF-0012"]]},
  "state_vector_schema": { "type": "object", "properties": { "...": {"type": "number"} } }
}
```

- 함수 시그니처·파라미터 값·출처(`[REF-xxx]`)는 본문 근거와 일치시킨다.
- 이 카드는 `formal_section: true`로 표시하면 `--variant general`(일반용)에서 자동 제외된다(F36).

## 어느 모드를 사용해야 하나

- plugin의 `/techdoc` 통합 파이프라인을 사용하는 경우 → Standard 모드 (자동).
- 자체 호출 1건 = 카드 1개 패턴을 사용하는 경우 → Self-model 모드 (v0.2.0 엄격 표준 — 위 규약 준수, `/techdoc-rewrite`·`/techdoc-write --single-call`에서 자동 인식).
- 두 모드를 한 프로젝트에서 혼용하지 않습니다. `output/`에 두 모드 산출물이 섞이면 plugin이 standard를 우선합니다 (`scripts.card_layout.detect_mode`).
