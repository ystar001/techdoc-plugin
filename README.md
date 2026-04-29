# TechDoc Plugin

> **v1.0.0** · AI 기술보고서 생성 Claude Code Cowork Plugin

명령 한 줄로 100~300페이지 전문 기술보고서 생성. 대학·기업 R&D·전문연구기관 레퍼런스 77% 기반, 핵심 기술·프로젝트는 별첨으로 **논문 수준 심층분석**(기술 15k~40k자 / 프로젝트 20k~50k자).

## 설치

3분 안에 끝납니다:

```bash
# 1. ZIP 압축 해제
unzip techdoc-plugin-v1.0.0.zip -d ~/.claude/plugins/techdoc-plugin

# 2. Python 의존성
cd ~/.claude/plugins/techdoc-plugin && pip install -e ".[pdf,docx]"
playwright install chromium

# 3. Claude Code에 등록 (Claude Code 세션 안에서)
/plugin marketplace add ~/.claude/plugins/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
/reload-plugins

# 4. 환경 진단 (모두 [OK] 나와야 함)
/techdoc-doctor
```

자세한 설치 옵션: [INSTALL.md](INSTALL.md)

---

## 5분 예시 (지금 바로 시도)

### 예시 1: TOC 없이 AI가 구조 생성

```
/techdoc-outline "5G 네트워크 기술 동향 보고서"
```

**결과** (30초 내):
```
output/
└── draft_outline.json    ← 10개 섹션 구조 자동 생성
```

→ JSON 열어 섹션 제목·subtopics 확인. 수정 후 다음 단계.

### 예시 2: 간단한 TOC로 전체 파이프라인

**toc.txt**:
```
1. 5G 개요
● 5G NR 정의
● 주파수 대역

2. 네트워크 아키텍처
● gNB 구조
● Core Network 5G

3. 한국 상용화 현황
● 3사 경쟁 구도
● 주요 사례
```

**실행**:
```
/techdoc "5G 네트워크 기술 동향" --toc ./toc.txt --domain tech --no-deep-dive
```

**결과** (40~60분):
- `output/5G네트워크기술동향_YYYYMMDDHHMM.html` (3섹션, 약 50페이지)
- `output/...md` 편집 가능 Markdown

`--no-deep-dive`로 별첨 생략해 빠르게 완성.

### 예시 3: 별첨 포함 풀버전

```
/techdoc "AI 반도체 기술보고서" \
  --toc ./toc.txt \
  --domain tech \
  --style 서술형 \
  --depth standard \
  --deep-dive-auto 5
```

**결과** (90~130분):
- 본문 10섹션 100~150페이지 (카드 70개 내외)
- **별첨 5개** × 15~35페이지 = 85~175페이지
- HTML + PDF + DOCX + MD 4종
- 총 **185~325페이지 전문 보고서**

---

## 11개 명령어 한눈에

| 분류 | 명령 | 입력 예 | 소요 |
|---|---|---|---|
| **유틸** | `/techdoc-doctor` | (없음) | 5초 |
| | `/techdoc-demo` | (없음) | 3분 |
| **단계** | `/techdoc-outline` | `"제목" --toc toc.txt` | 30초~2분 |
| | `/techdoc-research` | `--outline draft_outline.json` | 5~8분 |
| | `/techdoc-write` | `--outline ... --refs reference_list.json` | 10~15분 |
| | `/techdoc-review` | `--input document_draft.json --domain tech` | 5~8분 |
| | `/techdoc-render` | `--input document_draft.json` | 2~3분 |
| **재실행** | `/techdoc-resume` | `--from write` | 가변 |
| | `/techdoc-rewrite` | `1.1.3 --instruction "..."` | 2~3분 |
| | `/techdoc-deepdive` | `1.1.1` | 10~15분 |
| **통합** | `/techdoc` | `"제목" --toc ... --domain tech` | 60~130분 |

---

## 옵션 전체 레퍼런스

### 문서 생성 핵심 옵션 (`/techdoc` 및 단계별 공통)

| 옵션 | 기본값 | 값 | 효과 | 사용 시점 |
|---|---|---|---|---|
| `--toc FILE` | (없음) | 파일 경로 | 사용자 목차 사용 | 대부분의 실제 보고서 |
| `--mode MODE` | `exact` | `exact` / `enhance` | `exact`: TOC 그대로 / `enhance`: AI가 subtopics 보강 | subtopics가 부족할 때 `enhance` |
| `--outline FILE` | (없음) | `draft_outline.json` | 이미 만든 outline 사용 (Step 1 스킵) | outline을 수동 수정한 후 |
| `--domain DOMAIN` | (없음) | `tech` / `market` / `policy` | 해당 도메인 전문가 검토 + 보완 | 품질 끌어올리고 싶을 때 |
| `--style STYLE` | `서술형` | `서술형` / `개조식` | 서술형=논문 스타일 / 개조식=공문서 스타일 | 공공기관·정부 보고서는 `개조식` |
| `-o DIR` | `./output` | 디렉토리 | 출력 위치 | 여러 보고서 분리 관리 시 |

