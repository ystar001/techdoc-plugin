# TechDoc Plugin v1.0.0 요구사항 추적성 매트릭스

> PLUGIN_PLAN.md v1.5에서 확정된 모든 결정이 실제 어떤 파일·코드에 반영되었는지 역추적.
> 2026-04-23 기준.

---

## 1. 핵심 설계 결정 (24개)

### 1.1 아키텍처 (4개)

| # | 결정 | 반영 위치 | 상태 |
|---|---|---|---|
| A01 | Python 패키지 유지 + 슬래시 커맨드 래퍼 | `techdoc_core/` + `commands/` | ✅ |
| A02 | AI 호출 Claude Code 네이티브 (API 제거) | `pyproject.toml` (anthropic 없음) + subagents | ✅ |
| A03 | Researcher 3개 + Writer 3개 Subagent 병렬 (섹션 범위 분할 A/B/C) | `agents/techdoc-researcher.md` + `techdoc-writer.md` + `constants.py::RESEARCHER_SECTION_GROUPS` | ✅ |
| A04 | 단계별 명령 + 통합 `/techdoc` + 카드 단위 `/techdoc-rewrite` + 별첨 `/techdoc-deepdive` | `commands/techdoc*.md` (11개) | ✅ |

### 1.2 조사·자료 (5개)

| # | 결정 | 반영 위치 | 상태 |
|---|---|---|---|
| R01 | 섹션당 21회 5라운드 심층 조사 | `prompts/research_queries.md`, `agents/techdoc-researcher.md` | ✅ |
| R02 | 기술연구 가중 77% (학술 35+기업R&D 24+연구기관 18) | `constants.py::REF_TARGETS`, `prompts/ref_targets.md` | ✅ |
| R03 | REF 목표 기술보고서 110~130 (본문 85 + 별첨 50~70) | `constants.py`, `prompts/ref_targets.md` | ✅ |
| R04 | 섹션당 REF 18~22건 | `constants.py` | ✅ |
| R05 | 타깃 사이트 카탈로그 (대학·기업 R&D·전문연구기관) | `prompts/research_sites.md` | ✅ |

### 1.3 섹션·카드 구조 (5개)

| # | 결정 | 반영 위치 | 상태 |
|---|---|---|---|
| C01 | 섹션 구조: 토픽 열거식 → 카드 중첩식 | `prompts/section_write.md`, `renderers/card_renderer.py` | ✅ |
| C02 | 카드 분량 (tech 1,500~3,500 / project 1,800~4,000 / product 1,000~2,000) | `constants.py::CARD_LENGTH_RULES` | ✅ |
| C03 | 섹션당 카드 수 (기술 3~5 + 프로젝트 2~3 + 제품 1~2 + 종합분석 1) | `constants.py::CARDS_PER_SECTION` | ✅ |
| C04 | 섹션 본문 분량 15,000~25,000자 (10~15p) | 위 조합으로 계산 | ✅ |
| C05 | 중요도별 차등 분량 (high/medium/low) | `constants.py::CARD_LENGTH_BY_IMPORTANCE`, `prompts/card_length_rules.md` | ✅ |

### 1.4 별첨 심층분석 (v1.4/v1.5 핵심) (6개)

| # | 결정 | 반영 위치 | 상태 |
|---|---|---|---|
| AP01 | 핵심 기술·프로젝트를 문서 말미 Appendix로 별도 심층분석 | `renderers/card_renderer.py::render_all_appendices`, `agents/techdoc-writer.md` | ✅ |
| AP02 | 기술 별첨 분량 15,000~40,000자 (10블록) | `constants.py::APPENDIX_LENGTH_RULES`, `models.py::TechAppendix`, `prompts/appendix_tech.md` | ✅ |
| AP03 | 프로젝트 별첨 분량 20,000~50,000자 (11블록) | 동일 (ProjectAppendix) + `prompts/appendix_project.md` | ✅ |
| AP04 | 별첨 자동 3~7개 선정 (`--deep-dive` 수동) | `prompts/appendix_selection.md`, `commands/techdoc.md` | ✅ |
| AP05 | 별첨 6라운드 추가 조사 (별첨당 25~30회) | `prompts/research_deepdive.md`, `agents/techdoc-researcher.md` (deepdive 모드) | ✅ |
| AP06 | 별첨당 전용 REF 20~30건 | `prompts/appendix_tech.md`, `appendix_project.md` | ✅ |

