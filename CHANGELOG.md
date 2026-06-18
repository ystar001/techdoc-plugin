# Changelog

All notable changes to TechDoc Plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (서식 게이트 — check_quality format_gate)

- **F27** 신규 `scripts/format_gate.py` + `check_quality` self_model 경로 통합 — 자식 `verify_rewrite.py` 게이트 이식. 리스트 비율·인라인 계층번호 `(i)(ii)/(a-1)`·상위 평문 라벨 `(a)(b)(c)`·비-불릿 들여쓰기·평탄화 위험(4배수 아닌 들여쓰기)·중복 요약(종합하면/정리하면)·REF/수치/분량 회귀 측정. 전부 WARNING 기본·`--strict`로 구조 결함 FAIL 승격·optional `--baseline` 회귀 검사·self_model 전용·`markdown` optional(미설치 시 render_nesting만 생략). `check_quality`에 `_collect_body_text`(F1 변형 robust 본문 추출) 추가. `agents/techdoc-reviewer.md`에 형식 정량화는 check_quality 소관 명문화. 신규 테스트 28건(`test_format_gate.py` 16 + `test_check_quality.py` +12). (findings F27, F28, F30)

### Compatibility

- non-breaking. optional 인자(`--baseline`·`--strict`·`--tolerance`) 기본값으로 기존 호출 100% 호환. standard 모드 무변경. SCHEMA_VERSION 0.2.0 유지. 신규 의존성 0개.

## [1.7.0] — 2026-06-04

### Added (Plan N — render 트리 디렉토리 생성)

- **F15** `/techdoc-render --tree` — config 기반 트리 디렉토리 출력. 신규 `techdoc_core/renderers/markdown_tree.py`(`MarkdownTreeExporter`): `routing_config.parse_card_id`로 카드를 Part/시리즈로 분류, split 카드(L1/L2/L3)는 `parent_id`로 부모당 1파일 병합, Part별·최상위 표지/TOC INDEX 생성. 자식 `render_md.py` `write_tree` 일반화 — openfieldtech 도메인 명칭(카테고리·시리즈 라벨)은 routing config 선택 필드로 분리(없으면 card_id 기반 generic 폴백). `paragraph.format_paragraphs`(F10)·`section_heading.section_key_to_heading`(F12) 재사용. `--cards-dir`·`--routing-config`·`--with-series-index` 인자. (findings F15)
- **F17** 단일 카드 시리즈 폴더의 INDEX.md 생략 — `len(entries) > 1`일 때만 시리즈 INDEX 생성(Part·최상위 INDEX는 항상). 중복 INDEX로 인한 1-클릭 추가 진입 제거. (findings F17)

### Compatibility

- non-breaking. `--tree`는 opt-in(단일파일 render 무변경). SCHEMA_VERSION 0.2.0 유지. 신규 모듈·명령 옵션만 추가.

## [1.6.0] — 2026-06-03

### Added (Plan L — autopilot deepdive chunk + 중반 재개)

- **F9-i** autopilot `deepdive`(별첨) chunk — `chunks.STAGE_ORDER`의 review와 render 사이에 삽입. `_prerequisites`에 `deepdive ← review`·`render ← deepdive` 추가. `runner.CHUNK_TO_COMMAND_HINT["deepdive"]` → `/techdoc-deepdive` 매핑. `state.init_state`가 `config.deep_dive_auto`/`deep_dive` 요청 시 `pending`, 아니면 `skipped`(흐름 무변경). autopilot CLI에 `--deep-dive-auto N`·`--deep-dive <ids>` 인자 추가. (findings F9)
- **F9-ii** `state.scan_completed_stages(output_dir)` + `init_state(resume_from_disk=True)` — 디스크 산출물(outline·reference_list·research_*·cards·reviews·document_final)을 스캔해 완료 stage를 `completed`로 자동 마킹(중반 재개). autopilot CLI에 `--resume-from-disk` 인자 추가. 결정론적·LLM 호출 0회. (findings F9)

### Added (Plan K — export-wiki 후처리)

- **F18** `/techdoc-export-wiki`에 후처리 단계 추가 — `scripts/wiki/postprocess.py`. "학술" 과잉 수식어 정리(학술 framework→프레임워크 등)·메타 표시 제거(`## 헤더 (확장)`)·긴 문단 분리(Plan I `paragraph.format_paragraphs` 재사용)·영문 slug 부분 한국어화(고유명사 보존)·문서 안내 섹션. `[REF-xxx]`·수치·고유명사 보존, 멱등, AI 마커 영역만 적용(사용자 메모 보존). `--enhance/--no-enhance`(기본 on). (findings F18)

