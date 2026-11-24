---
description: 품질 게이트 — 렌더 트리·카드 경로만 받아 게이트를 돌리고, 결과마다 규칙 번호·층·대상 수·판정·집행 수준을 단다
argument-hint: <project_root> [--config techdoc.project.yaml] [--gates V8,V13] [--selftest]
---

# /techdoc-qc — 품질 게이트 (v1.11)

문서 프로젝트 폴더 하나를 받아 본체·문서 종류·분야·시리즈 묶음의 게이트를 돌린다. LLM 호출은 0회이고 결정론적이다. 같은 입력이면 같은 결과가 나온다.

```bash
cd ${CLAUDE_PLUGIN_ROOT}
python -m scripts.qc "$PROJECT_ROOT"                     # 전부
python -m scripts.qc "$PROJECT_ROOT" --gates V8,V68      # 일부만
python -m scripts.qc "$PROJECT_ROOT" --selftest          # 게이트 자기검사만
```

결과는 `<카드 폴더의 부모>/qc_report.json`(기본 `output/qc_report.json`)과 화면 표로 나온다.

> **입력 범위**: self-model 카드(`cards/*_card.json`)·렌더 트리 md·md 직접 저작 원고(`draft/`)를 읽는다. self-model 카드가 없으면 플러그인 기본 **standard 모드 산출물**(카드 폴더의 부모, 기본 `output/`)에서 카드를 읽는다 — `document_draft.json`, 없으면 `document_final.json`, 그것도 없으면 `sections/section_*.json`의 `tech_cards`·`project_cards`·`product_cards`(본문 blocks 7/7/6)와 절 `html_content`(카드 id = 절 id). 카드 id는 카드의 `id`(예: `1.1.1`)이고, 종류가 다른 카드와 번호가 겹치면 `1.1.1~project`처럼 종류를 붙인다. 카드의 `ref_ids`는 작성기가 선언한 목록이라 인용으로 세지 않는다(V8은 본문 블록의 `[REF-…]`만 본다). 산문 게이트는 렌더 트리를 보므로, standard 모드에서 카드만 있으면 산문 게이트 다수가 「대상 없음」으로 나온다(통과가 아니다). 렌더 트리 위치가 기본값과 다르면 `paths.render_tree`로 알려 준다.

## 판정과 집행 수준 — 서로 다른 두 축

| 판정 | 뜻 |
|---|---|
| `pass` | 대상을 읽었고 지적 없음 |
| `fail` | 지적 있음, 또는 문서 종류상 **있어야 할 대상이 없음** |
| `no-target` | 읽은 대상 0 — **통과가 아니다**. 따로 보고한다 |
| `skip` | 설정으로 끔, 또는 명세는 있으나 아직 구현 없음 |

| 수준 | `fail`일 때 | 합계 |
|---|---|---|
| 막음 | 종료 코드 1 | `blocking_total` |
| 경고 | 진행 | `warning_total` |
| 기록만 | 진행 | `record_total` |
| 시범 | 진행 | `pilot_total` (합계 밖) |
| 구조 | 종료 코드 1 | `blocking_total` |

## 종료 코드

| 코드 | 뜻 |
|---|---|
| 0 | 막음 수준 실패 없음 |
| 1 | 막음 수준 실패 있음 |
| 2 | 입력 없음 — self-model 카드·standard 모드 카드(`document_draft.json` 등)·렌더 트리를 모두 못 찾음(경로 설정 확인), 또는 `--gates`로 남은 게이트가 없음 |
| 3 | 게이트 자기검사 실패, 또는 실행 중 게이트 오류(그 게이트만 건너뛰고 나머지는 끝까지 돈다) |

## 프로젝트 설정 `techdoc.project.yaml` (선택)

없으면 플러그인 출력 관례(`output/cards`·`output/render/tree`·`output/reference_list.json`)로 돈다.