### 1.5 안정성·보안·운영 (4개)

| # | 결정 | 반영 위치 | 상태 |
|---|---|---|---|
| S01 | 체크포인트 단위 카드 레벨 (`writer_state.json`) | `schemas.py::WriterStateSchema`, `agents/techdoc-writer.md`, `commands/techdoc-rewrite.md` | ✅ |
| S02 | schema_version 필드 모든 JSON + `migrate.py` | `schemas.py`, `scripts/migrate.py`, `constants.py::SCHEMA_VERSION` | ✅ |
| S03 | 보안 3종 (WebSearch sanitization, --ref path 검증, pydantic 엄격 검증) | `agents/techdoc-researcher.md`, `schemas.py::KeyRefSchema` | ✅ |
| S04 | output_dir-keyed 인스턴스 격리 (동시 호출) | `scripts/monitor.py` (output_dir 인자) | ✅ |

---

## 2. 실행·사용자 경험 (7개)

| # | 결정 | 반영 위치 | 상태 |
|---|---|---|---|
| U01 | `/techdoc-doctor` 15개 환경 진단 | `scripts/doctor.py` (15 checks), `commands/techdoc-doctor.md` | ✅ |
| U02 | `/techdoc-demo` <3분 smoke test | `commands/techdoc-demo.md` | ✅ (fixtures 필요) |
| U03 | `/techdoc-rewrite <card-id>` 카드 단위 재실행 | `commands/techdoc-rewrite.md` | ✅ |
| U04 | 구조화 진행 이벤트 (카드 단위) | `scripts/monitor.py`, `schemas.py::ProgressEventSchema` | ✅ |
| U05 | 에러 프레임워크 `TECHDOC-Exxx` + 원인·수정·문서 | `schemas.py::ERROR_CODES` (23개), `format_error()` | ✅ |
| U06 | Python 의존성 선택적 extras `[pdf,docx]` | `pyproject.toml::optional-dependencies` | ✅ |
| U07 | 실행 시간 허용 60~130분 (전체 통합) | 문서·프롬프트에 명시 | ✅ |

---

## 3. 설명 수준 요구사항 (REQ-012~014)

| REQ | 원문 요구사항 | 반영 위치 | 상태 |
|---|---|---|---|
| REQ-001 | AI 추론 차단 (레퍼런스 기반) | `prompts/_shared/no_ai_inference.md`, `schemas.py::RELIABILITY_LEVELS` | ✅ |
| REQ-002 | 서술형·개조식 2종 | `prompts/_shared/style_narrative.md`, `style_bullet.md` | ✅ |
| REQ-003 | 근거 제시 원칙 (수치·연도·기관 명시) | `prompts/_shared/citation_rules.md`, `tech_depth.md` | ✅ |
| REQ-004 | 표지 4단 레이아웃 | `design_templates/*/cover.css`, `config.json::cover` | ✅ |
| REQ-005 | 사전 정의 디자인 5종 | `design_templates/` (5종) + `_shared/` 공통 | ✅ |
| REQ-006 | 국내/해외 자료 균형 (해외 40%+) | `constants.py::REF_TARGETS::min_en_ratio` | ✅ |
| REQ-007 | 사용자 참고 자료 (file/url/site) | `commands/techdoc-research.md::--ref`, `agents/techdoc-researcher.md` | ✅ |
| REQ-008 | HTML 참고문헌 링크 (원본+KeyRef 요약) | `renderers/html_renderer.py::_build_references` | ✅ |
| REQ-009 | 그림·표·차트 상세 설명 | `prompts/section_analysis.md`, `section_write.md` | ✅ |
| REQ-010 | 인용 [REF-xxx] 문장 끝 배치 | `prompts/_shared/citation_rules.md` | ✅ |
| REQ-011 | 표 목차·그림 목차·각주 인덱스 | `renderers/html_renderer.py::_build_table_figure_toc` + `_build_footnotes` | ✅ |
| **REQ-012** | **기술 설명 (논문 수준)** | **`prompts/tech_depth.md`, `tech_card.md`, `appendix_tech.md`** | ✅ |
| **REQ-013** | **연구·프로젝트 설명 (논문 수준)** | **`prompts/tech_depth.md`, `project_card.md`, `appendix_project.md`** | ✅ |
| **REQ-014** | **제품·솔루션 설명 (마케팅 자료 수준)** | **`prompts/tech_depth.md`, `product_card.md`** | ✅ |