### Added (Plan M — 테스트 재사용성)

- **F23** `@pytest.mark.project` 마커 등록(`pyproject.toml`) + 컨벤션 문서(`tests/README.md`) — 프로젝트 특화 검증을 분리해 자식 프로젝트가 `pytest -m "not project"`로 코어만 실행 가능. plugin 자체 테스트는 이미 fixtures 기반. (findings F23)

### Note

- F15(render 트리 생성)·F17(시리즈 INDEX 과잉)은 render 트리 후속에서 함께 처리 예정 — open 유지(닫힘 아님).

### Compatibility

- non-breaking. deepdive 미요청 시 `skipped`(render 흐름 유지). `resume_from_disk`·`--enhance` 기본값이 기존 동작 보존. 마커 등록은 테스트 무영향. SCHEMA_VERSION 0.2.0 유지.

## [1.5.0] — 2026-06-03

### Added (Plan I 코어 — render 일반화)

- **F10** MD 출력 단락 break — `techdoc_core/renderers/paragraph.py`(키워드 break + 800자 길이 ceiling, 자식 render_md 흡수, 멱등). `MarkdownExporter`가 섹션별 적용(표·인용 안전). 메타 단락 필터는 Plan H(prompt) 담당이라 미포함. (findings F10)
- **F12** 섹션 키 → 한글 헤딩 — `techdoc_core/renderers/section_heading.py`. Plan G `DEFAULT_SECTION_TITLES` 재사용, 구 서술형 키(`sec3_trends_*`)도 위치(sec3)로 정규화. (findings F12)
- **F21** Part 라우팅 config 외부화 — `techdoc_core/routing_config.py`. openfieldtech 하드코딩을 데이터 기반 config + schema-agnostic `parse_card_id(card_id, config)`로 재설계(프로젝트별 config 교체). `load_routing_config`가 규칙 필수 키 검증. (findings F21)

### Note

- F15 (render 트리 디렉토리 생성)는 본 release에서 **분리**(deferred) — 후속에서 `routing_config` 위에 `write_tree` 흡수 예정. open 유지(미closed). (※ 닫힘 아님 — sync 마커 미부착)

### Compatibility

- non-breaking. SCHEMA_VERSION 0.2.0 유지. F10은 MD 출력에만 적용(HTML/PDF/DOCX 무영향)·멱등. F12·F21은 신규 유틸(기존 호출 무변경).

## [1.4.0] — 2026-06-03

> ⚠️ **BREAKING (SCHEMA_VERSION 0.1.0 → 0.2.0)** — self-model 카드 스키마 표준화.
> 기존 self-model 카드(`output/cards/*_card.json`)를 쓰는 자식 프로젝트는 흡수 후
> **`python -m scripts.migrate output/`** 를 1회 실행해 0.2.0으로 변환한다. plugin
> 표준 카드(`document_final.json`·`blocks`)·KeyRef·writer_state는 무영향.

### Migration 가이드 (자식 프로젝트)

1. `/techdoc-update` 로 v1.4.0 흡수.
2. `python -m scripts.migrate output/` — self-model 카드를 0.2.0으로 변환
   (body 키 통일·섹션 키 `sec1~sec6`·`card_id`/`parent_id`·`title`/`split_summary` 분리).
3. `python ../../techdoc_work/scripts/sync_findings.py --check` 로 일관성 게이트 통과 확인.

### Added (Plan G — 카드 스키마 표준화, breaking)

- **F1** self-model 섹션 본문을 단일 `body` 키로 표준화(narrative·content 변형은 migrate가 흡수). (findings F1)
- **F3** self-model 섹션 키를 위치 기반 `sec1`~`sec6`로 강제하고, 서술 헤딩은 섹션 `title` 필드로 분리. `field_validator`가 비표준 키 거부. (findings F3)
- **F13** self-model 카드 식별자를 단일 `card_id`(split marker 포함) + `parent_id`로 통합(구 `section_id`/`appendix_id` 이중 필드 폐지). (findings F13)
- **F14** 카드 `title`에서 운영 미주(분할 N/M·§구성·페이지)를 `split_summary`로 분리. (findings F14)
- `scripts/migrate.py`: 0.1.0→0.2.0 self-model 변환 등록(standard `blocks` 카드 무영향 가드). `SCHEMA_VERSION = "0.2.0"`.

### Added (Plan J — 본문 카드 시각 필드, additive)