```yaml
schema: techdoc-project/1
kind: methodology              # 문서 종류 묶음 (기본 tech_report)
kind_dir: ../_bundles/kinds/my_kind   # 비공개 문서 종류 묶음 경로 (선택 — 없으면 플러그인 bundles/kinds/<kind>)
domain: ../_bundles/agriculture   # 분야 묶음 경로 (선택)
series: ../my-series/rules        # 시리즈 묶음 경로 (선택)
numbering: {section: arabic, appendix: letter}   # arabic(1.1) · roman(II.6) · letter_middle(2.A.7)
paths:
  cards: output/cards
  render_tree: output/render/tree
  references: output/reference_list.json
  draft: output/draft            # md 직접 저작 원고가 있으면 산문 게이트가 트리 대신 본다
gates:
  off: [V45]                     # 끌 게이트
  exempt:
    "1.1|sec2": {gates: [V13], why: "개정 이력 표가 옛 이름을 인용"}   # 그 카드의 그 섹션만
    "1.4": {gates: [V27], why: "법령 원문 인용 카드"}                    # 그 카드의 지적 전부
  level: {V68: 막음}             # 집행 수준 덮어쓰기 (V68 본체 기본은 경고)
expects: {V57: ">=1"}            # 이 문서에 있어야 할 대상(없으면 fail) — 보통 문서 종류 묶음이 싣는다
extra:
  citation:
    internal_files: [PLAN.md]    # 참고문헌에 나오면 안 되는 내부 작업 파일 이름
    nonprimary_ok: {REF-012: "1차 문헌이 없는 사실"}   # 백과사전 출처 면제(사유 필수)
    group_authors_ok: [R Core Team]   # 정당한 단체 지은이 — V68 「… Team」 자리표시로 안 잡음
  leak:
    plan_docs: [PRD, case_plan.md]    # 프로젝트 계획 문서 — 「PRD §1.2」·「PRD REQ-003」·파일 이름을 V87이 잡음
```

설정이 부르는 게이트 id가 없는 id면 경고가 나온다(조용히 무시하지 않음). `domain`·`series` 경로가 없거나 `kind`가 모르는 이름이어도 경고한다. `gates.exempt`의 카드 id는 **따옴표로 감싼다**(`"1.10"` — YAML은 따옴표 없는 1.10을 숫자 1.1로 읽는다, 그러면 오류로 멈춘다).

**면제 키 두 꼴**: `"<카드id>|<섹션키>"`는 그 섹션의 지적만, 파이프 없는 `"<카드id>"`는 **그 카드의 지적 전부**(그 카드의 모든 섹션·분할 조각 `cid|…`)를 면제한다 — 넓은 면제라 사유(`why`)를 꼭 적는다. 면제가 먹지 않는 게이트(명세 `exemptable: false` — V6·V7·V8·V13·V59 등 원본이 면제를 거치지 않던 것)에 적은 면제는 경고 한 줄을 남기고 지적은 그대로 둔다.

**문서 종류 묶음과 겹침 규칙**(v1.11-c): 설정은 **본체 기본 → 문서 종류 묶음(`bundles/kinds/<kind>/kind.yaml`, 또는 `kind_dir`) → 이 파일** 순서로 겹친다. 뒤가 이긴다.
- 표(dict) — `extra`·`gates.level`·`expects` — 는 키마다 재귀로 겹친다. 이 파일이 적은 키만 바뀐다.
- 값·목록 — `gates.off`, `extra.*`의 목록 — 은 **통째로 교체**한다(이어 붙이지 않음). 예: 이 파일에 `gates.off`를 적으면 문서 종류 묶음의 `off`는 버려진다.
- 문서 종류 묶음 꼴: `schema: techdoc-kind/1`, `gates: {level, off}`, `extra`, `expects`. 플러그인은 `tech_report`(분량 하한 800자 경고·V88 카드 블록 표제 `extra.repeat.block_heads`)와 `methodology`(분량 하한 경고)를 싣는다. 묶음이 없는 종류(`policy_report` 등)는 본체 기본으로 돌고 경고 한 줄을 남긴다.
- 분량 하한은 경고뿐이다(E18). 시리즈 고유 분량(예: 절 1만 자대)은 시리즈 설정 `extra.check_quality.size_thresholds`·`extra.verify_cards.thresholds`에 둔다. 아무 층도 표를 싣지 않으면(묶음 없는 종류) qc는 범용 바닥 800자(카드 규칙의 가장 낮은 하한)로 본다 — 기존 CLI(`check_quality`·`verify_cards`)의 기본표는 그대로다.
- 상한은 없다. 지시문의 상한은 안내값이고, 넘치면 별첨으로 옮긴다(내용 보존, 줄이거나 압축하지 않음).