---

## 4. 품질 검증 체계

### 4.1 Phase A 결정론적 측정 (23개, `scripts/check_quality.py`)

**기본 12개**:
- total_sections, total_word_count, total_citations, ai_estimate_count, ai_estimate_ratio
- short_sections, low_citation_sections, has_h2_all
- (추가) academic_ratio, rd_ratio, sections_without_analysis_block, total_refs_usable

**기술연구 5개** (REQ-012~014):
- tech_institution_number_patterns (대학명+수치 패턴)
- product_spec_patterns (제품+스펙 패턴)
- project_period_patterns (프로젝트+연도범위 패턴)
- academic_ratio (35%+ 목표)
- rd_ratio (24%+ 목표)

**카드 시스템 6개**:
- tech_card_total, project_card_total, product_card_total
- sections_under_tech_min, sections_under_project_min
- tech_card_block_fill_avg (85%+ 목표)
- project_card_block_fill_avg (85%+ 목표)
- undersized_tech_cards, undersized_project_cards

### 4.2 도메인 검토 (reviewer subagent)

- tech 도메인 (`prompts/review_tech.md`)
- market 도메인 (`prompts/review_market.md`)
- policy 도메인 (`prompts/review_policy.md`)
- FAIL 게이트 아닌 revision_instruction 생성

### 4.3 자체 검증 (각 subagent 내부)

- researcher: 카테고리 할당량, 빈 결과 graceful degradation
- writer: 카드당 블록 충족·길이·인용 (3회 재시도)

---

## 5. 컴포넌트 커버리지

### 5.1 Python 모듈 (techdoc_core/)

| 모듈 | 행 | 책임 |
|---|---|---|
| `__init__.py` | 4 | 버전 메타 |
| `constants.py` | 180 | REF_TARGETS, CARD_LENGTH, APPENDIX_LENGTH, ANALYSIS_TAGS, RELIABILITY, DESIGN_KEYWORDS, SCHEMA_VERSION |
| `models.py` | 900+ | Outline, Document, ReferenceList, KeyData, Reference, DataConflict, UserSource + **TechCard, ProjectCard, ProductCard, TechAppendix, ProjectAppendix** |
| `schemas.py` | 260 | pydantic 스키마 + 23개 ERROR_CODES |
| `renderers/html_renderer.py` | 433 | HTML 생성 (표지·목차·각주·상호참조) |
| `renderers/card_renderer.py` | 신규 | **카드 3종 + 별첨 2종 HTML + MathJax/Mermaid 로더** |
| `renderers/pdf_export.py` | 55 | playwright 기반 PDF |
| `renderers/docx_export.py` | 155 | python-docx 기반 DOCX |
| `renderers/md_export.py` | 223 | Markdown 편집 파일 |

### 5.2 디자인 템플릿 (design_templates/)

| 폴더 | 구성 |
|---|---|
| `_shared/` | `cards.css`, `appendix.css` (5종 디자인 공통) |
| `tech_report/` | config.json (18 components), components/cover/print.css, preview.html |
| `business_plan/` | 위와 동일 + 색상 palette 조정 |
| `policy_report/` | 위와 동일 |
| `research_report/` | 위와 동일 |
| `education_material/` | 위와 동일 |