- **F22** 본문 카드(Tech/Project/Product)에 `figures`(`{path, caption}`)·`diagrams`(`{mermaid, caption}`) 필드 추가(별첨 전용이던 시각 필드 흡수). `generate_chart.specs_to_figures`로 차트 연결, card_renderer가 `<figure>`·Mermaid 출력(path·caption HTML escape), `has_math_or_mermaid`가 카드 diagrams도 스캔. (findings F22)

### Added (Plan H — 공공문서 작성 품질 표준)

- **F11** writer 본문에 운영 메타·시그너처('학술' 과잉 수식·1발 PASS·PRD 정합·전수 인용 류) 인라인 금지 — `self_check`/`self_review`로 분리. (findings F11)
- **F16** 신설 프롬프트 4종(`terminology_rules`·`abbreviation_rules`·`reference_format` APA 7th·`review_consistency`) + `citation_rules`·`edit_rules`·`section_write` 확장 + reviewer **consistency** 도메인(tech/market/policy → +1) + `scripts/extract_glossary.py`(KeyRef·카드 → `outline.glossary` 자동추출, 비면 WARN) + `check_quality` 표기 일관성 지표 2종. (findings F16)

### Compatibility

- **breaking**: self-model 카드만(migrate 필요). standard 카드·KeyRef·writer_state·autopilot_state·notion_state 무영향.
- Plan J·H는 additive — 기존 카드 호환. 프롬프트 추가/확장은 런타임 무영향.

## [1.3.1] — 2026-06-02

### Added

- **F19** `parse_toc`가 영숫자 prefix 섹션 ID(R·G1·AP·A-1·R.1)를 지원. ID 뒤 구분자(공백/마침표)를 요구해 "5G/LTE" 같은 제목이 ID로 오인되는 것을 방지. (findings F19)
- **F20** `parse_toc`가 마크다운 표 TOC(`| ID | 제목 | … | Sizing | … |`)를 auto-detect 파싱. 헤더에 "제목" 칼럼이 있는 표만 항목 표로 인식해 메타·매핑 표는 자동 제외하고, Sizing 칼럼(S/M/L/XL)을 `estimated_length`로 매핑(XL→long). 자식 프로젝트 `preprocess_toc.py` 우회 흡수. (findings F20)

### Changed

- `scripts/parse_toc.py`: 섹션 ID 정규식을 모듈 상수 `SECTION_ID_RE`로 승격. `parse_toc_file`을 평문/표 auto-detect 디스패처로 분리(기존 평문 로직은 `parse_toc_plain`으로 보존, 시그니처 무변경). `build_outline`이 표의 Sizing을 `estimated_length`로 우선 반영하고 없으면 subtopic 추정으로 폴백.
- `tests/test_parse_toc.py` 신설 — 16 회귀(영숫자 ID·제목 오인 방지·항목표 식별·Sizing 매핑·평문 보존·깨진 행 skip).

### Compatibility

- SCHEMA_VERSION 0.1.0 유지 (breaking 아님). 평문 TOC 동작 100% 보존. `parse_toc_file(path)->list[dict]` 시그니처 무변경 → 기존 caller·CLI 무영향.

## [1.3.0] — 2026-05-13

### Added

- **TechDoc Autopilot** — 보고서 1건을 사용자 walk-away 가능한 자율 모드로 실행. `/techdoc-autopilot`이 superpowers `/loop` dynamic mode 위에 thin orchestrator로 동작. 매 wake-up마다 1 chunk(섹션 그룹) 처리 → state checkpoint → 다음 ScheduleWakeup. 일반 보고서 ~10 wake-ups, 1.5~2.5h 예산.
- **4 신규 슬래시 명령**: `/techdoc-autopilot` · `/techdoc-autopilot-status` · `/techdoc-autopilot-stop` · `/techdoc-autopilot-resume`. 총 14종 → 18종.
- **6 safety 트리거** — quality_fail · quality_warn_exceeded · card_failures_exceeded · wall_clock_exceeded · state_corruption · manual_stop. 위반 즉시 halt + chat 알림.
- **알림 모델** — silent file log + 이상 시만 chat (`--notify anomalies_only` 기본) + opt-in verbose (`--notify each-wake-up`).
- **신규 모듈** — `scripts/autopilot/{state,triggers,chunks,notify,runner}.py` + `scripts/autopilot.py` + `scripts/autopilot_step.py`. LLM 호출 0회 (autopilot 자체).
- **신규 테스트 ~40건** — state·triggers·chunks·notify·runner 각 회귀.

### Changed

- README 양쪽 14종 → 18종 카운트. 새 "Autopilot" 섹션 (PART Ⅵ).

### Compatibility

