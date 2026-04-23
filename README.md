# TechDoc Plugin

> **v0.1.0** — AI 기술보고서 생성 Cowork Plugin (Claude Code 네이티브)

대학·기업·연구기관 레퍼런스 기반 논문 수준 기술보고서를 자동 생성합니다. 핵심 기술·프로젝트는 **별첨으로 심층 분석** (기술 15k~40k자 / 프로젝트 20k~50k자).

## 특징

- 🎯 **레퍼런스 100% 기반** — AI 추측 차단, 수치·기관·연구 모두 [REF] 인용
- 📚 **카드 중첩식 섹션** — 기술·프로젝트·제품을 독립 카드로 구조화
- 📖 **별첨 심층분석** — 핵심 대상을 15~40페이지 리뷰 논문 수준으로 해부
- 🔬 **기술연구 77% 가중** — 학술 35% + 기업 R&D 24% + 전문연구기관 18%
- ⚡ **Claude Code 네이티브** — ANTHROPIC_API_KEY 불필요, 세션 자격증명 사용
- 🔄 **카드 단위 재실행** — 마음에 안 드는 카드만 `/techdoc-rewrite`로 다시

## 설치

### 1. 기본 설치
```bash
cd techdoc-plugin
pip install -e .
```

### 2. 선택 의존성 (PDF/DOCX 생성 시)
```bash
pip install -e ".[pdf,docx]"
playwright install chromium  # PDF용
```

### 3. 환경 진단
```bash
/techdoc-doctor
```
15개 항목 모두 `[OK]`이면 정상 설치 완료.

## 설치·사용 가이드

- **설치**: [INSTALL.md](INSTALL.md) — 4가지 방법 (ZIP·로컬경로·개발자모드·Git)
- **사용법 + 샘플 예제**: [USAGE.md](USAGE.md) — 4가지 도메인 시나리오·단계별 실행·카드 재작성·FAQ

## 빠른 시작

### 1. 목차 파일 준비 (`my_toc.txt`)
```
1. 정밀농업 개요
● 정의
● 기술 구성요소
● 시장 동향

2. 관개 자동화 시스템
● 점적관수 시스템
● AI 물수요 예측

3. 전망
● 로드맵
● 도전과제
```

### 2. 통합 파이프라인 실행
```
/techdoc "스마트농업 기술 보고서" --toc ./my_toc.txt --domain tech
```

60~130분 내 본문 100~150p + 별첨 85~175p 보고서 완성.

### 3. 결과 확인
```
output/
  스마트농업기술보고서_YYYYMMDDHHMM.html   마스터 (카드+별첨 포함)
  스마트농업기술보고서_YYYYMMDDHHMM.pdf    인쇄용
  스마트농업기술보고서_YYYYMMDDHHMM.docx   MS Word
  스마트농업기술보고서_YYYYMMDDHHMM.md     편집용 Markdown
```

## 명령어 (11개)

### 유틸리티
| 명령 | 설명 |
|---|---|
| `/techdoc-doctor` | 환경 진단 (15개 항목) |
| `/techdoc-demo` | 3분 smoke test (fixtures 기반) |

### 파이프라인 단계
| 명령 | Step | 설명 |
|---|---|---|
| `/techdoc-outline "제목" [--toc]` | 1 | 문서 구조 설계, 사용자 검토 대기 |
| `/techdoc-research --outline ...` | 2 | 5라운드 자료 조사 (researcher × 3 병렬) |
| `/techdoc-write --outline ... --refs ...` | 5 | 섹션·카드 작성 (writer × 3 병렬) |
| `/techdoc-review --input ... --domain tech` | 8 | 도메인 전문가 검토 + 보완 |
| `/techdoc-render --input ...` | 12 | HTML/PDF/DOCX/MD 생성 |

### 재실행·수정
| 명령 | 설명 |
|---|---|
| `/techdoc-resume --from <step>` | 단계 단위 재실행 |
| `/techdoc-rewrite <card-id>` | 카드 하나만 다시 (다른 카드 보존) |
| `/techdoc-deepdive <card-id>` | 별첨 심층분석 개별 생성 |

### 통합
| 명령 | 설명 |
|---|---|
| `/techdoc "제목" [옵션]` | 위 단계 전체 순차 실행 |

## 주요 옵션