### 5.3 Python 유틸리티 (scripts/)

| 파일 | 역할 |
|---|---|
| `parse_toc.py` | TOC 파일 → draft_outline.json |
| `select_design.py` | 디자인 자동 판별 + CSS 결합 |
| `build_reflist.py` | KeyRef → reference_list + 카테고리 분류 |
| `merge_research.py` | 3 researcher 병렬 출력 dedup·병합 |
| `migrate.py` | schema_version 기반 JSON 변환 |
| `generate_chart.py` | 명세 JSON → matplotlib PNG (bar/line/pie/radar/comparison) |
| `check_quality.py` | Phase A 23개 지표 측정 |
| `render.py` | HTML + PDF + DOCX + MD 오케스트레이션 (카드·별첨·시각화) |
| `monitor.py` | writer_state.json 실시간 폴링 (tail + snapshot) |
| `doctor.py` | 환경 진단 15개 항목 |

### 5.4 프롬프트 (prompts/, 26개)

| 그룹 | 파일 수 | 내용 |
|---|---|---|
| `_shared/` | 5 | citation_rules, style_narrative, style_bullet, analysis_tags, no_ai_inference |
| 카드 | 5 | tech_card, project_card, product_card, section_analysis, card_length_rules |
| 별첨 | 4 | appendix_tech (10블록), appendix_project (11블록), appendix_selection, research_deepdive |
| 조사 | 4 | research_sites (사이트 카탈로그), research_queries, keyref_schema, ref_targets |
| 작성·검토 | 8 | outline_draft, section_write, section_revise, review_tech/market/policy, edit_rules, tech_depth |

### 5.5 Subagent (agents/, 3개)

| Subagent | Tools | 책임 |
|---|---|---|
| `techdoc-researcher` | WebSearch, WebFetch, Read, Write, Bash, Glob | 5라운드 본문 + 6라운드 별첨, entity resolution |
| `techdoc-writer` | Read, Write, Edit, Bash, Glob | 카드·별첨 작성, writer_state 이벤트 |
| `techdoc-reviewer` | Read, Bash | 도메인별 검토, revision_instruction |

### 5.6 슬래시 커맨드 (commands/, 11개)

| # | 명령 | 단계 |
|---|---|---|
| 1 | `/techdoc-doctor` | 환경 진단 |
| 2 | `/techdoc-demo` | <3분 smoke test |
| 3 | `/techdoc-outline` | Step 1 |
| 4 | `/techdoc-research` | Step 2 (subagent × 3) |
| 5 | `/techdoc-write` | Step 5 (subagent × 3) |
| 6 | `/techdoc-review` | Step 8 |
| 7 | `/techdoc-render` | Step 12 |
| 8 | `/techdoc-resume` | 단계 단위 재실행 |
| 9 | `/techdoc-rewrite` | 카드 단위 재실행 |
| 10 | `/techdoc-deepdive` | 별첨 개별 작성 |
| 11 | `/techdoc` | 통합 파이프라인 |

---

## 6. 미반영·부분 반영 (v0.2.0 예정)

| 항목 | 상태 | 사유 |
|---|---|---|
| Fixtures (tests/fixtures/) | 🚧 구조만 존재, 파일 없음 | Stage 5.0 예정, v1.0.0은 디자인 검증만 |
| Unit test (tests/test_*.py) | 🚧 미작성 | Stage 5 예정 |
| `--no-web-search --ref-bundle` 완전 오프라인 | ❌ | v0.2.0 |
| 문서 타입 사용자 정의 (`~/.techdoc/types/`) | ❌ | v0.2.0 |
| 디자인 템플릿 커스터마이징 | ❌ | v0.2.0 |
| 프롬프트 오버라이드 (`.techdoc/prompts-override/`) | ❌ | v0.2.0 |
| CI·배치 모드 (Claude Code 세션 외) | ❌ | v0.3.0+ |
| 예시 갤러리 (5종 × 샘플 PDF) | ❌ | v0.2.0 |
| 프롬프트 스냅샷 (`output/<run-id>/prompts-snapshot/`) | ❌ | v0.2.0 |