- SCHEMA_VERSION 0.1.0 유지 (autopilot_state.json은 별도 `schema_version` "0.1.0").
- 신규 의존성 0개 (superpowers loop skill은 이미 5.1.0 설치).
- `/techdoc` 동작 변경 없음 — autopilot은 별도 명령 (opt-in).
- 기존 `/techdoc-resume`·`/techdoc-rewrite`는 autopilot halt 후 사용 가능.

### Spec · Plan

- `docs/superpowers/specs/2026-05-13-techdoc-autopilot-design.md` (380줄, 15 섹션).
- `docs/superpowers/plans/2026-05-13-techdoc-autopilot.md` (~17 task, 8 phase).

## [1.2.0] — 2026-05-13

### Added

- **Notion 통합** — `/techdoc-export-notion` 신규 슬래시 명령. TechDoc 보고서를 Notion 워크스페이스로 publish. 페이지 계층(루트 + 섹션·별첨 자식 페이지) + KeyRef inline database 자동 생성.
- `/techdoc --push-notion <parent_page_id>` 통합 옵션 — 보고서 생성 완료 후 자동 Notion publish.
- 신규 모듈: `scripts/notion/{client,blocks,keyref_db,state,preflight}.py` + `scripts/export_notion.py`. LLM 호출 0회. httpx 기반 (신규 의존성 0).
- **delta sync** — `output/notion_state.json`의 content hash로 변경 카드만 update_page. 50카드 중 1개 수정 시 API ~1회.
- **mode 자동 판별** — standard + self_model 양쪽 지원 (`scripts.card_layout.detect_mode` 재사용).
- **Phase A 안전 장치** — parent page 권한 사전 점검 + parent_page_id 일관성 검증 + title 변경 자동 갱신.
- **v2 호환 디자인 원칙 4종 명시적 구현**:
  - `notion_state.json`에 `last_edited_time` 보존 (v1.3.x conflict 감지 준비)
  - blocks 변환 가역성 (heading level·code language·table 구조 무손실)
  - REF mention의 안정적 ID (`REF-XXX` 기준)
  - `schema_version` 명시 (`notion_state.json` 0.1.0)

### Spec · Plan

- `docs/superpowers/specs/2026-05-13-notion-push-integration-design.md` (285줄, 12 섹션).
- `docs/superpowers/plans/2026-05-13-notion-push-integration.md` (~20 task).

### 양방향 sync 로드맵 (§10-1)

- **v1.2.x**: `--protect-pages` 옵션 — Notion 측 수동 편집 부분 보존.
- **v1.3.x**: 선택적 pull-back (`/techdoc-pull-notion`) — Notion → disk 명시적 sync.
- **v2.0**: 완전 양방향 sync — timestamp 기반 reconciliation.

### Compatibility

- SCHEMA_VERSION 0.1.0 유지 (breaking 아님).
- 신규 의존성 0개 (httpx·pydantic 이미 포함).
- `NOTION_TOKEN` 미설정 사용자는 영향 없음 (단순히 새 기능을 사용 안 함).

## [1.1.3] — 2026-05-13

### Added

- **F5** `scripts/check_quality`에 self-model 카드 레이아웃(`output/cards/*_card.json`) 지원 추가. 기존 standard 모드(`document_final.json`)와 함께 라우팅: `python -m scripts.check_quality -i <output_dir>`가 mode 자동 판별. openfieldtech `scripts/verify_cards.py`의 사이즈별 임계(S 14k / L1 7k / L2 10k / L3 5k)·F1 변형 본문 키(`body`/`narrative`/`content`) 재귀 합산 패턴 흡수. (openfieldtech findings F5)
- `scripts/check_quality.run_quality_check(output_dir)` — 새 entry point (mode 자동 라우팅).
- `scripts/check_quality.measure_self_model(output_dir)` — self-model 일괄 검사.
- `tests/test_check_quality.py` — self_model/standard/unknown 모드 + F1 변형·CLI 회귀 5건.

### Changed

- `commands/techdoc-review.md` Step 0 (Phase A): domain reviewer 호출 전에 `check_quality` 자동 실행 명시.
- `scripts/check_quality.main` CLI: `-i <dir>` 형태로 디렉토리 지정 시 자동 mode 판별. 기존 `-i <document_final.json>` 동작 유지.

### Compatibility

- SCHEMA_VERSION 0.1.0 유지. 기존 standard 모드 호출(`-i document_final.json`)은 무변경 통과.

## [1.1.2] — 2026-05-13

### Added