### 조사 깊이 옵션 (소요 시간 + 품질)

| `--depth` | 섹션당 검색 횟수 | REF 목표 | 시간 | 사용 시점 |
|---|---|---|---|---|
| `quick` | 11회 (라운드 1~2) | 10~12건 | 3~5분 | 초안·빠른 확인용 |
| `standard` (기본) | 21회 (5라운드) | 18~22건 | 5~8분 | **대부분의 실제 보고서** |
| `deep` | 30회+ (라운드 추가) | 25~30건 | 10~15분 | 연구보고서·학술 문서 |

### 별첨 제어 옵션 (심층분석 선택)

| 옵션 | 효과 |
|---|---|
| `--deep-dive-auto N` | 자동으로 N개 별첨 선정 (importance=high 중). 기본 3~7개 |
| `--deep-dive "이름1,이름2"` | 이름으로 별첨 대상 지정 (쉼표 구분) |
| `--deep-dive-ids "1.1.1,2.3.2"` | 카드 ID로 별첨 지정 |
| `--no-deep-dive` | 별첨 완전 생략 (본문만, 시간 40% 단축) |

### 사용자 참고자료 옵션

| 옵션 | 예시 | 효과 |
|---|---|---|
| `--ref file:path.pdf` | `--ref file:./2023_보고서.pdf` | PDF 텍스트 추출 후 KeyRef로 사용 |
| `--ref url:...` | `--ref url:https://arxiv.org/abs/2401.12345` | 단일 URL 내용 확보 |
| `--ref site:...` | `--ref site:https://www.kiast.or.kr` | 해당 도메인을 `site:` 검색에 추가 |
| (여러 번 반복 가능) | `--ref file:a.pdf --ref site:b.com` | 모두 누적 |

### `/techdoc-resume` 옵션

| `--from` | 재개 지점 |
|---|---|
| `research` | Step 2 자료 조사부터 |
| `write` | Step 5 섹션 작성부터 (가장 흔한 재개 지점) |
| `review` | Step 8 도메인 검토부터 |
| `render` | Step 12 렌더링부터 |

### `/techdoc-rewrite <card-id>` 옵션

| 옵션 | 예시 |
|---|---|
| `--instruction "..."` | `--instruction "성능 블록에 벤치마크 10개 추가"` |
| `--refs REF-023,REF-041` | 참조 REF 교체·추가 |
| `--rollback` | 직전 버전으로 복원 |

### `/techdoc-deepdive <card-id>` 옵션

| 옵션 | 예시 |
|---|---|
| `--skip-research` | 기존 별첨 조사 재사용 (writer만 재호출) |
| `--instruction "..."` | 별첨 작성 지시 |

---

## 실제 사용 예 — 상황별

### 상황 A: 회사 내부용 기술보고서 (기본)

```
/techdoc "사내 AI 활용 현황 보고서" --toc ./toc.txt --domain tech
```

**결과**: 본문 100~150p + 별첨 3~7개. 학술·기업 R&D 중심.

### 상황 B: 공공기관 제출용 (개조식)

```
/techdoc "지자체 스마트시티 로드맵" \
  --toc ./toc.txt \
  --domain policy \
  --style 개조식 \
  --depth deep
```

**결과**: 정책·법령 중심, 이해관계자 분석, 국제 비교. 개조식으로 공문서 스타일.

### 상황 C: 빠른 초안 (별첨 없음)

```
/techdoc "양자컴퓨팅 개요" --toc ./toc.txt --no-deep-dive --depth quick
```

**결과**: 본문만 40~60페이지. 15~25분 완료.

### 상황 D: 기존 자료 활용

```
/techdoc "차세대 배터리 기술" \
  --toc ./toc.txt \
  --ref file:./KITECH_2024_report.pdf \
  --ref site:https://www.kbatt.or.kr \
  --domain tech
```

**결과**: 사용자 제공 PDF·사이트 + 일반 웹검색 병합. 제공 자료 REF에 `category: 사용자제공` 기록.

### 상황 E: 일부 카드만 다시 쓰기

```
# 생성한 보고서 중 카드 1.2.3이 부실
/techdoc-rewrite 1.2.3 --instruction "CSMA/CA 프로토콜 단계별로 상세히. 의사코드 포함"

# → 다른 69개 카드는 그대로, 1.2.3만 2~3분 만에 재작성
```

### 상황 F: 별첨 추가

```
# 처음엔 별첨 3개만 생성했는데, 카드 2.1.1 프로젝트도 심층분석이 필요
/techdoc-deepdive 2.1.1

# → 기존 별첨 3개 유지, A.4로 신규 별첨 추가 (10~15분)
```

### 상황 G: 중단 후 재개

```
# /techdoc 실행 중 네트워크 문제로 중단됨
/techdoc-resume --from write

# → writer_state.json 기반으로 미완료 카드만 재작성
```

