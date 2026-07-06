# TechDoc Plugin

> **AI 기술보고서 자동 생성 Claude Code 플러그인** — v1.3.0 (2026-05-13)
> 레퍼런스 100% 기반 · 카드 중첩식 섹션 · 별첨 논문 수준 심층분석 · LLM Wiki 통합 · Claude Code 네이티브

[![Version](https://img.shields.io/badge/version-1.8.0-green)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Plugin](https://img.shields.io/badge/claude--code-plugin-purple)]()

---

## 목차

- [PART Ⅰ. 개요](#part-ⅰ-개요)
  - [1. TechDoc이란](#1-techdoc이란)
  - [2. 대상 사용자](#2-대상-사용자)
  - [3. 해결하는 문제](#3-해결하는-문제)
  - [4. 설계 원칙](#4-설계-원칙)
  - [5. 빠른 체험 (Quick Start)](#5-빠른-체험-quick-start)
- [PART Ⅱ. 구조·아키텍처](#part-ⅱ-구조아키텍처)
  - [6. 전체 폴더 구조](#6-전체-폴더-구조)
  - [7. 데이터 흐름 (Data Flow)](#7-데이터-흐름-data-flow)
  - [8. 모듈 레이어](#8-모듈-레이어)
  - [9. 카드·별첨 문서 구조](#9-카드별첨-문서-구조)
- [PART Ⅲ. 주요 기능](#part-ⅲ-주요-기능)
  - [10. 9대 핵심 기능](#10-9대-핵심-기능)
  - [11. 카드 중첩식 섹션](#11-카드-중첩식-섹션)
  - [12. 별첨 심층분석](#12-별첨-심층분석)
  - [13. Evidence-First 근거 체계](#13-evidence-first-근거-체계)
  - [14. 기술연구 77% 가중](#14-기술연구-77-가중)
  - [15. 품질 검증 3단계](#15-품질-검증-3단계)
  - [16. LLM Wiki 통합 (D 하이브리드, v1.1.0 신규)](#16-llm-wiki-통합-d-하이브리드-v110-신규)
- [PART Ⅳ. 사용 예시](#part-ⅳ-사용-예시)
  - [17. 시나리오 A — 5분만에 목차 생성](#17-시나리오-a--5분만에-목차-생성)
  - [18. 시나리오 B — 본문 생성 (40~60분)](#18-시나리오-b--본문-생성-4060분)
  - [19. 시나리오 C — 별첨 포함 풀버전 (60~130분)](#19-시나리오-c--별첨-포함-풀버전-60130분)
  - [20. 시나리오 D — Wiki 누적 워크플로 (v1.1.0 신규)](#20-시나리오-d--wiki-누적-워크플로-v110-신규)
  - [21. 자주 하는 작업 패턴 6종](#21-자주-하는-작업-패턴-6종)
  - [22. 핵심 파일 예시](#22-핵심-파일-예시)
- [PART Ⅴ. 명령·옵션 레퍼런스](#part-ⅴ-명령옵션-레퍼런스)
  - [23. 슬래시 명령 전체 (18종)](#23-슬래시-명령-전체-18종)
  - [24. 주요 옵션 상세](#24-주요-옵션-상세)
- [PART Ⅵ. 운영·배포](#part-ⅵ-운영배포)
  - [25. 설치 경로 4종](#25-설치-경로-4종)
  - [26. 자체 업데이트 (v1.1.0 신규)](#26-자체-업데이트-v110-신규)
  - [27. 릴리스·상태](#27-릴리스상태)
  - [28. FAQ·트러블슈팅](#28-faq트러블슈팅)
  - [29. Notion 통합 (v1.2.0 신규)](#29-notion-통합-v120-신규)
  - [30. Autopilot 자율 모드 (v1.3.0 신규)](#30-autopilot-자율-모드-v130-신규)
- [관련 문서](#관련-문서)

---

# PART Ⅰ. 개요

## 1. TechDoc이란

TechDoc은 **AI 기술보고서 자동 생성 + LLM Wiki 누적을 지원하는 Claude Code 플러그인**입니다. 사용자가 Claude와 협업하면서:

- 모든 수치·기관·연구에 **[REF-xxx] 출처 자동 인용**
- 대학·기업 R&D·전문연구기관 레퍼런스 **77% 가중 확보**
- 기술·프로젝트·제품을 **독립 카드**로 구조화
- 핵심 대상은 **별첨 심층분석**(기술 15k~40k자 / 프로젝트 20k~50k자)
- 3개 Subagent(researcher·writer·reviewer) **병렬 협업**
- HTML · PDF · DOCX · MD **4종 동시 생성**
- ⭐ **LLM Wiki 누적** (D 하이브리드: 옵시디언·MkDocs·표준 마크다운 호환)
- ⭐ **자체 업데이트** (`/techdoc-update`로 새 버전 자동 갱신)

하도록 설계된 **18종 슬래시 명령 + 3종 Subagent + 25종 프롬프트(+공통 6종) + 14+ Python 모듈**의 종합 도구입니다.

## 2. 대상 사용자

| 대상 | 얻는 가치 |
|---|---|
| **기술기획 부서** | 기술동향·R&D 보고서 작성 시간 단축, 참고문헌 자동 정리, 주제별 영속 지식 베이스 |
| **R&D 연구소** | 기술 리뷰 논문·백서·특허 조사 자동화, 누적되는 기술 wiki |
| **컨설팅 수행사** | 클라이언트별 기술 분석 보고서 템플릿화, 도메인 지식 누적 |
| **투자·사업 기획** | 시장·경쟁사·기술 트렌드 통합 보고서, 의사결정 근거 추적 |
| **학술·연구 기관** | 선행 연구 문헌 조사·리뷰 논문 초안 생성, 주제 지식 그래프 |

## 3. 해결하는 문제

기술보고서 작성의 **실질 고질병**에 각각 대응합니다.

| 고질병 | 기존 방식 | TechDoc 해결 |
|---|---|---|
| "이 수치 어디서 나왔지?" **출처 불명 인용** | 에디터 메모 | `[REF-xxx]` 각주 + `KeyRef/` 원문 보관 + 품질 등급 |
| 기술·프로젝트가 **스쳐 지나감** (3~5줄씩 나열) | 한 섹션에 열거 | **카드 중첩식** (기술 7블록·프로젝트 7블록·제품 6블록 독립 카드) |
| 논문 수준 심층 설명이 **본문에 들어가면 가독성 파괴** | 선택·희생 | **별첨 심층분석** (기술 10블록 15k~40k자 / 프로젝트 11블록 20k~50k자) |
| 해외·학술·기업 R&D **레퍼런스 부족** | 한국 뉴스·정부만 | **77% 가중**: 학술 35% + 기업 R&D 24% + 연구기관 18% |
| 긴 파이프라인 중단 시 **전부 다시 작성** | 처음부터 | 카드 단위 `/techdoc-rewrite` · 별첨 단위 `/techdoc-deepdive` |
| API 키 관리·비용 | `.env` ANTHROPIC_API_KEY 필수 | **Claude Code 세션 네이티브** (API 키 불필요) |
| 팀 공유 복잡 | 각자 pip install | `/plugin install` 한 줄 |
| 특정 카드만 마음에 안 듦 | 전체 재작성 | `/techdoc-rewrite <card-id>` (다른 카드 보존) |
| **보고서 결과가 일회성** | 한 번 만들고 끝 | ⭐ **LLM Wiki 누적** — 같은 주제 vault에 시간이 갈수록 풍부해지는 영속 지식 |
| **수동 plugin 업그레이드** | zip 다운로드·압축 해제 | ⭐ **`/techdoc-update`** 한 줄로 GitHub Releases 최신 자동 갱신 |

## 4. 설계 원칙

TechDoc은 다음 8개 원칙 위에 구현되었습니다.

1. **Evidence-First** — 출처 없는 수치·기관명은 금지. `[REF-xxx]` 인용 없는 구체 서술 불가.
2. **카드 중첩식 구조** — "1 섹션 = N 카드 + 종합분석". 기술·프로젝트·제품을 독립 단위로.
3. **본문 ↔ 별첨 분리** — 본문 카드는 개괄, 별첨은 논문 수준 리뷰. 가독성·깊이 양립.
4. **기술연구 가중** — 학술·기업 R&D·전문연구기관 합계 77% aspirational target.
5. **Subagent 병렬화** — researcher × 3 (섹션 A/B/C 분할), writer × 3 병렬 작성.
6. **카드 단위 체크포인트** — `writer_state.json`으로 카드 단위 resume 지원.
7. **Claude Code 네이티브** — API 키·별도 구독 불필요. Claude Code 세션 자격증명만 사용.
8. **D 하이브리드 출력** ⭐ — Wiki를 표준 마크다운으로 출력해 옵시디언·VS Code·MkDocs·Logseq·Foam·Hugo·Jekyll 등 모두 호환.

## 5. 빠른 체험 (Quick Start)

### A. 3분 안에 설치

```bash
# 1. ZIP 다운로드
# https://github.com/ystar001/techdoc-plugin/releases/tag/v1.1.0

# 2. 압축 해제
unzip techdoc-plugin-v1.1.0.zip -d ~/.claude/plugins/techdoc-plugin

# 3. Python 의존성
cd ~/.claude/plugins/techdoc-plugin && pip install -e ".[pdf,docx]"
playwright install chromium

# 4. Claude Code 등록
/plugin marketplace add ~/.claude/plugins/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
/reload-plugins
/techdoc-doctor                       # 15개 항목 모두 [OK] 확인
```

### B. 5분 안에 첫 목차 생성

```
/techdoc-outline "5G 네트워크 기술 동향 보고서"
```

→ 30초 내 `output/draft_outline.json` (10섹션 구조 자동 생성).

### C. 60~130분 안에 풀버전 보고서 + Wiki 누적

```
/techdoc "AI 반도체 기술보고서" \
  --toc ./toc.txt \
  --domain tech \
  --style 서술형 \
  --deep-dive-auto 5 \
  --export-wiki ~/Obsidian/AI반도체
```

→ 본문 100~150페이지 + 별첨 5개 × 15~35페이지 + HTML/PDF/DOCX/MD + **vault에 wiki 누적** (Tech·Projects·Products·Sources·Concepts·Reports 카테고리별 페이지).

전체 설치 경로 4종은 [25절](#25-설치-경로-4종) 참조.

---

# PART Ⅱ. 구조·아키텍처

## 6. 전체 폴더 구조

```
techdoc-plugin/                                  # 플러그인 루트 (v1.1.0)
│
├── .claude-plugin/                              # 플러그인 매니페스트
│   ├── plugin.json                              # 이름·버전·설명
│   └── marketplace.json                         # 자체 마켓플레이스
│
├── commands/                                    # 18종 슬래시 명령
│   ├── techdoc.md            techdoc-outline.md
│   ├── techdoc-research.md   techdoc-write.md
│   ├── techdoc-review.md     techdoc-render.md
│   ├── techdoc-resume.md     techdoc-rewrite.md
│   ├── techdoc-deepdive.md   techdoc-doctor.md
│   ├── techdoc-demo.md       techdoc-update.md          # ⭐ v1.1.0
│   ├── techdoc-export-wiki.md                           # ⭐ v1.1.0
│   ├── techdoc-export-notion.md                         # ⭐ v1.2.0
│   ├── techdoc-autopilot.md                             # ⭐ v1.3.0
│   ├── techdoc-autopilot-status.md                      # ⭐ v1.3.0
│   ├── techdoc-autopilot-stop.md                        # ⭐ v1.3.0
│   └── techdoc-autopilot-resume.md                      # ⭐ v1.3.0
│
├── agents/                                      # 3종 Subagent
│   ├── techdoc-researcher.md                    # 5+6라운드 조사
│   ├── techdoc-writer.md                        # 카드·별첨 작성
│   └── techdoc-reviewer.md                      # 도메인 검토
│
├── prompts/                                     # 25종 프롬프트(+공통 6종)
│   ├── _shared/                                 # 공통 (5종)
│   ├── tech_card.md  project_card.md  product_card.md
│   ├── appendix_tech.md  appendix_project.md
│   ├── research_sites.md  research_queries.md
│   └── ... (기타 프롬프트)
│
├── scripts/                                     # Python 유틸
│   ├── parse_toc.py       select_design.py
│   ├── build_reflist.py   merge_research.py
│   ├── migrate.py         generate_chart.py
│   ├── check_quality.py   format_gate.py             # 서식 게이트(self_model)
│   ├── render.py          monitor.py     doctor.py
│   ├── build_release.py
│   ├── update_plugin.py                                 # ⭐ v1.1.0
│   ├── export_wiki.py                                   # ⭐ v1.1.0
│   └── wiki/                                            # ⭐ v1.1.0 신규
│       ├── markers.py      frontmatter.py
│       ├── filename.py     conflict.py
│       ├── assets.py       lint.py
│       ├── mkdocs_setup.py  postprocess.py    # postprocess: ⭐ v1.6.0 (F18)
│       └── builders/
│           ├── source.py   entity.py
│           ├── appendix.py concept.py
│           ├── report.py   index.py
│           └── log.py
│
├── techdoc_core/                                # 데이터 모델·렌더러
│   ├── __init__.py  constants.py  models.py  schemas.py
│   ├── renderers/                               # 4종 출력
│   │   ├── html_renderer.py  card_renderer.py
│   │   ├── pdf_export.py     docx_export.py
│   │   └── md_export.py
│   └── design_templates/                        # 5종 디자인
│       ├── _shared/                             # 공통 CSS (cards·appendix)
│       ├── tech_report/      business_plan/
│       ├── policy_report/    research_report/
│       └── education_material/
│
├── tests/                                       # ⭐ v1.1.0 pytest 인프라
│   ├── __init__.py    conftest.py
│   ├── test_update_plugin.py    (32 tests)
│   └── test_export_wiki.py      (53 tests)
│
├── README.md  USAGE.md  INSTALL.md  CHANGELOG.md
├── REQUIREMENTS_TRACEABILITY.md
├── pyproject.toml
└── LICENSE
```

> **테스트 컨벤션 (재사용성):** 프로젝트 특화 검증은 `@pytest.mark.project`로 분리 — 자식 프로젝트는 `pytest -m "not project"`로 코어만 실행(재사용성, F23). 컨벤션: `tests/README.md`.

## 7. 데이터 흐름 (Data Flow)

```
┌────────────────────────────────────────────────────────────┐
│                 사용자 (기술기획·R&D)                       │
│                         │                                   │
│                         ▼                                   │
│            Claude Code + TechDoc Plugin                    │
│                         │                                   │
│    ┌────────────────────┴────────────────────┐             │
│    ▼                                          ▼             │
│ 슬래시 명령 (/techdoc-*)            Python 유틸 (scripts/) │
│    │                                          │             │
│    └──────────────┬───────────────────────────┘             │
│                   ▼                                         │
│       ┌───────────────────────────┐                         │
│       │ 메인 Claude 세션 (오케스트레이터) │                  │
│       │  WebSearch · WebFetch · Read · Bash                 │
│       └──┬──────────┬──────────┬─┘                          │
│          ▼          ▼          ▼                            │
│    ┌──────────┬──────────┬──────────┐                      │
│    │researcher│  writer  │ reviewer │ (격리 컨텍스트 병렬) │
│    │    × 3   │    × 3   │          │                      │
│    └─────┬────┴─────┬────┴──────┬───┘                      │
└──────────┼──────────┼───────────┼──────────────────────────┘
           ▼          ▼           ▼
┌───────────────────────────────────────────────────────────┐
│                      데이터 계층                           │
│                                                            │
│  KeyRef/*.md   ◄──►   reference_list.json                 │
│   (REF 원문·YAML)      (카테고리 분류·비율)               │
│       │                      │                             │
│       ▼                      ▼                             │
│  document_draft.json (카드 + 별첨)                        │
│       │                                                    │
│       ▼                                                    │
│  writer_state.json (카드 단위 상태·resume)                │
│       │                                                    │
│       ▼                                                    │
│  보고서_*.{html,pdf,docx,md} (최종 산출물)                │
│       │                                                    │
│       ▼ (--export-wiki 옵션 시)                            │
│  vault/{Sources,Tech,Projects,Products,Concepts,Reports}  │ ⭐ v1.1.0
│  ├── 각 페이지: frontmatter + 본문 + AI 영역 마커          │
│  └── log.md · index.md (자동 갱신)                         │
└───────────────────────────────────────────────────────────┘
```

**핵심 원칙**: KeyRef·reference_list가 **Single Source of Truth**. 문서·별첨·차트·wiki 페이지는 모두 여기서 파생. `writer_state.json`이 카드·별첨 단위 진행 상태를 실시간 기록.

## 8. 모듈 레이어

Python 구현은 4개 계층으로 구성됩니다.

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4  오케스트레이션                                  │
│   render.py (전체 렌더링 플로)                           │
│   build_release.py (배포 ZIP 빌드)                       │
│   update_plugin.py (자체 갱신, v1.1.0)                   │
│   export_wiki.py (wiki 통합, v1.1.0)                     │
├─────────────────────────────────────────────────────────┤
│ Layer 3  품질·진단·마이그레이션                          │
│   check_quality.py (Phase A 23지표)                      │
│   doctor.py (환경 진단 15항목)                           │
│   migrate.py (schema_version 변환)                       │
│   monitor.py (writer_state 실시간 폴링)                  │
├─────────────────────────────────────────────────────────┤
│ Layer 2  데이터 가공                                     │
│   merge_research.py (3 researcher 출력 dedup·병합)       │
│   build_reflist.py (KeyRef → reference_list 분류)        │
│   generate_chart.py (차트 5종)                           │
│   wiki/builders/* (vault 페이지 빌더 7종, v1.1.0)        │
│   wiki/conflict.py (충돌 감지, v1.1.0)                   │
├─────────────────────────────────────────────────────────┤
│ Layer 1  기반                                            │
│   parse_toc.py · select_design.py                        │
│   techdoc_core (models · schemas · constants · renderers)│
│   wiki/markers.py · frontmatter.py · filename.py · assets.py · lint.py · mkdocs_setup.py (v1.1.0) │
└─────────────────────────────────────────────────────────┘
```

**의존 규칙**: 상위 계층만 하위 계층을 import. 동일 계층 간 의존 최소화.

## 9. 카드·별첨 문서 구조

TechDoc의 핵심 혁신 — 섹션은 **카드의 집합**이고, 핵심 카드는 **별첨**에서 심층 분석.

| 레벨 | 요소 | 분량 | 역할 |
|---|---|---|---|
| 섹션 | 개요 문단 | 100~200자 | 다룰 기술·프로젝트 지도 |
| 섹션 | **기술 카드** (7블록) | 1,500~3,500자 | 특정 기술 개괄 |
| 섹션 | **프로젝트 카드** (7블록+메타) | 1,800~4,000자 | 프로젝트 개괄 |
| 섹션 | **제품 카드** (6블록) | 1,000~2,000자 | 상용 제품 개괄 |
| 섹션 | 종합 분석 | 800~1,200자 | 비교·타임라인·차트 |
| **별첨** | **기술 심층분석** (10블록) | **15k~40k자 (15~35p)** | 논문 수준 리뷰 |
| **별첨** | **프로젝트 심층분석** (11블록) | **20k~50k자 (20~40p)** | 박사논문 수준 |

**섹션 10개 문서 기본 구성** (`--deep-dive-auto 5` 기준):
- 본문 100~150페이지 (섹션당 10~15p)
- 별첨 5개 × 15~35p = 85~175페이지
- **총 185~325페이지 전문 보고서**

---

# PART Ⅲ. 주요 기능

## 10. 9대 핵심 기능

### 🎯 기능 1 — TOC 파싱 + AI 구조 생성 (`/techdoc-outline`)

사용자 TOC 파일 자동 파싱 (`parse_toc.py`) 또는 AI가 10개 섹션 구조 자동 설계. 3가지 모드:
- **exact**: TOC 그대로 사용
- **enhance**: AI가 subtopics 보강·재배열
- **(TOC 없음)**: 완전 자동 생성

`parse_toc`는 평문 TOC와 **마크다운 표 TOC**(`| ID | 제목 | … | Sizing | … |`)를 자동 판별한다. 표의 Sizing 칼럼(S/M/L/XL)은 `estimated_length`로 매핑되며("제목" 칼럼이 있는 표만 항목 표로 인식해 메타·매핑 표는 제외), 카드 ID는 숫자뿐 아니라 **영숫자 prefix(R·G1·AP·A-1)** 를 지원한다.

### 📚 기능 2 — 5라운드 심층 조사 (`/techdoc-research`)

3개 researcher subagent 병렬 (섹션 범위 A/B/C 분할):

| 라운드 | 목적 | 횟수 |
|---|---|---|
| 1. 광범위 | 주제 지형 파악 | 6회/섹션 |
| 2. 대학 타깃 | arxiv, IEEE, ACM, mit.edu 등 | 5회 |
| 3. 기업 R&D | Google Research, Meta AI, Samsung 등 | 4회 |
| 4. 전문연구기관 | ETRI, KIST, Fraunhofer 등 | 3회 |
| 5. 인용·최신 | cited-by, 2024~2026 | 3회 |
| **합계** | | **21회/섹션** |

### 🎴 기능 3 — 카드 기반 섹션 작성 (`/techdoc-write`)

3개 writer subagent 병렬. 각 섹션을 개요 + 카드 3종 + 종합분석으로 조립. 카드당 자체 검증 (블록·인용·길이).

### 📖 기능 4 — 별첨 심층분석 (`/techdoc-deepdive`)

본문 카드 대비 **10배 분량**으로 리뷰 논문 수준 작성. 전용 6라운드 추가 조사 (25~30회/별첨).

### 👥 기능 5 — 도메인 전문가 검토 (`/techdoc-review`)

tech · market · policy · **consistency**(표기 일관성 — 약어·기관명·외래어·참고문헌·glossary) 4개 도메인 중 선택. reviewer subagent가 카드·별첨 단위로 `revision_instruction` 생성 → writer가 **외과적 수정** (다른 카드 보존). `/techdoc-outline` 단계에서 `extract_glossary`가 KeyRef·카드에서 약어·용어를 자동 추출해 `outline.glossary`를 채우며(비면 WARN), `check_quality`가 표기 일관성을 측정한다 (v1.4).

### 🔄 기능 6 — 카드 단위 재실행 (`/techdoc-rewrite`)

특정 카드 ID만 재작성. `writer_state.json` 기반. 다른 69개 카드는 그대로.

### 📑 기능 7 — 4종 문서 동시 생성 (`/techdoc-render`)

HTML (마스터) + PDF + DOCX + MD. 카드·별첨·MathJax 수식·Mermaid 다이어그램·matplotlib 차트 자동 포함. MD 출력은 단락 break(`renderers/paragraph`, 키워드+800자 ceiling, F10)·섹션 키 한글 헤딩(`renderers/section_heading`, F12) 적용. Part 라우팅은 `routing_config`로 외부화(F21, 프로젝트별 config 교체). `--tree`로 config 기반 트리 디렉토리 출력(`renderers/markdown_tree`, F15) — Part/시리즈 + 계층 INDEX, split 카드 병합, 단일 시리즈 INDEX 생략(F17).

### 🌐 기능 8 — LLM Wiki 누적 (`/techdoc-export-wiki`) ⭐ v1.1.0

보고서 산출물을 표준 마크다운 wiki로 변환·누적. 같은 주제 vault에 여러 보고서를 누적하면 엔티티 페이지가 시간이 갈수록 풍부해짐 (Karpathy LLM Wiki 비전).

- **D 하이브리드**: 옵시디언·VS Code·Cursor·Logseq·Foam·Dendron·MkDocs Material·Docusaurus·Hugo·Jekyll·GitHub/GitLab 마크다운 뷰어 모두 호환
- **충돌 감지**: 같은 엔티티의 다른 보고서가 다른 수치(연도·기관 등)를 가지면 페이지에 `> ⚠️ **정보 충돌 감지**` callout 자동 추가
- **사용자 메모 보존**: `<!-- techdoc:auto-* -->` 마커 외부의 사용자 메모는 재export에도 절대 손대지 않음
- **MkDocs 옵션** (`--mkdocs`): vault에 mkdocs.yml 자동 생성 → `mkdocs build`로 정적 사이트
- **후처리** ⭐ v1.6.0 (`--enhance`, 기본 on): "학술" 과잉 수식어 정리·메타 표시(`(확장)`) 제거·긴 문단 분리·영문 slug 부분 한국어화·문서 안내 섹션. `[REF]`·수치·고유명사 보존, AI 마커 영역만 적용. `--no-enhance`로 비활성 (F18)
- **LLM 호출 0회** (결정론적 변환)

### 🔧 기능 9 — Plugin 자체 업데이트 (`/techdoc-update`) ⭐ v1.1.0

GitHub Releases에서 최신 zip을 자동 다운로드·교체. 사용자가 매번 zip 다운로드 + 압축 해제 + 재등록할 필요 없음.

```bash
/techdoc-update --check    # 새 버전 체크만
/techdoc-update            # [y/N] 확인 후 자동 적용
```

LLM 호출 0회. 결정론적 흐름. 자세한 사용은 [26절](#26-자체-업데이트-v110-신규).

## 11. 카드 중첩식 섹션

### 기술 카드 7블록

| # | 블록 | 분량 | 예시 |
|---|---|---|---|
| 1 | 기술 개요·배경 | 300자 | 등장 배경·해결 문제 |
| 2 | 작동 원리 | 600~800자 | 알고리즘·프로토콜 단계별 |
| 3 | 구성 요소 (HW/SW) | 300~400자 | 역할·상호작용 |
| 4 | 성능 지표 | 300~400자 | 정량 수치 + 맥락 해석 |
| 5 | 기술적 장단점 | 300~400자 | 근거 있는 비교 |
| 6 | 차별점·한계·발전방향 | 300~400자 | 분석적 서술 |
| 7 | 근거·인용 | 200자 | [REF-xxx] 3~5건 |

### 프로젝트 카드 7블록 + 메타

메타 헤더: 기관·PI·기간·예산·자금원 5개 필드.

### 제품 카드 6블록 + 메타

메타 헤더: 모델명·제조사·국가 3개 필드.

### 본문 카드 시각 필드 (v1.4)

본문 카드(tech/project/product)는 블록 외에 선택적 `figures`(`{path, caption}` — `generate_chart`로 렌더)·`diagrams`(`{mermaid, caption}`) 필드를 가질 수 있다. 렌더러가 HTML `<figure>`·Mermaid로 출력하며 MD/PDF에도 보존된다 (별첨 전용이던 시각 필드를 본문 카드로 확장).

### 섹션당 카드 수 (기본)

| 유형 | 개수 |
|---|---|
| 기술 카드 | 3~5개 |
| 프로젝트 카드 | 2~3개 |
| 제품 카드 | 1~2개 |
| 종합 분석 | 1개 (매트릭스·타임라인·차트·요약) |

## 12. 별첨 심층분석

### 기술 심층분석 10블록 (15k~40k자, 권장 20~25k)

| # | 블록 | 분량 |
|---|---|---|
| 1 | 기술 개요·연구사 | 1,500~2,000자 |
| 2 | **수학·물리 원리** (MathJax 수식) | 3,000~4,000자 |
| 3 | **상세 알고리즘** (의사코드 3~5개, Mermaid) | 5,000~6,500자 |
| 4 | 구현 아키텍처 (컴포넌트 다이어그램) | 2,500~3,000자 |
| 5 | **성능 벤치마크** (10지표 × 10대상) | 3,000~4,000자 |
| 6 | 주요 구현체·오픈소스 | 1,500~2,000자 |
| 7 | 연구 동향 타임라인 | 1,500~2,000자 |
| 8 | 한계·미해결 과제 (이론/실용/윤리/경제) | 2,500~3,000자 |
| 9 | 미래 연구 방향 | 1,500~2,000자 |
| 10 | 전문 참고문헌 | **20~30건** |

### 프로젝트 심층분석 11블록 (20k~50k자, 권장 25~30k)

| # | 블록 | 분량 |
|---|---|---|
| 1 | 프로젝트 연대기 | 2,000~2,500자 |
| 2 | 연구 체계 + 조직도 | 1,500~2,000자 |
| 3 | 단계별 기술 접근 (Phase 1/2/3) | 5,000~6,000자 |
| 4 | **실험 설계 상세** | 4,500~5,500자 |
| 5 | 데이터셋·리소스 | 1,500~2,000자 |
| 6 | **핵심 결과 심층** (통계 유의성) | 5,500~6,500자 |
| 7 | 파생·후속 연구 | 2,500~3,000자 |
| 8 | 경쟁·보완 프로젝트 비교 | 2,500~3,000자 |
| 9 | 상업화·산업 응용 | 1,500~2,000자 |
| 10 | 핵심 연구자 프로필 | 1,500~2,000자 |
| 11 | 전문 참고문헌 | **25~40건** |

### 자동 선정 로직 (`appendix_selection.md`)

`--deep-dive-auto N`: importance=high 카드 중 **4축 스코어링** 상위 N개:
- `ref_count` (확보된 REF 수)
- `cross_ref_count` (여러 섹션 걸친 중요도)
- `key_metrics_count` (구체 수치 다양성)
- `category_tier` (학술·기업 R&D 우선)

## 13. Evidence-First 근거 체계

### 신뢰도 4등급 자동 부여

| 등급 | 기준 | 인용 가능 여부 |
|---|---|---|
| **확인됨** | 2개 이상 독립 출처 교차 확인 | ✅ |
| **단일출처** | 공신력 있는 1개 출처 | ✅ |
| **미확인** | 출처 이름은 있으나 원본 접근 불가 | ❌ |
| **AI지식** | 검색으로 확인 못 함 | ❌ |

`check_quality.py`가 미확인·AI지식 인용을 자동 탐지해 FAIL.

### KeyRef YAML 구조

```yaml
---
schema_version: "0.2.0"
id: REF-023
category: 학술                # 정부공공|국제기구|학술|기업R&D|전문연구기관|산업시장|뉴스
source: MIT CSAIL
authors: [Park, J., Smith, K.]
year: 2024
venue: IEEE IoT Journal
title: "Low-power LoRa mesh for precision irrigation"
url: https://...
reliability: 확인됨
related_sections: ["1.1", "2.3"]
key_numbers:
  - "정확도 94.3% (기존 81% 대비 13.3%p 향상)"
technologies:
  - name: "LoRa-Mesh Precision Irrigation"
    importance: high
projects:
  - name: "SMART-IRRI-2024"
    pi: "Dr. Park, Junho"
    period: "2023.01-2025.12"
    budget: "$3.2M"
    importance: high
---

원문 요약 또는 핵심 발췌...
```

## 14. 기술연구 77% 가중

### 카테고리 할당 (기술보고서 기준)

| 카테고리 | 목표 비율 | 예시 |
|---|---|---|
| **학술 (대학)** | **35%** | arxiv·IEEE·ACM·Nature·MIT·Stanford·RISS·DBpia |
| **기업 R&D** | **24%** | Google Research·Meta AI·Samsung·LG·특허 |
| **전문연구기관** | **18%** | ETRI·KIST·Fraunhofer·CSIRO·RIKEN·NIST |
| 산업시장 | 7% | Gartner·IDC·MarketsandMarkets |
| 정부공공 | 6% | 정부 통계·공공 데이터 |
| 국제기구 | 5% | FAO·OECD·World Bank·IEA |
| 뉴스 | 5% | 산업 뉴스·일간지 |

**77% = 학술 + 기업 R&D + 전문연구기관 aspirational target**. niche 주제에서는 예외 허용 (FAIL 게이트 아님).

## 15. 품질 검증 3단계

### Phase A: 결정론적 측정 23개 지표 (`check_quality.py`)

| 카테고리 | 지표 수 | 예시 |
|---|---|---|
| 기본 | 12 | 섹션 길이·인용 수·AI추정 비율·h2 여부·용어 일치 |
| 기술연구 | 5 | 대학+수치 패턴·기업+제품 스펙·학술 비율≥35%·R&D≥24% |
| 카드 시스템 | 6 | 섹션당 카드 수·7블록 충족률·최소 길이·종합분석 존재 |

self_model 모드는 추가로 **서식 게이트**(`scripts/format_gate.py`)를 적용한다 — 리스트 비율·인라인 계층번호 `(i)(ii)`·평문 라벨 `(a)(b)`·비-불릿/평탄화 들여쓰기·중복 요약·제어문자(BEL·BS·VT·FF·CR)·mermaid 라벨 미인용·인라인 병렬 열거(첫째/둘째)를 측정하고, 전부 WARNING 기본·`--strict`로 구조 결함(제어문자 포함) FAIL 차단·optional `--baseline`으로 재작성 회귀(REF·수치·분량)를 검사한다. 문서 단위로 캡션(`표·그림 N-M`) 유일성·순번·참조 정합도 점검한다 (findings F27·F28·F30·F37·F39·F40·F41·F42).

### Phase B: Subagent 도메인 검토

3개 도메인 중 선택: `tech` · `market` · `policy`. 카드·별첨 단위 `revision_instruction` 생성.

### 카드 단위 자체 검증 (writer subagent)

각 카드 작성 후:
- [ ] 모든 블록 채움 (tech 7 / project 7 / product 6)
- [ ] [REF-xxx] 인용 최소 5건
- [ ] 최소 분량 (중요도별) 충족
- [ ] AI 추정 표현 < 30%
- [ ] `[근거 미확인]` 잔존 없음

미달 시 해당 카드 재작성 (최대 3회). 3회 초과 시 `TECHDOC-E030` 기록.

## 16. LLM Wiki 통합 (D 하이브리드, v1.1.0 신규)

보고서 산출물을 표준 마크다운 wiki로 변환·누적해 **영속 지식 자산**으로 만듭니다.

### 카테고리별 페이지 구조

| 디렉토리 | 출처 | 단위 |
|---|---|---|
| `Sources/REF-*.md` | reference_list.json + KeyRef/*.md | 참고문헌 1건 |
| `Tech/<name>.md` | document_final.json["tech_cards"][] | 기술 카드 (7블록) |
| `Tech/<name>_appendix.md` | document_final.json["tech_appendices"][] | 기술 별첨 (10블록) |
| `Projects/<name>.md` | project_cards[] (+ meta 평탄화) | 연구·프로젝트 카드 |
| `Projects/<name>_appendix.md` | project_appendices[] | 프로젝트 별첨 (11블록) |
| `Products/<name>.md` | product_cards[] | 제품 카드 (6블록) |
| `Concepts/<term>.md` | outline.glossary | 용어 정의 |
| `Reports/<title>.md` | document_final.json | 보고서 MOC |
| `Assets/figures/<report>/` | figures/*.png | 차트·다이어그램 |
| `index.md`, `log.md` | 자동 생성 | vault 카탈로그·이력 |

### D 하이브리드 호환

본문은 표준 마크다운 `[text](path.md)`, frontmatter만 옵시디언 wiki-style `[[X]]` 유지.

| 도구 | 동작 |
|---|---|
| 옵시디언 | vault 그대로 사용. Dataview 쿼리·그래프뷰·백링크 모두 동작 |
| VS Code / Cursor | 마크다운 그대로. Foam extension 권장 |
| Logseq · Foam · Dendron | vault 그대로 |
| MkDocs Material | `--mkdocs` 옵션으로 mkdocs.yml 자동 생성 → `mkdocs build` |
| Docusaurus · Hugo · Jekyll | docs 디렉토리로 사용 |
| GitHub / GitLab | repo로 push → 자동 마크다운 렌더 |

### 충돌 감지 (자동)

같은 엔티티의 다른 보고서가 핵심 사실(연도·수치·기관)에서 다른 값을 가지면 페이지에 자동 callout 추가:

```markdown
> ⚠️ **정보 충돌 감지**
> **연도**:
> - 기존: 2024
> - 신규: 2025
```

LLM 호출 없이 정규식·휴리스틱 기반.

### 사용자 메모 보존

페이지에 사용자가 직접 추가한 메모는 절대 보존:

```markdown
---
type: tech
name: 점적관개
---

> 사용자가 직접 추가한 메모 (자유 편집 — 보존됨)

<!-- techdoc:auto-start -->
... AI가 관리하는 영역 (재export 시 갱신) ...
<!-- techdoc:auto-end -->

> 또 다른 사용자 메모 (보존됨)
```

---

# PART Ⅳ. 사용 예시

## 17. 시나리오 A — 5분만에 목차 생성

**상황**: 주제만 있고 목차도 없는 상태. 빠르게 구조 설계.

```
/techdoc-outline "5G 네트워크 기술 동향 보고서"
```

**결과** (30초 내):
- `output/draft_outline.json` (10개 섹션 자동 설계)
- 각 섹션: 제목 + subtopics 3~6개 + analysis_tags

사용자 검토·수정 후 다음 단계 진행.

## 18. 시나리오 B — 본문 생성 (40~60분)

**상황**: TOC 확정. 본문만 빠르게 (별첨 없음).

```bash
/techdoc "스마트농업 기술 보고서" \
  --toc ./my_toc.txt \
  --domain tech \
  --style 서술형 \
  --no-deep-dive
```

**산출물**:
- 본문 100~150페이지 (섹션 10개)
- 각 섹션: 기술 카드 3~5 + 프로젝트 카드 2~3 + 제품 카드 1~2 + 종합분석
- REF 85~130건
- HTML + PDF + DOCX + MD

## 19. 시나리오 C — 별첨 포함 풀버전 (60~130분)

**상황**: 완전판. 본문 + 핵심 5개 별첨 심층분석.

```bash
/techdoc "AI 반도체 기술보고서" \
  --toc ./toc.txt \
  --domain tech \
  --deep-dive-auto 5 \
  --depth standard
```

**산출물**:
- 본문 100~150p (카드 70개)
- 별첨 5개 × 15~35p = 85~175p
- **총 185~325p 전문 보고서**
- REF 225~280건 (본문 110~130 + 별첨 100~150)
- 시각화 28개 (차트 10 + 별첨 18)

## 20. 시나리오 D — Wiki 누적 워크플로 (v1.1.0 신규)

**상황**: 같은 주제로 여러 보고서를 작성하며 영속 지식 베이스 구축.

```bash
# 첫 보고서 + 같은 vault에 누적
/techdoc "노지 스마트농업 분석" --toc ./toc1.txt --domain tech \
  --export-wiki ~/Obsidian/스마트농업

# 다른 보고서 — 같은 vault에 추가 → 같은 엔티티 페이지에 정보 합쳐짐
/techdoc "스마트팜 로드맵 2030" --toc ./toc2.txt --domain tech \
  --export-wiki ~/Obsidian/스마트농업

# 기존 보고서를 사후 vault로 통합
/techdoc-export-wiki --doc ./output/v1_final \
                     --vault ~/Obsidian/스마트농업 \
                     --create-vault \
                     --mkdocs   # 정적 사이트 옵션
```

**누적 효과**:
- 첫 export: vault에 50개 페이지 생성
- 두 번째 export: 같은 엔티티(예: "점적관개")가 등장하면 그 페이지에 보고서별 섹션 추가 + 충돌 감지
- 시간이 갈수록 vault가 풍부해지는 영속 지식 자산

**MkDocs 정적 사이트 옵션**:
```bash
cd ~/Obsidian/스마트농업
pip install mkdocs-material
mkdocs build
# → ./site/ 정적 HTML 사이트 (GitHub Pages·Netlify·S3 배포 가능)
```

**lint** (vault 점검):
```bash
/techdoc-export-wiki --vault ~/Obsidian/스마트농업 --lint
# → vault/_lint_report.md (충돌 callout 잔존·끊어진 링크 등)
```

## 21. 자주 하는 작업 패턴 6종

### 패턴 1 — "특정 카드만 다시 쓰기"

```
/techdoc-rewrite 1.2.3 --instruction "성능 블록에 벤치마크 10개 추가. IEEE 802.11ax 비교 포함"
```

다른 69개 카드는 그대로. 2~3분 만에 해당 카드만 재작성.

### 패턴 2 — "별첨 추가"

```
# 처음엔 별첨 3개만 생성했는데, 카드 2.1.1 프로젝트도 심층분석 필요
/techdoc-deepdive 2.1.1
```

기존 별첨 3개 유지, A.4로 신규 별첨 추가 (10~15분).

### 패턴 3 — "중단 후 재개"

```
# 네트워크 문제로 /techdoc 중단
/techdoc-resume --from write
```

`writer_state.json` 기반으로 미완료 카드만 재작성.

### 패턴 4 — "기존 자료 활용"

```
/techdoc "차세대 배터리 기술" \
  --toc ./toc.txt \
  --ref file:./KITECH_2024.pdf \
  --ref site:https://www.kbatt.or.kr \
  --ref url:https://arxiv.org/abs/2401.12345
```

- `file:` PDF 텍스트 추출 후 KeyRef 저장
- `site:` 해당 도메인 `site:` 검색 추가
- `url:` 단일 URL 내용 확보

### 패턴 5 — "공공기관 제출용 개조식"

```
/techdoc "지자체 스마트시티 로드맵" \
  --toc ./toc.txt \
  --domain policy \
  --style 개조식 \
  --depth deep
```

- `--domain policy`: 법령·이해관계자·국제 비교
- `--style 개조식`: 명사형 종결·항목 중심 공문서 스타일
- `--depth deep`: 검색 30회/섹션, REF 25~30건

### 패턴 6 — "Plugin 자체 업그레이드" (v1.1.0 신규)

```
# 새 버전 체크
/techdoc-update --check

# 적용 (사용자 [y/N] 확인 후)
/techdoc-update
```

GitHub Releases에서 자동 다운로드·교체. LLM 호출 없이 결정론적.

## 22. 핵심 파일 예시

### `.claude-plugin/plugin.json` — 플러그인 매니페스트

```json
{
  "name": "techdoc-plugin",
  "version": "1.1.0",
  "description": "TechDoc — AI 기술보고서 생성 Cowork Plugin",
  "license": "MIT",
  "commands": "./commands/",
  "agents": "./agents/"
}
```

### `output/writer_state.json` — 카드 단위 상태 (resume의 핵심)

```json
{
  "schema_version": "0.2.0",
  "section_states": {
    "1.1": {
      "overview": { "status": "completed", "chars": 180 },
      "cards": [
        {
          "id": "1.1.1",
          "type": "tech",
          "name": "LoRa-Mesh",
          "importance": "high",
          "status": "completed",
          "chars": 2847,
          "attempts": 1
        }
      ]
    }
  },
  "appendices": [
    { "id": "A.1", "source_card_id": "1.1.1", "status": "completed", "chars": 24512 }
  ]
}
```

### `output/reference_list.json` — REF 집계

```json
{
  "schema_version": "0.2.0",
  "document_type": "기술보고서",
  "total_refs": 87,
  "usable_refs": 82,
  "en_ratio": 0.52,
  "category_coverage": [
    { "category": "학술", "count": 31, "target": 30, "ratio": 0.356 },
    { "category": "기업R&D", "count": 19, "target": 20, "ratio": 0.218 },
    { "category": "전문연구기관", "count": 14, "target": 15, "ratio": 0.161 }
  ]
}
```

### `vault/Tech/<name>.md` — Wiki 페이지 예시 (v1.1.0)

```markdown
---
type: tech
name: 점적관개
name_en: Drip Irrigation
importance: high
source_card_ids: ["1.1.1"]
ref_ids: ["REF-001", "REF-002"]
reports: ["[[Reports/노지스마트농업분석]]"]
appendix: "[[Tech/점적관개_appendix]]"
techdoc_auto: true
---

> 사용자 자유 메모 (보존)

<!-- techdoc:auto-start -->
> ℹ️ **심층분석 별첨**: [점적관개 — 심층분석](점적관개_appendix.md)

## 개요

토양·작물 수분에 따른 정밀 급수 ...

## 작동 원리·알고리즘

...

(7블록 + 별첨 콜아웃)
<!-- techdoc:auto-end -->
```

---

# PART Ⅴ. 명령·옵션 레퍼런스

## 23. 슬래시 명령 전체 (18종)

| 그룹 | 명령 | 핵심 역할 | 소요 |
|---|---|---|---|
| **유틸** | `/techdoc-doctor` | 환경 진단 (15개 항목) | 5초 |
| | `/techdoc-demo` | 3분 smoke test | 3분 |
| | `/techdoc-update` ⭐ | plugin 자체 자동 갱신 | 30초 |
| **파이프라인** | `/techdoc-outline` | Step 1 구조 설계 | 30초~2분 |
| | `/techdoc-research` | Step 2 조사 (researcher × 3) | 5~8분 |
| | `/techdoc-write` | Step 5 작성 (writer × 3) | 10~15분 |
| | `/techdoc-review` | Step 8 도메인 검토 + 보완 | 5~8분 |
| | `/techdoc-render` | Step 12 4종 출력 | 2~3분 |
| **재실행** | `/techdoc-resume` | 단계 단위 | 가변 |
| | `/techdoc-rewrite` | **카드 단위** ⭐ | 2~3분 |
| | `/techdoc-deepdive` | **별첨 개별** ⭐ | 10~15분 |
| **Wiki** ⭐ | `/techdoc-export-wiki` | LLM Wiki 변환·누적 | 1~2분 |
| **Notion** ⭐ | `/techdoc-export-notion` (v1.2.0) | TechDoc 보고서 → Notion publish (페이지 계층 + KeyRef DB) | 30초~3분 |
| **Autopilot** ⭐ | `/techdoc-autopilot` (v1.3.0) | 자율 모드 보고서 생성 (walk-away). deepdive(별첨) chunk 자동 처리(`--deep-dive-auto N`)·`--resume-from-disk` 중반 재개(기존 산출물 스캔) | 1.5~2.5h |
| | `/techdoc-autopilot-status` | 진행 상태 조회 | 즉시 |
| | `/techdoc-autopilot-stop` | graceful halt 요청 | 즉시 |
| | `/techdoc-autopilot-resume` | halt 후 재개 (`--resume-from-disk` 지원) | 즉시 |
| **통합** | `/techdoc` | 전체 파이프라인 (`--export-wiki` / `--push-notion` 옵션) | 60~130분 |

## 24. 주요 옵션 상세

### 문서 생성 핵심 옵션

| 옵션 | 기본값 | 값 | 효과 |
|---|---|---|---|
| `--toc FILE` | (없음) | 파일 경로 | 사용자 목차 사용 |
| `--mode MODE` | `exact` | `exact` / `enhance` | `exact`: TOC 그대로 / `enhance`: AI 보강 |
| `--outline FILE` | (없음) | `draft_outline.json` | 기존 outline (Step 1 스킵) |
| `--domain DOMAIN` | (없음) | `tech` / `market` / `policy` | 도메인 전문가 검토 |
| `--style STYLE` | `서술형` | `서술형` / `개조식` | 논문/공문서 문체 |
| `-o DIR` | `./output` | 디렉토리 | 출력 위치 |

### 조사 깊이 (소요 시간 ↔ 품질)

| `--depth` | 검색/섹션 | REF/섹션 | 시간 | 권장 |
|---|---|---|---|---|
| `quick` | 11회 | 10~12 | 3~5분 | 초안·빠른 확인 |
| `standard` (기본) | 21회 | 18~22 | 5~8분 | **대부분의 실제 보고서** |
| `deep` | 30회+ | 25~30 | 10~15분 | 연구·학술 문서 |

### 별첨 제어

| 옵션 | 효과 |
|---|---|
| `--deep-dive-auto N` | 자동 N개 선정 (importance=high 중) |
| `--deep-dive "이름1,이름2"` | 이름으로 지정 |
| `--deep-dive-ids "1.1.1,2.3.2"` | 카드 ID로 지정 |
| `--no-deep-dive` | 별첨 완전 생략 (시간 40% 단축) |

### 사용자 참고자료

| 옵션 | 예시 | 효과 |
|---|---|---|
| `--ref file:PATH` | `--ref file:./report.pdf` | PDF 텍스트 추출 (pymupdf) |
| `--ref url:URL` | `--ref url:https://arxiv.org/...` | 단일 URL WebFetch |
| `--ref site:URL` | `--ref site:https://kiast.or.kr` | `site:` 검색 추가 |

### Wiki 옵션 (v1.1.0 신규)

| 옵션 | 효과 |
|---|---|
| `--export-wiki <vault>` | `/techdoc` 마지막 단계로 wiki export 자동 호출 |
| `--vault <경로>` | (단독 명령) vault 디렉토리 |
| `--doc <output>` | (단독 명령) 보고서 출력 디렉토리 |
| `--create-vault` | vault 미존재 시 신규 생성 |
| `--lint` | vault 점검만 수행 (충돌 callout 잔존·끊어진 링크) |
| `--mkdocs` | vault에 mkdocs.yml 자동 작성 |

### `/techdoc-update` 옵션 (v1.1.0 신규)

| 옵션 | 효과 |
|---|---|
| (없음) | 새 버전 체크 + [y/N] 후 적용 |
| `--check` | 체크만, 적용 안 함 |
| `--force` | 동일 버전이어도 강제 재설치 |

### `/techdoc-resume` 재개 지점

| `--from` | 재개 위치 |
|---|---|
| `research` | Step 2 자료 조사부터 |
| `write` | Step 5 섹션 작성부터 (가장 흔함) |
| `review` | Step 8 도메인 검토부터 |
| `render` | Step 12 렌더링부터 |

---

# PART Ⅵ. 운영·배포

## 25. 설치 경로 4종

### ① ZIP 배포본 ⭐ (가장 간단)

```bash
# 1. Release 다운로드
# https://github.com/ystar001/techdoc-plugin/releases/tag/v1.1.0
unzip techdoc-plugin-v1.1.0.zip -d ~/.claude/plugins/techdoc-plugin

# 2. Python 의존성
cd ~/.claude/plugins/techdoc-plugin && pip install -e ".[pdf,docx]"
playwright install chromium

# 3. Claude Code 등록
/plugin marketplace add ~/.claude/plugins/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
/reload-plugins
/techdoc-doctor
```

### ② 자체 마켓플레이스 (GitHub 저장소)

```
/plugin marketplace add github.com/ystar001/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
```

### ③ 로컬 개발 모드

```bash
git clone https://github.com/ystar001/techdoc-plugin.git
cd techdoc-plugin
pip install -e ".[pdf,docx]"
claude --plugin-dir .
```

### ④ 수동 배포 (wrapped ZIP)

```bash
# 래퍼 폴더 포함 ZIP — 아무 곳에 해제해도 techdoc-plugin/ 폴더 자동 생성
unzip techdoc-plugin-v1.1.0-wrapped.zip -d ~/.claude/plugins/
```

### 검증

```bash
/techdoc-doctor
# → 15개 항목 [OK] 확인 (Python·의존성·디자인·한글폰트·playwright)
```

## 26. 자체 업데이트 (v1.1.0 신규)

`/techdoc-update`로 GitHub Releases에서 최신 zip을 자동 다운로드·교체. 사용자가 매번 zip 다운로드 + 압축 해제 + 재등록할 필요 없음.

### 사용

```bash
# 새 버전 체크만
/techdoc-update --check
# → "TechDoc Plugin v1.1.0 — 최신 버전 사용 중입니다." 또는
# → "신규 버전 발견: v1.2.0 (CHANGELOG 미리보기)"

# 적용 (사용자 [y/N] 확인 후 자동)
/techdoc-update
# → 다운로드 → SHA-256 검증 → 디렉토리 교체 → /reload-plugins 안내

# 동일 버전 강제 재설치 (디버깅·복구)
/techdoc-update --force
```

### 동작

1. GitHub API 호출 (`api.github.com/repos/ystar001/techdoc-plugin/releases/latest`)
2. semver 비교 (`is_newer`)
3. 새 버전 있으면 CHANGELOG 미리보기 표시 + [y/N]
4. zip + sha256 다운로드 (HTTPS)
5. 무결성 검증 (SHA-256 일치)
6. `~/.claude/plugins/techdoc-plugin/` 디렉토리 덮어쓰기
7. `/reload-plugins` 안내

**LLM 호출 0회**. 결정론적·안전.

## 27. 릴리스·상태

| 버전 | 주요 변경 | 파일 수 | 코드 |
|---|---|---|---|
| **v1.8.0** (2026-07-06) | 서식 게이트 확장: `format_gate`에 제어문자(F40)·mermaid 라벨 sanity(F39)·인라인 열거(F41) 지표 + `render_nesting` fenced_code(F37), `check_quality`에 캡션 정합 게이트(F42). writer 프롬프트 서식·mermaid 저작 규칙(`card_layout_conventions.md`). F38·F43은 F15 렌더러 흡수 종속으로 유보. SCHEMA 유지. | (변동 없음) | 약 22k줄 |
| **v1.3.0**–**v1.7.0** | 상세 이력은 `CHANGELOG.md` 참조 (Notion·Autopilot·self-model 표준화·render 일반화/트리·서식 게이트 도입 F27·F28·F30). | (변동 없음) | — |
| **v1.3.0** (2026-05-13) | Autopilot 자율 모드: `/techdoc-autopilot` + status/stop/resume. superpowers `/loop` 기반 self-paced. 6 safety 트리거 + 이상 시 chat. SCHEMA 유지. | (변동 없음) | 약 21k줄 |
| **v1.2.0** (2026-05-13) | Notion 통합: `/techdoc-export-notion` + `/techdoc --push-notion` 옵션. 페이지 계층 + KeyRef inline database. delta sync. v2 호환 4원칙 준수. | (변동 없음) | 약 20k줄 |
| **v1.1.3** (2026-05-13) | F5 자체 모델 품질 검사: `scripts/check_quality`에 self-model 카드 레이아웃 지원 + mode 자동 라우팅 + F1 변형 본문 키 재귀 합산. `/techdoc-review` Phase A 자동화. SCHEMA 유지. | (변동 없음) | 약 19k줄 |
| **v1.1.2** (2026-05-13) | F8 자체 모델 호환: `/techdoc-rewrite`·`/techdoc-write` skill에 self-model 카드 레이아웃(`output/cards/<id>_card.json`) fallback + `--single-call` 인자. F1·F3 컨벤션 명문화. SCHEMA 유지. | (변동 없음) | 약 18.5k줄 |
| **v1.1.1** (2026-05-13) | F2·F4·F6·F7 정합: writer `self_check` 필드 통일 + 본문 인라인 자체 검증 금지 + researcher Write 권한 거부 사전 차단(preflight·prompt 규약) + `/techdoc-update` SHA-256·자동 백업·롤백. SCHEMA_VERSION 유지. | (변동 없음) | 약 18k줄 |
| **v1.1.0** (2026-05-04) | `/techdoc-update`(자체 갱신) + `/techdoc-export-wiki`(LLM Wiki, D 하이브리드) + `/techdoc --export-wiki` 통합 옵션. pytest 인프라(85 tests). | 130+ | 약 17k줄 |
| **v1.0.0** (2026-04-29) | 정식 릴리스. plugin 단독 메인 구조. MIT 라이선스 + public 배포. | 100+ | 약 15k줄 |
| **v0.1.0** (2026-04-24) | 알파 릴리스. Cowork Plugin 전환. 카드 + 별첨 시스템. 5종 디자인 | 97 | 14,866줄 |

### 향후 로드맵

| 버전 | 예정 기능 |
|---|---|
| v1.2.x | 보고서 자료 갱신 기능 (기존 보고서의 KeyRef·refs를 새 검색으로 갱신) |
| v1.x | CI·배치 모드 (Claude Code 세션 외), 다국어 지원 (영문 보고서) |
| 별도 product | Knowledge Base 시스템 (write → wiki → 사용자 검수 → consolidate → 보고서) |

### 의존성

Python 3.10+, pydantic, rapidfuzz, matplotlib, pyyaml, jinja2, rich, pymupdf, httpx. 선택: playwright (PDF), python-docx (DOCX).

## 28. FAQ·트러블슈팅

### Q1. `/plugin` 명령이 인식 안 됨

Claude Code 구버전일 수 있음. `claude --version` 확인 후 최신 업그레이드.

### Q2. `plugin validation fail`

v1.1.0부터는 공식 스키마 준수. 구 버전 ZIP을 받았다면 최신 Release 재다운로드:
- https://github.com/ystar001/techdoc-plugin/releases/tag/v1.1.0

### Q3. `/techdoc-doctor`에서 `techdoc_core: [FAIL]`

Python 의존성 누락. 재설치:
```bash
cd ~/.claude/plugins/techdoc-plugin && pip install -e .
```

### Q4. `Korean font: [WARN]`

matplotlib 차트의 한글 폰트 없음. 운영체제별:
- Windows: 기본 Malgun Gothic 자동
- macOS: `brew install font-nanum-gothic`
- Linux: `sudo apt install fonts-nanum`

### Q5. PDF 생성 실패

playwright 미설치. PDF 불필요하면 무시 (HTML+MD는 정상). 필요 시:
```bash
pip install -e ".[pdf]"
playwright install chromium   # ~300MB
```

### Q6. 중간에 중단됐어요

`writer_state.json` 기반으로 카드 단위 재개:
```
/techdoc-resume --from write
```

### Q7. 특정 카드·별첨만 수정하고 싶어요

- 카드: `/techdoc-rewrite <id>` (예: `1.2.3`)
- 별첨: `/techdoc-deepdive <card-id>`

### Q8. WebSearch quota 초과

60초 대기 후:
```
/techdoc-resume --from research
```

또는 `--depth quick` 으로 검색량 축소.

### Q9. 기술보고서 외 다른 유형 가능?

네. 5종 자동 판별:
- 사업계획서 (`--type business_plan`)
- 정책보고서 (`--type policy_report` 또는 `--domain policy`)
- 연구보고서 (`--type research_report`)
- 교육자료 (`--type education_material`)

### Q10. ANTHROPIC_API_KEY 설정해야 하나요?

**아니요**. TechDoc Plugin은 Claude Code 세션 자격증명 사용. API 키 불필요. 구독 플랜의 WebSearch·Subagent 쿼터 내에서 동작.

### Q11. `/techdoc-update`가 v1.0.0 사용자에게 동작하나요? (v1.1.0 신규)

v1.0.0에는 `/techdoc-update` 명령이 없습니다. v1.0.0 사용자는 처음 한 번 수동으로 v1.1.0 zip을 다운로드·교체해야 합니다. 그 후부터는 `/techdoc-update`로 자동.

### Q12. Wiki vault에 사용자가 추가한 메모는 보존되나요? (v1.1.0 신규)

네. 모든 페이지에 `<!-- techdoc:auto-start -->`/`<!-- techdoc:auto-end -->` 마커가 있고, AI는 마커 사이만 갱신합니다. 마커 외부 사용자 메모는 절대 손대지 않습니다.

### Q13. Wiki 충돌 callout이 너무 많이 떠요. (v1.1.0 신규)

같은 엔티티가 보고서마다 다른 수치를 가진 정상 변동입니다. 사용자가 수동으로 정리하거나 callout을 삭제하면 다음 export 시 사라집니다 (충돌 ID 추적).

---

## 29. Notion 통합 (v1.2.0 신규)

`/techdoc-export-notion`이 TechDoc 보고서를 Notion 워크스페이스로 publish합니다.

### 사전 준비 (최초 1회)

1. **Notion integration 생성**: https://www.notion.so/my-integrations → "New integration" → token 발급.
2. **환경 변수**: `export NOTION_TOKEN=secret_xxx`.
3. **parent page 권한**: 보고서를 둘 부모 페이지의 `...` 메뉴 → "Add connections" → integration 추가.

### 사용

```bash
export NOTION_TOKEN=secret_xxx
/techdoc-export-notion --parent-page <32자-hex-UUID>
```

또는 `/techdoc` 통합 옵션:

```bash
/techdoc "title" --toc ... --push-notion <parent_page_id>
```

### 생성되는 Notion 구조

```
parent_page
└── 보고서 title                    ← 루트 페이지
    ├── 1.1 섹션 제목               ← 자식 페이지 (섹션마다)
    ├── 1.2 섹션 제목
    ├── 별첨 A.1 별첨 제목
    └── KeyRef                      ← inline database
         ├── REF-001 row
         └── ...
```

### delta sync

재실행 시 `output/notion_state.json`의 content hash와 비교해 **변경된 카드만 update_page** 호출. 50카드 중 1개 수정 → API ~1회.

### 충돌 대응

- v1.2.0은 **단방향(techdoc → Notion)**. Notion에서 수동 편집한 본문은 다음 push에서 덮어쓰여집니다.
- **권장**: Notion에서 본문 직접 편집보다 코멘트·제안 모드 사용. 작성자가 plugin에서 반영 후 재publish.
- 양방향 sync는 v1.3.x·v2.0 로드맵.

**spec**: `docs/superpowers/specs/2026-05-13-notion-push-integration-design.md`

---

## 30. Autopilot 자율 모드 (v1.3.0 신규)

`/techdoc-autopilot`이 보고서 1건을 walk-away 가능한 자율 모드로 실행합니다. 사용자가 1~2시간 동안 세션을 지켜볼 필요 없음.

### 동작 원리

superpowers `/loop` dynamic mode 위에 동작. 매 wake-up마다:

1. `autopilot_state.json` + `writer_state.json` 로드
2. 6 safety 트리거 점검 → 위반 시 즉시 halt
3. 다음 chunk 결정 (stage dependency graph)
4. chunk 실행 (researcher/writer/reviewer subagent 또는 Python 호출)
5. `check_quality` 자동 호출 → 결과를 state·log에 기록
6. `ScheduleWakeup` 60s (immediate) 또는 1200s (rate limit signal)

### Chunk granularity — 섹션 그룹 단위

| Chunk | 평균 소요 |
|---|---|
| `outline` | 30초~2분 |
| `research_A·B·C` | 5~8분 |
| `merge_research` | 1분 |
| `write_A·B·C` | 10~15분 |
| `review` | 5~8분 |
| `render` | 2~5분 |

일반 보고서 ~10 wake-ups, 총 1.5~2.5h.

### 6 safety 트리거

| 트리거 | 조건 |
|---|---|
| `quality_fail` | check_quality FAIL > 0 |
| `quality_warn_exceeded` | WARN > `--max-warnings` (기본 10) |
| `card_failures_exceeded` | retry 3회 초과 카드 수 > `--max-consecutive-card-failures` (기본 5) |
| `wall_clock_exceeded` | 시작 후 `--max-wall-clock` (기본 4h) 초과 |
| `state_corruption` | writer_state·autopilot_state 파싱 실패 |
| `manual_stop` | `$OUTPUT_DIR/autopilot.stop` 파일 존재 |

### 사용 예

```bash
# 자율 시작 + Notion publish
/techdoc-autopilot "AI 반도체 기술보고서" \
  --toc ./toc.txt \
  --domain tech \
  --deep-dive-auto 5 \
  --push-notion 2f1a9b8c4d5e6f7a8b9c0d1e2f3a4b5c

# 다른 일 하다가 진행 확인
/techdoc-autopilot-status

# 1시간 후 chat 확인 — 완료 또는 halt 알림
```

### 사용자 개입 시나리오

- **품질 미달로 halt** (`quality_fail` 또는 `quality_warn_exceeded`):
  ```bash
  /techdoc-rewrite <문제카드>   # 또는 직접 수정
  /techdoc-autopilot-resume
  ```
- **사용자가 중간 stop**:
  ```bash
  /techdoc-autopilot-stop       # autopilot.stop flag 생성
  # ... 나중에 ...
  /techdoc-autopilot-resume
  ```

### 알림 모드

| 모드 | 채팅 알림 |
|---|---|
| `anomalies_only` (기본) | 시작·완료·halt만 |
| `each-wake-up` | 매 wake-up 1줄 (8~10건 메시지) |

silent 모드에서도 `output/autopilot.log`에 모든 wake-up 기록.

상세는 spec `docs/superpowers/specs/2026-05-13-techdoc-autopilot-design.md` 참조.

---

## 관련 문서

| 문서 | 용도 |
|---|---|
| [USAGE.md](USAGE.md) | 샘플 예제·도메인별 사용 패턴 |
| [INSTALL.md](INSTALL.md) | 4가지 설치 방법·업데이트·제거 |
| [CHANGELOG.md](CHANGELOG.md) | 버전별 변경 이력 |
| [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) | 설계 ↔ 구현 매핑 |
| [LICENSE](LICENSE) | MIT |

---

## 기여·문의

- 저장소: [github.com/ystar001/techdoc-plugin](https://github.com/ystar001/techdoc-plugin)
- 최신 Release: [v1.1.0](https://github.com/ystar001/techdoc-plugin/releases/tag/v1.1.0)
- 이슈·제안: [GitHub Issues](https://github.com/ystar001/techdoc-plugin/issues)
- 라이선스: MIT