**`extra.*` 형식 검사**: 게이트가 읽는 키는 형을 본다 — 목록 자리에 문자열(`allow_heads: "결론"`), 정수 자리에 글자(`max_repeats: "abc"`), `max_repeats: 0`(1 이상이어야 함)은 키 이름을 담은 오류로 멈춘다.

## 게이트 (v1.11 — 90종)

판정 수준은 **플러그인 기본값**이다. 가독성·문체 게이트는 범용 기본을 「경고」로 두고(E18), 시리즈·문서 종류 설정(`gates.level`)이 「막음」으로 올릴 수 있다. 「시범」은 합계·종료 코드 밖.
명세의 `kinds`가 있는 게이트는 그 문서 종류에서만 돈다 — 다른 종류면 skip(「문서 종류 밖」), 합계 밖. 게이트 사전(`dicts/` 한계값·띄어쓰기 목록)은 본체 → 문서 종류 → 분야 → 시리즈 → 프로젝트(`.techdoc/dicts/`) 층 순서로 덮어쓰거나 `"extend": true`면 잇는다.

### 인용·서지 (4)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V8 | 인용 REF가 참고문헌 목록에 있나·고아 REF | 본체 | 막음 |
| V13 | 참고문헌 중복 등록·백과사전·말미 목록 | 본체 | 막음 |
| V45 | [REF-n](…) 가짜 링크 | 본체 | 막음 |
| V68 | 참고문헌 내부 파일·지은이 빈칸·정렬 (단체 지은이 허용 `extra.citation.group_authors_ok`) | 문서종류 | 경고 |

### 구조·상호참조 (12)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V2 | 끊어진 상호참조 | 문서종류 | 막음 |
| V21 | 핵심요약 규약 (methodology만) | 문서종류 | 막음 |
| V26 | 개요 절 아래 분업·항해 하위절 | 문서종류 | 막음 |
| V30 | md 상호참조 | 문서종류 | 막음 |
| V31 | 표제 형식 | 문서종류 | 경고 |
| V34 | 절 도입부 | 문서종류 | 막음 |
| V39 | 표제 꼴 | 본체 | 경고 |
| V44 | 물음꼴 볼드 소표제 | 본체 | 경고 |
| V57 | 절 끝 결론 (methodology만) | 문서종류 | 막음 |
| V59 | 별첨 문자가 A부터 건너뛰지 않음 | 문서종류 | 막음 |
| V72 | 별첨 번호 꼴 | 문서종류 | 막음 |
| V78 | 항 안 번호 층위 | 문서종류 | 시범 |