- **F8** `/techdoc-rewrite`·`/techdoc-write`에 self-model 카드 레이아웃(호출 1건 = 단일 카드 JSON `output/cards/<id>_card.json`) fallback 추가. `scripts/card_layout.py`로 standard vs self_model 자동 판별. `/techdoc-write --single-call <id>` 인자 신설.
- `techdoc_core.schemas.SelfModelCardSchema` + `SelfModelSection` — 2nd-class 자체 모델 인정·문서화 (1st-class 채택 아님, 자식 프로젝트 호환 단편).
- `prompts/_shared/card_layout_conventions.md` — F1(body 키)·F3(section 키) 권장 컨벤션 명문화. 자식 프로젝트가 self-model 채택 시 참조.
- `tests/test_card_layout.py` — 모드 판별·로드·schema 회귀 10건.
- `tests/fixtures/cards/self_model_layout.json` — openfieldtech 6.5 카드 모사 fixture.

### Changed

- `commands/techdoc-rewrite.md` Step 0: 카드 레이아웃 mode 자동 판별 + self-model 분기.
- `commands/techdoc-write.md`: `--single-call <id>` 인자 명세 추가.

### Compatibility

- SCHEMA_VERSION 0.1.0 유지. 기존 standard 모드 카드·writer_state는 무변경 통과.
- self-model 모드는 자식 프로젝트 선택 — plugin core(`render`·`check_quality`·`migrate`)는 standard만 직접 지원.

## [1.1.1] — 2026-05-13

### Fixed

- **F4** writer subagent가 자체 검증 메모(`AI 추정 표현 0%`·`자가진단:` 등)를 카드 본문 텍스트 안에 인라인으로 부착하던 문제. 검증 결과는 이제 카드 JSON의 `self_check` 필드 1곳에만 기록됨. (openfieldtech findings F4)
- **F2** 자체 검증 필드가 카드 사이즈(S·L1·L2·L3)에 따라 비대칭(`validation`·`structure_check` 일부 사이즈에서만 출력)이던 문제. `SelfCheckResult` 단일 스키마로 통일. (openfieldtech findings F2)
- **F7** `/techdoc-update`에 SHA-256 무결성 검증, 적용 전 자동 백업, 실패 시 자동 롤백을 추가. 변조·손상된 zip 적용을 방지하고 적용 실패 시 이전 상태로 안전하게 복원. (openfieldtech findings F7)
- **F6** researcher subagent가 Write 권한 거부 시 메인 세션이 우회 생성하여 중복 산출(`KeyRef_overlap_*`)이 만들어지던 사고 재발 방지. `scripts/preflight.py`로 사전 점검 + researcher prompt에 거부 시 행동 규약(payload 반환·우회 생성 금지) 명시 + `/techdoc-research` Step 2.5에 preflight 자동 실행. (openfieldtech findings F6, 2026-04-29 cat13/14 사고 원인 해소)

### Added

- `techdoc_core.schemas.SelfCheckResult` — 사이즈·카드 type 무관 단일 self-check 스키마 (모든 필드 optional, 역호환 유지).
- `TechCard`·`ProjectCard`·`ProductCard` dataclass에 `self_check: dict | None = None` 필드.
- `tests/test_self_check_schema.py` — F2·F4 회귀 fixture 3종 + 12 테스트.
- `scripts/update_plugin.py`: `compute_sha256`·`verify_sha256`·`fetch_sha256_for_release`·`backup_plugin`·`rollback_plugin` 5개 함수. `Release` dataclass에 `sha256_url` 필드.
- `tests/test_update_plugin.py`: SHA-256·backup·rollback·통합 흐름 13건 회귀.
- `scripts/preflight.py` + `tests/test_preflight.py` — Write 권한 사전 점검(파일 생성·정리 사이클, 4건 회귀).
- `agents/techdoc-researcher.md` 신설 섹션 "Write 권한 거부 시 행동 규약".

### Changed

- `prompts/section_write.md`·`agents/techdoc-writer.md` 자체 검증 섹션: 본문 인라인 금지 + `self_check` JSON 강제.
- `prompts/edit_rules.md` "편집하지 말아야 할 것"에 `self_check` 보호 + 본문 인라인 금지 명시.
- `commands/techdoc-update.md`: 안전 장치 단계(SHA-256·백업·롤백) 명시. 기존 "백업·롤백 없음·SHA256 미검증" 한계 표기 제거.
- `scripts/doctor.py`의 output dir 검사를 "will be created" 표기에서 실제 Write preflight 시도로 강화.
- `commands/techdoc-research.md`: Step 2.5에 preflight 자동 실행 + 거부 시 abort 흐름 추가.

### Compatibility

- SCHEMA_VERSION 0.1.0 유지 (breaking 아님). 기존 카드는 그대로 통과(누락 시 WARN).
- `.sha256` 자산이 없는 v1.1.0 이전 release를 update할 때는 경고만 출력하고 진행 (역호환).

