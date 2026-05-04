# Changelog

All notable changes to TechDoc Plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