### 문장(산문) (18)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V23 | 문장 접합 | 본체 | 막음 |
| V24 | 메타 서술 누수 | 문서종류 | 경고 |
| V25 | 도표 되읽기 | 문서종류 | 경고 |
| V27 | 문장 길이 160자 초과 | 본체 | 경고 |
| V28 | 줄표 남용 | 본체 | 경고 |
| V29 | 강조 밀도 | 본체 | 경고 |
| V35 | 낯선 표현 | 본체 | 경고 |
| V36 | 구성 설명 | 본체 | 경고 |
| V41 | 서수 나열 문단 | 본체 | 경고 |
| V41W | 흩어진 서수 나열(V41 넓힘) | 본체 | 시범 |
| V43 | 문서 주어 결손 | 본체 | 경고 |
| V50 | 겹친 말 | 본체 | 막음 |
| V53 | 그림 구성 설명 | 본체 | 경고 |
| V54 | 안내·제목 되풀이 | 문서종류 | 경고 |
| V56 | 문서 자기 선언 | 문서종류 | 경고 |
| V69 | 표 읽어 주기 | 본체 | 경고 |
| V76 | 띄어쓰기 | 본체 | 시범 |
| V81 | 굵은 글씨 | 본체 | 시범 |

### 캡션·도표 (12)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V6 | 캡션·본문 연계 | 문서종류 | 막음 |
| V12 | 도표 번호 정합 | 문서종류 | 막음 |
| V15 | 표 뒤 빈 줄 | 문서종류 | 막음 |
| V17 | 캡션 규약 일관성 | 문서종류 | 경고 |
| V18 | 도표 아래 설명 문단의 가독성 | 문서종류 | 경고 |
| V40 | 근거 등급 열 | 문서종류 | 경고 |
| V62 | 표의 참조 열 | 문서종류 | 경고 |
| V63 | 표 열 이름 정규화 | 문서종류 | 경고 |
| V66 | 그림·표 자리 호출 | 본체 | 경고 |
| V73 | mermaid 홑 물결표 | 본체 | 막음 |
| V75 | 그래프 축 이름 | 본체 | 막음 |
| V80 | 그림 안 글 길이 | 본체 | 시범 |

### 용어·표기·기타 (11)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V7 | 이미지 라이선스 대장 | 본체 | 막음 |
| V14 | 요약·본문 일치 | 문서종류 | 막음 |
| V22 | 콜아웃 본문 들여쓰기 | 본체 | 막음 |
| V37 | 수식 손상 | 본체 | 막음 |
| V42 | 사적 기호 | 본체 | 경고 |
| V46 | 한글이 든 인라인 코드 | 본체 | 경고 |
| V47 | 한글 기울임 | 본체 | 경고 |
| V48 | 수식 안 한글 | 본체 | 막음 |
| V49 | 이스케이프 안 된 통화 $ | 본체 | 막음 |
| V51 | 저작 도구 표시 | 본체 | 막음 |
| V64 | 약어 장 첫 등장 풀이 | 문서종류 | 막음 |

### 집필 흔적(신규) (1)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V87 | 집필 흔적 — 호출 번호·작업 파일 이름·분할 안내·「이 카드」 | 본체 | 경고 |

### 같은 틀 되풀이(신규) (1)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V88 | 같은 틀 되풀이 — 한 장 안 같은 표제 머리 3회 초과 · 같은 머리 묶음이 여러 장에 걸침 | 본체 | 경고 |

설정: V87 `extra.leak.file_patterns`(작업 파일 이름 글롭 — `allow`와 같은 `fnmatch` 꼴 `*.py`, 정규식은 `re:` 접두)·`extra.leak.allow`(글자 그대로 또는 글롭)·`extra.leak.plan_docs`(프로젝트 계획 문서 이름 — 기본 없음, 플러그인은 계획 문서를 만들지 않는다)·`extra.leak.card_fields`(독자 글이 없을 때만 읽는 카드 칸, 기본 `scope_note`·`split_continuation_note`). V87은 **독자 글(draft·렌더 트리)이 있으면 그것만** 본다 — 카드 칸은 렌더되지 않거나 이미 트리에 있다. V88 `extra.repeat.max_repeats`(1 이상, 기본 3)·`allow_heads`(프로젝트)·`block_heads`(문서 종류 묶음 — 둘을 합쳐 세지 않음)·`frame_heads`(틀 길이, 기본 3)·`frame_chapters`(틀이 걸친 장 수 기준, 기본 4). V21 분야 전문어는 `extra.structure.qs_jargon`과 층 사전 `dicts/qs_jargon.json`(`{"items": [...]}`)을 합친다.