## [1.1.0] — 2026-05-04

### 신규 슬래시 커맨드 2개

- **`/techdoc-update`** — plugin 자체를 GitHub Releases 최신 버전으로 자동 갱신. `--check`(체크만), `--force`(동일 버전 강제 재설치) 옵션. LLM 호출 0회.
- **`/techdoc-export-wiki`** — TechDoc 보고서 산출물(`document_final.json` + `KeyRef/` + `figures/` + outline glossary)을 표준 마크다운 LLM Wiki로 변환·누적. **D 하이브리드** 호환 — 옵시디언·VS Code·Cursor·Logseq·Foam·Dendron·MkDocs Material·Docusaurus·Hugo·Jekyll·GitHub/GitLab 마크다운 뷰어 등. `--vault`·`--create-vault`·`--lint`·`--mkdocs` 옵션. LLM 호출 0회.

### 통합

- `/techdoc` 커맨드에 `--export-wiki <vault>` 옵션 추가 — 보고서 생성 완료 후 마지막 단계로 wiki export 자동 실행.

### Wiki 모듈 (신규)

- `scripts/wiki/` — markers·frontmatter·conflict·filename·assets·lint·mkdocs_setup
- `scripts/wiki/builders/` — source·entity·appendix·concept·report·index·log
- `scripts/export_wiki.py` — 9단계 오케스트레이션 main + 충돌 감지 end-to-end

### 정책

- **사용자 메모 보존**: `<!-- techdoc:auto-* -->` 마커 외부는 절대 손대지 않음
- **충돌 감지**: 같은 엔티티의 핵심 사실(연도·수치·기관) 충돌 시 `> ⚠️ **정보 충돌 감지**` callout 자동 추가
- **멱등성**: 같은 입력으로 두 번 실행 시 vault 상태 동일
- **링크 형식**: 본문 표준 마크다운 `[text](path.md)`, frontmatter wiki-style `[[X]]` 유지 (옵시디언 Dataview 호환)
- **Vault 디렉토리**: `Tech/`(단수)·`Projects/`·`Products/`·`Sources/`·`Concepts/`·`Reports/`·`Assets/figures/<report>/`

### 테스트

- pytest 인프라 도입 (plugin v1.x 첫 단위 테스트)
- 85 tests pass (32 update_plugin + 53 export_wiki)
- 멱등성·사용자 메모 보존·충돌 감지 end-to-end·vault 미존재·doc 미존재 모두 통합 테스트 커버

### Changed

- 패키지 버전: 1.0.0 → 1.1.0
- 표면 표기 갱신: plugin.json·marketplace.json·pyproject.toml·CHANGELOG·__init__.py

### 보존

- 기존 11개 슬래시 커맨드·3개 subagent·26개 프롬프트 — 완전 호환
- `SCHEMA_VERSION = "0.1.0"` — 데이터 호환성 표시 유지

---

## [1.0.0] — 2026-04-29 (정식 릴리스)

### TechDoc Plugin이 차세대 정식 버전으로 승격

v0.1.0 알파의 모든 기능을 그대로 계승하면서 패키지의 책임 라인을 알파(Development Status 3)에서 정식(Development Status 5)으로 전환. 이후 TechDoc 메인 라인은 본 플러그인으로 계속 발전한다.

### Changed

- 패키지 버전: 0.1.0 → 1.0.0
- `pyproject.toml` classifier: `Development Status :: 3 - Alpha` → `5 - Production/Stable`
- 표면 표기 일괄 갱신: `plugin.json` · `marketplace.json` · `README.md` · `INSTALL.md` · `USAGE.md` · `REQUIREMENTS_TRACEABILITY.md`

### 기능 유지 (Breaking Change 없음)

- 기능·데이터 모델·프롬프트 26개·슬래시 커맨드 11개·subagent 3개 — v0.1.0과 완전 호환
- `SCHEMA_VERSION = "0.1.0"` 보존 (데이터 스키마 호환성 표시는 패키지 버전과 별개로 운영. JSON 포맷의 breaking change가 발생할 때만 별도 마이그레이션을 거쳐 갱신)

### v1.x 발전 계획 (예정)

- v1.x — Obsidian LLM Wiki 통합 (`docs/superpowers/specs/2026-04-29-obsidian-llm-wiki-design.md`)
- v1.x — Fixtures + Unit test suite + CI 연동 (기존 v0.2.0 deferred 항목 흡수)
- v1.x — 완전 오프라인 모드, 디자인 템플릿 커스터마이징, 프롬프트 오버라이드, 예시 갤러리