```
--toc FILE              # 사용자 목차 파일
--mode exact|enhance    # TOC 모드 (기본: exact = 그대로 사용)
--domain tech|market|policy  # 도메인 검토 활성화
--style 서술형|개조식    # 문체 (기본: 서술형)
--depth quick|standard|deep  # 검색 깊이 (기본: standard)
--ref file:path.pdf     # 사용자 참고 자료 (PDF/URL/site)
--deep-dive "이름"       # 별첨 수동 지정
--deep-dive-auto N      # 자동 선정 개수 (기본 3~7)
--no-deep-dive          # 별첨 생략
-o DIR                  # 출력 디렉토리 (기본: ./output)
```

## 문서 유형 5종 (자동 판별)

| 유형 | 키워드 | REF 목표 |
|---|---|---|
| 기술보고서 | 기술, R&D, 연구개발 | 85 (+별첨 50~70) |
| 연구보고서 | 연구, 논문, 학술 | 90 (+별첨) |
| 사업계획서 | 사업, 투자, BM | 35 |
| 정책보고서 | 정책, 제도, 규제 | 45 |
| 교육자료 | 교육, 가이드, 매뉴얼 | 30 |

## 카드 구조

### 섹션 내 본문 카드 (개괄)
- **기술 카드** (7블록): 개요·원리·구성·성능·장단점·차별점·근거 (1,500~3,500자)
- **프로젝트 카드** (7블록 + 메타): 배경·체계·방법·결과·시사점·후속·근거 (1,800~4,000자)
- **제품 카드** (6블록): 배경·기능·사양·도입사례·시장·근거 (1,000~2,000자)

### 문서 말미 별첨 (심층분석)
- **기술 별첨** (10블록): 연구사·원리·알고리즘·아키텍처·벤치마크·구현체·타임라인·한계·미래·참고문헌 (15k~40k자)
- **프로젝트 별첨** (11블록): 연대기·체계·단계·실험설계·데이터셋·결과심층·후속·비교·상업화·연구자·참고문헌 (20k~50k자)

## 실행 시간 예상

| depth | 별첨 | 총 시간 |
|---|---|---|
| quick | 없음 | 15~25분 |
| standard | 없음 | 40~60분 |
| standard | 3~7개 (기본) | **60~130분** |
| deep | 5~7개 | 100~180분 |

## 파이프라인 구조

```
/techdoc → /techdoc-doctor
          → /techdoc-outline (사용자 검토 대기)
          → /techdoc-research (researcher×3 병렬)
          → /techdoc-write (writer×3 병렬, 카드 단위 resume)
          → /techdoc-review (reviewer + 자동 보완)
          → /techdoc-deepdive × N (별첨 심층분석)
          → /techdoc-render (HTML+PDF+DOCX+MD)
```

## 트러블슈팅

### "playwright 없음" 경고
PDF 생성이 필요 없으면 무시. HTML+MD는 정상 생성됨. 필요 시:
```bash
pip install -e ".[pdf]"
playwright install chromium
```

### "한글 폰트 없음" 경고
matplotlib 차트의 한글이 깨짐. Pretendard 또는 NanumGothic 설치:
- Windows: 시스템 기본 Malgun Gothic 사용 (자동)
- macOS: `brew install font-nanum-gothic`
- Linux: `sudo apt install fonts-nanum`

### 파이프라인 중단 시
```bash
/techdoc-resume --from write   # 작성 단계부터 재개
```

### 특정 카드만 수정
```bash
/techdoc-rewrite 1.1.3                          # 자동 재작성
/techdoc-rewrite 1.1.3 --instruction "기간·예산 더 상세히"
```

### 별첨 추가
```bash
/techdoc-deepdive 2.3.1                         # 본문 카드 → 별첨
```

### 환경 문제 일반
```bash
/techdoc-doctor
```
`[FAIL]` 항목의 수정 제안 따라 실행.

## 아키텍처

- **메인 Claude 세션**: 오케스트레이터 (WebSearch·WebFetch·Read·Write·Bash)
- **3 Subagent**: researcher / writer / reviewer (격리 컨텍스트, 병렬 실행)
- **10 Python 유틸**: 결정론적 처리 (파싱·dedup·마이그레이션·렌더링·진단)
- **카드 레벨 체크포인트**: `writer_state.json`으로 카드 단위 resume 지원

## 버전 히스토리

v0.1.0 — 최초 릴리스. 자세한 변경 이력은 [CHANGELOG.md](CHANGELOG.md) 참조.

## 요구사항 추적성

설계 결정 vs 구현 매핑은 [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) 참조.

## 라이선스

Private.