**실제 문서 검출 측정 반영(v1.11-c, F109~F117)** — 본체 기본을 넓히고, 원본 판정이 필요한 문서(시리즈)는 설정으로 되돌린다.

- V68 `extra.citation.group_author_fields`(기본 `[institution]`): `authors`가 비어도 이 칸에 이름이 있으면 단체 지은이로 본다. `[]`이면 `authors`만.
- V57 `extra.structure.conclusion_split_groups`(기본 켬): 부모 카드 없는 분할(`II.6.L1`~)을 부모 절 하나로 묶어 마지막 분할에서 결론을 본다. `conclusion_titles`(기본 결론·종합·맺음·마무리): 마지막 절 표제 머리가 이 낱말로 시작하면 결론이 있는 것으로 본다(`[]`이면 `conclusion` 칸만).
- V21 `extra.structure.summary_retired_fields`(기본 없음): 남아 있으면 결함인 폐지 칸(시리즈는 `[one_sentence]`). `summary_limits`(`min_chars`·`max_chars`·`min_sentences`·`max_sentences`·`sentence_max`, 기본 20·160·1·2·110).
- V24 자칭 서술 낱말은 층 사전 `dicts/meta_self_reference.json`(`nouns`·`verbs` — 「섹션」·「정한다·정리한다·본다·묻는다」 포함). `extra.prose.selfref_nouns`·`selfref_verbs`는 목록을 통째로 바꾼다.
- 같은 위치·같은 글의 지적은 보고에 `[중복] Vnn n건`으로 따로 알린다(건수는 원본 계약대로). V6·V14·V30·V87은 지적마다 대상(표 번호·낱말·차례)을 글에 담아 고유하다.

### 시각 필드·코드 네임스페이스(신규) (2)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V89 | 시각 필드 id에만 번호 — 캡션에 그림·표 번호 없음 | 본체 | 경고 |
| V90 | 코드 네임스페이스 — 같은 코드를 절마다 다른 뜻으로 정의 | 본체 | 경고 |

V89(F82): 카드 `diagrams[]`·`figures[]` 항목에 `id`가 있는데 `caption`에 「그림 1-2」·「표 II.8-1」 같은 번호가 없으면 경고 — 렌더에서는 캡션만 실려 번호가 사라진다.
V90(F75): 코드 토큰(기본 `[A-Z]{1,3}-?\d{1,3}`, `REF-…` 제외)이 **정의**되는 곳은 ① 표의 첫 칸이 토큰 하나뿐인 행(뜻 = 다음 칸) ② 줄 첫머리(목록·표제 기호 허용)의 `토큰:`·`토큰 —`·`토큰(뜻)` 두 가지뿐이다. 한 토큰이 두 절 이상에서 뜻이 다르게 정의되면 토큰마다 경고 하나(같은 뜻·한쪽이 다른 쪽을 품는 줄임은 통과, 분할 카드 `.L1`·`.L2`는 같은 절). 설정 `extra.code_namespace.pattern`(토큰 정규식)·`extra.code_namespace.allow`(토큰 목록).

### 기존 품질 도구 흡수 (29)