---

## 7. autoplan 리뷰 반영 확인 (2026-04-23)

| # | 변경 | 반영 |
|---|---|---|
| A1 | 카드 레벨 resume (writer_state.json, /techdoc-rewrite) | ✅ |
| A2 | merge_research.py 신설 | ✅ |
| A3 | ProgressLogger 인스턴스 격리 | ✅ (monitor.py output_dir-keyed) |
| A4 | KeyRef pydantic 스키마 + 검증 | ✅ (schemas.py::KeyRefSchema) |
| A5 | "API 0회" → "ANTHROPIC_API_KEY 불필요" 문구 수정 | ✅ (README, 프롬프트) |
| A6 | `[pdf,docx]` 선택적 extras | ✅ (pyproject.toml) |
| A7 | WebSearch sanitization | ✅ (agents/techdoc-researcher.md) |
| A8 | `--ref file:` path 검증 | ✅ (agents/techdoc-researcher.md, commands/techdoc-research.md) |
| A9 | `/techdoc-demo` + `/techdoc-doctor` 신규 | ✅ |
| A10 | schema_version 필드 + migrate.py | ✅ |
| A11 | 구조화 진행 이벤트 | ✅ (schemas.py, monitor.py) |
| A12 | TECHDOC-Exxx 에러 프레임워크 | ✅ (schemas.py, 23개) |
| A13 | 섹션 범위 분할 (researcher A/B/C) | ✅ |
| A14 | 40~60분 vs 20~30분 모순 해결 | ✅ (60~130분 통일) |

---

## 8. 종합 커버리지

| 영역 | 계획 | 구현 | 커버리지 |
|---|---|---|---|
| 핵심 설계 결정 | 24 | 24 | **100%** |
| REQ-001~014 | 14 | 14 | **100%** |
| autoplan 개선 | 14 | 14 | **100%** |
| Python 모듈 | 10+ | 10 | **100%** |
| 디자인 템플릿 | 5 + 공통 | 5 + 공통 | **100%** |
| 프롬프트 | 26 | 26 | **100%** |
| Subagent | 3 | 3 | **100%** |
| 슬래시 커맨드 | 11 | 11 | **100%** |
| **v1.0.0 전체** | - | - | **100%** (fixtures·unit test 제외) |
| **Stage 5 (테스트)** | - | - | **예정** (v1.1.0) |

---

## 9. 파일 구조 (최종)

```
techdoc-plugin/
├── .claude-plugin/
│   └── plugin.json
├── agents/ (3)
│   ├── techdoc-researcher.md
│   ├── techdoc-writer.md
│   └── techdoc-reviewer.md
├── commands/ (11)
│   └── techdoc*.md
├── prompts/ (26)
│   ├── _shared/ (5)
│   └── *.md (21)
├── scripts/ (10)
│   └── *.py
├── techdoc_core/
│   ├── __init__.py
│   ├── constants.py
│   ├── models.py
│   ├── schemas.py
│   ├── design_templates/
│   │   ├── _shared/ (cards.css, appendix.css)
│   │   ├── tech_report/
│   │   ├── business_plan/
│   │   ├── policy_report/
│   │   ├── research_report/
│   │   └── education_material/
│   └── renderers/
│       ├── html_renderer.py
│       ├── card_renderer.py (신규)
│       ├── pdf_export.py
│       ├── docx_export.py
│       └── md_export.py
├── tests/
│   └── fixtures/ (Stage 5.0 예정)
├── docs/ (Stage 6 예정)
├── pyproject.toml
├── README.md
├── CHANGELOG.md (Stage 6 예정)
└── REQUIREMENTS_TRACEABILITY.md (이 파일)
```