---

## 출력 결과 구조

```
output/
├── 보고서_202604231430.html   ★ 마스터 (카드+별첨 통합)
├── 보고서_202604231430.pdf    ★ 인쇄용
├── 보고서_202604231430.docx   ★ MS Word 편집
├── 보고서_202604231430.md     ★ Markdown 편집
│
├── draft_outline.json        Step 1 목차
├── final_outline.json        Step 3 보정
├── reference_list.json       Step 2 REF 목록 (카테고리 분류)
├── KeyRef/
│   ├── 001~087_*.md          수집한 REF 원문 (YAML + 요약)
│   └── index.json
├── document_draft.json       Step 5 초안 (카드 포함)
├── document_final.json       최종
├── domain_review.json        Step 8 도메인 검토
├── quality_report.json       Phase A 23개 지표
├── writer_state.json         카드 단위 상태 (resume용)
└── figures/
    └── fig_*.png             matplotlib 차트
```

---

## 특징

- 🎯 **레퍼런스 100% 기반**: 모든 수치·기관·연구에 `[REF-xxx]` 인용
- 📚 **카드 중첩식 섹션**: 기술·프로젝트·제품을 독립 카드로
- 📖 **별첨 심층분석**: 핵심 대상을 15~40페이지 리뷰 논문 수준으로
- 🔬 **77% 가중 레퍼런스**: 학술 35% + 기업 R&D 24% + 전문연구기관 18%
- ⚡ **Claude Code 네이티브**: ANTHROPIC_API_KEY 불필요
- 🔄 **카드 단위 재실행**: 마음에 안 드는 카드만 다시
- 📊 **시각화 자동**: matplotlib 차트 + MathJax 수식 + Mermaid 다이어그램

---

## 문서 유형 5종 (자동 판별)

제목 키워드로 디자인 자동 선택:

| 제목 키워드 | 판별 | REF 목표 |
|---|---|---|
| 기술, R&D, 연구개발 | 기술보고서 | 본문 85 + 별첨 50~70 |
| 연구, 논문, 학술 | 연구보고서 | 본문 90 + 별첨 |
| 사업, 투자, BM | 사업계획서 | 35 |
| 정책, 제도, 규제 | 정책보고서 | 45 |
| 교육, 가이드, 매뉴얼 | 교육자료 | 30 |

수동 지정: `--type policy_report`

---

## 실행 시간 가이드

| 설정 | 시간 | 분량 | 권장 상황 |
|---|---|---|---|
| `--depth quick --no-deep-dive` | **15~25분** | 40~60p | 초안·아이디어 확인 |
| `--depth standard --no-deep-dive` | 40~60분 | 100~150p | 본문 중심 보고서 |
| `--depth standard --deep-dive-auto 5` ★ | **60~130분** | 185~325p | **대부분의 실제 보고서** |
| `--depth deep --deep-dive-auto 7` | 100~180분 | 280~450p | 박사논문·연구보고서 |

---

## 트러블슈팅

| 증상 | 조치 |
|---|---|
| `/techdoc` 명령 인식 안 됨 | `/reload-plugins` |
| `plugin validation fail` | 최신 ZIP 다운로드 후 재설치 |
| `doctor`에서 `techdoc_core: [FAIL]` | `cd <plugin-path> && pip install -e .` |
| `Korean font: [WARN]` | Pretendard 또는 NanumGothic 설치 |
| PDF 생성 실패 | `pip install -e ".[pdf]" && playwright install chromium` |
| 중간에 중단됨 | `/techdoc-resume --from write` |
| 특정 카드 부실 | `/techdoc-rewrite <id>` |
| 별첨 추가 필요 | `/techdoc-deepdive <card-id>` |
| WebSearch quota 초과 | 60초 대기 후 `/techdoc-resume --from research` |

---

## 추가 문서

- **[INSTALL.md](INSTALL.md)** — 4가지 설치 방법, 업데이트·제거, 검증
- **[USAGE.md](USAGE.md)** — 상세 샘플 예제 (4 도메인), 단계별 실행, FAQ 7문항, end-to-end 실습
- **[CHANGELOG.md](CHANGELOG.md)** — 버전별 변경 이력
- **[REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md)** — 설계 결정 vs 구현 매핑

---

## 아키텍처 (간단히)

```
/techdoc
  └─> 메인 Claude 세션 (오케스트레이터)
       ├─> WebSearch · WebFetch · Read · Bash (내장 도구)
       └─> Subagent × 3 (격리 컨텍스트, 병렬)
            ├─ techdoc-researcher (5라운드 + 별첨 6라운드 조사)
            ├─ techdoc-writer (카드·별첨 작성, writer_state 카드 단위 resume)
            └─ techdoc-reviewer (도메인 전문가 검토)

  Python 유틸 (결정론적):
    parse_toc · select_design · build_reflist · merge_research · migrate
    check_quality · generate_chart · render · monitor · doctor
```

## 라이선스

Private.