`check_quality`·`format_gate`·`verify_cards`의 지표가 게이트가 됐다(지표 이름·판정 그대로, 측정 함수를 CLI와 함께 씀). 기존 CLI는 같은 결과 계약(`total_fail`·`total_warning`·종료 코드 2)을 내는 래퍼로 남는다. 수준은 도구의 FAIL → 막음, WARNING → 경고 — 단 **절대 분량 하한은 본체 기본 경고**(E18, 문서 종류 프로필이 막음으로 올림; CLI는 FAIL 그대로). PLG-CQ 문서 지표는 standard 모드에서, self-model 지표·PLG-FG·VC는 self-model 카드에서만 돈다(다른 모드면 「대상 없음」). `--strict` 승격·baseline 회귀는 CLI 전용. 임계 덮어쓰기: `extra.check_quality.size_thresholds`·`extra.verify_cards.thresholds`(예 `{S: 3000}`). 캡션 번호 꼴은 `numbering.section`을 따른다(F82 — CLI도 프로젝트 설정을 읽는다).

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| PLG-CQ-section_length | 섹션 본문 길이 하한 미달 | 본체 | 경고 |
| PLG-CQ-section_citations | 섹션 인용 수 하한 미달 | 본체 | 경고 |
| PLG-CQ-ai_estimate_ratio | AI 추정 표현 비율 초과 | 본체 | 막음 |
| PLG-CQ-undefined_abbreviations | 풀이 없는 약어 3종 초과 | 본체 | 경고 |
| PLG-CQ-terminology_inconsistencies | 외래어 비표준 표기 | 본체 | 경고 |
| PLG-CQ-academic_ratio | 학술 출처 비율 0.35 미만 | 본체 | 막음 |
| PLG-CQ-rd_ratio | 기업 R&D 출처 비율 0.24 미만 | 본체 | 막음 |
| PLG-CQ-tech_cards_per_section | 섹션당 기술 카드 수 하한 미달 | 본체 | 경고 |
| PLG-CQ-tech_card_block_fill | 기술 카드 7블록 충족률 0.85 미만 | 본체 | 막음 |
| PLG-CQ-undersized_cards | 최소 길이 미달 기술 카드 | 본체 | 경고 |
| PLG-CQ-caption_duplicate | 캡션 번호 중복 | 본체 | 경고 |
| PLG-CQ-caption_gap | 캡션 번호 결번 (self-model) | 본체 | 경고 |
| PLG-CQ-caption_dangling_ref | 정의 없는 캡션 번호 참조 | 본체 | 경고 |
| PLG-CQ-self_model_length | self-model 카드 사이즈별 본문 분량 | 본체 | 경고 |
| PLG-FG-inline_hierarchy | 인라인 계층번호 (i)(ii)·(a-1) | 본체 | 경고 |
| PLG-FG-top_plain_label | 상위 평문 라벨 (a)(b)(c) | 본체 | 경고 |
| PLG-FG-nonbullet_indent | 불릿 아닌 2·3칸 들여쓰기 줄 | 본체 | 경고 |
| PLG-FG-flatten_risk_indent | 4배수 아닌 리스트 들여쓰기 | 본체 | 경고 |
| PLG-FG-high_list_ratio | 섹션 리스트 비율 50% 초과 | 본체 | 경고 |
| PLG-FG-redundant_summary | 중복 요약 단락 — 종합하면·정리하면 | 본체 | 경고 |
| PLG-FG-control_chars | 본문 제어문자 | 본체 | 경고 |
| PLG-FG-mermaid_label_risk | mermaid 라벨 미인용 특수문자 | 본체 | 경고 |
| PLG-FG-inline_enumeration | 인라인 병렬 열거 — 첫째·둘째 | 본체 | 경고 |
| PLG-FG-visual_density | 시각화 밀도 — 4,000자당 표·그림 1개 미만 | 본체 | 경고 |
| VC-A | 카드 JSON 읽기 실패 | 본체 | 막음 |
| VC-B | 모르는 schema_version | 본체 | 경고 |
| VC-C | 사이즈별 본문 분량 | 본체 | 경고 |
| VC-D | 본문 종결부 컷오프 의심 | 본체 | 경고 |
| VC-E | citation_count 0 | 본체 | 막음 |

standard 모드 산출물 읽기와 기존 품질 도구 흡수는 v1.11-c에서 들어왔다.