---

## [0.1.0] — 2026-04-23

### 최초 릴리스 — Cowork Plugin 전환 완료

기존 Python CLI `techdoc` v1.1.0을 Claude Code Cowork Plugin으로 재구성. Anthropic API 호출을 완전히 제거하고 Claude Code 세션 네이티브로 전환. 카드 시스템 + 별첨 심층분석 추가.

### Added

#### 플러그인 구조
- `.claude-plugin/plugin.json` 매니페스트 (11 commands + 3 agents 선언)
- `pyproject.toml` 재구성 — `anthropic` 의존성 제거, `pydantic`·`rapidfuzz` 추가, `[pdf,docx]` 선택적 extras

#### 11개 슬래시 커맨드 (commands/)
- `/techdoc-doctor` — 환경 진단 (15개 항목)
- `/techdoc-demo` — <3분 smoke test (fixtures 기반)
- `/techdoc-outline` — 문서 구조 설계 (3 시나리오)
- `/techdoc-research` — 5라운드 자료 조사 (researcher × 3 병렬)
- `/techdoc-write` — 섹션·카드 작성 (writer × 3 병렬)
- `/techdoc-review` — 도메인 전문가 검토 + 보완
- `/techdoc-render` — HTML+PDF+DOCX+MD 생성
- `/techdoc-resume` — 단계 단위 재실행
- `/techdoc-rewrite <card-id>` — 카드 단위 재실행 (다른 카드 보존)
- `/techdoc-deepdive <card-id>` — 별첨 심층분석 개별 생성
- `/techdoc` — 통합 파이프라인

#### 3개 Subagent (agents/)
- `techdoc-researcher` — 5라운드 본문 + 6라운드 별첨 조사, 섹션 범위 분할(A/B/C) 병렬, entity resolution
- `techdoc-writer` — 카드·별첨 작성, writer_state.json 카드 단위 resume, 구조화 이벤트 emit
- `techdoc-reviewer` — 도메인별(tech/market/policy) 전문가 검토, revision_instruction 생성

#### 26개 프롬프트 (prompts/)
- 공통 5 (_shared/): citation_rules, style_narrative, style_bullet, analysis_tags, no_ai_inference
- 카드 5: tech_card, project_card, product_card, section_analysis, card_length_rules
- 별첨 4: appendix_tech (10블록), appendix_project (11블록), appendix_selection, research_deepdive
- 조사 4: research_sites (사이트 카탈로그), research_queries, keyref_schema, ref_targets
- 작성·검토 8: outline_draft, section_write, section_revise, review_tech/market/policy, edit_rules, tech_depth

#### 10개 Python 유틸리티 (scripts/)
- `parse_toc.py` — TOC 파일 → draft_outline.json
- `select_design.py` — 디자인 자동 판별 + CSS 결합
- `build_reflist.py` — KeyRef → reference_list + 카테고리 분류
- `merge_research.py` — 3 researcher 병렬 출력 dedup·병합 (URL + rapidfuzz 제목 유사도 ≥85)
- `migrate.py` — schema_version 기반 JSON 자동 변환 프레임워크
- `generate_chart.py` — matplotlib 차트 (bar/line/pie/radar/comparison)
- `check_quality.py` — Phase A 23개 지표 (기본 12 + 기술연구 5 + 카드 6)
- `render.py` — HTML/PDF/DOCX/MD 오케스트레이션 + 카드·별첨·시각화
- `monitor.py` — writer_state.json 실시간 폴링 (tail + snapshot)
- `doctor.py` — 환경 진단 15개 항목

#### 데이터 모델 (techdoc_core/)
- `TechCard` (7블록), `ProjectCard` (7블록 + 메타), `ProductCard` (6블록) — 본문 카드
- `TechAppendix` (10블록), `ProjectAppendix` (11블록 + 메타) — 별첨 심층분석
- `Document` 확장 — schema_version + 카드 3종 + 별첨 2종 필드
- pydantic 스키마 10종 (`schemas.py`) — KeyRef/WriterState/ResearchRound/DocumentMeta/QualityReport/ReferenceList 등
- `ERROR_CODES` 23개 — `TECHDOC-Exxx` + `format_error()` 헬퍼

#### 디자인 템플릿 (design_templates/)
- `_shared/cards.css` — 카드 3종 공통 스타일 (5 디자인 공용)
- `_shared/appendix.css` — 별첨 2종 공통 스타일 (MathJax·Mermaid·벤치마크 표 포함)
- `tech_report/`, `business_plan/`, `policy_report/`, `research_report/`, `education_material/` — 5종 디자인 + config.json 색상 palette

#### 렌더러 (techdoc_core/renderers/)
- `card_renderer.py` — 카드 3종 + 별첨 2종 HTML 생성 + MathJax/Mermaid CDN 로더 + `render_all_appendices()`
- `html_renderer.py` 확장 — 카드 주입 + 별첨 삽입

### Changed

- **브랜드 명칭**: `Techdoc` → `TechDoc` (문서 표기만, 코드·CLI는 소문자 `techdoc` 유지)
- **검색 라운드**: 본문 5라운드 + 별첨 6라운드 (섹션당 21회 + 별첨당 25~30회)
- **REF 목표 (기술보고서)**: 50건 → 110~130건 (본문) + 50~70건 (별첨) = 160~280건
- **카테고리 가중**: 학술 35% + 기업 R&D 24% + 전문연구기관 18% = **77% aspirational**
- **섹션 구조**: 토픽 열거식 → **카드 중첩식** (기술 3~5 + 프로젝트 2~3 + 제품 1~2 + 종합분석 1)
- **섹션 본문 분량**: 1,500~2,500자 → 15,000~25,000자
- **전체 문서**: 15~25p → 185~325p (본문 100~150p + 별첨 85~175p)
- **실행 시간**: 15~25분 → 60~130분 (별첨 포함)

### Security

- WebSearch 결과 sanitization (프롬프트 인젝션 방어): HTML strip + 가짜 [REF-xxx] 제거 + 필드 상한
- `--ref file:` 경로 검증: 화이트리스트(CWD) + `..` 거부 + 50MB 상한 (`TECHDOC-E070/E071`)
- KeyRef pydantic 엄격 검증 (schema drift 방지)

### Design Decisions

- **Anthropic API 완전 제거**: ANTHROPIC_API_KEY 불필요, Claude Code 세션 자격증명 사용 (API 비용 0원, 팀 공유 단순화)
- **카드 레벨 체크포인트**: `writer_state.json`으로 카드 단위 resume — 60~130분 긴 파이프라인 중단 복구
- **섹션 범위 분할 (A/B/C)**: researcher·writer 각 3개 병렬 호출 시 섹션 중복 방지
- **별첨 선정 4축 스코어링**: ref_count + cross_ref_count + key_metrics_count + category_tier
- **Empty Result Graceful Degradation**: 77% 가중은 aspirational (FAIL 아님), niche 주제에서 예외 허용

### Deferred to v0.2.0

- 완전 오프라인 모드 (`--no-web-search --ref-bundle`)
- 문서 타입 사용자 정의 (`~/.techdoc/types/*.yaml`)
- 디자인 템플릿 커스터마이징
- 프롬프트 오버라이드 (`.techdoc/prompts-override/`)
- 예시 갤러리 (5종 × 샘플 PDF)
- 프롬프트 스냅샷 (`output/<run-id>/prompts-snapshot/`)
- Unit test suite + fixtures
- CI·배치 모드

### 개발 과정 (Git 커밋 히스토리)

- `f320e88` Stage 0 — 스캐폴딩 + 브랜드 TechDoc 변경
- `df77e25` Stage 1.1-1.4 — 스키마·카드·별첨 데이터 모델 + 5종 디자인
- `58184c1` Stage 1.5-1.6 — Python 유틸리티 10개
- `b076915` Stage 2 — 프롬프트 26개
- `a021e35` Stage 3 — Subagent 3개
- `04421fd` Stage 4 — Slash command 11개

---

# Legacy: `techdoc` Python CLI (이전 세대)

이하는 plugin 전환 전 Python CLI 시절의 이력입니다. 본 플러그인의 직계 조상이며, 카드·별첨 등 v1.0.0의 핵심 데이터 구조 일부는 CLI 시절 v1.1.0의 REQ-012/013/014에서 이미 설계됐습니다.

## [Legacy 1.1.0] — 2026-04-15 (`techdoc` CLI)

기존 Python CLI 버전. Cowork Plugin 전환 전.

- 시나리오별 CLI 지원 (--mode, --outline, resume)
- 기술/연구/제품 설명 수준 강화 (REQ-012~014)
- Markdown 출력 추가 (4종: HTML+PDF+DOCX+MD)
- 병렬 작성·교정 (SectionWriter, Editor 3개 동시)
- 국내/해외 자료 균형 (해외 40%+, 국제기구 3건+)
- 진행 상황 실시간 로그 (progress.log)

## [Legacy 1.0.0] — 2026-04-14 (`techdoc` CLI)

최초 Python CLI 릴리스. 11개 스킬, 13단계 파이프라인, Anthropic API 직접 호출.
