# TechDoc Plugin 사용법 및 샘플 예제

> v1.0.0 | 설치: [INSTALL.md](INSTALL.md)

---

## 1. 첫 실행 체크리스트

설치 직후 권장 순서:

```
1. /techdoc-doctor       # 환경 진단 (15개 항목)
2. /techdoc-demo         # 3분 smoke test (실제 파이프라인 축소판)
3. /techdoc-outline "테스트 제목"  # 실제 구조 생성 시험
```

여기까지 성공하면 실제 보고서 생성 가능.

---

## 2. 전체 워크플로 (3가지 시나리오)

### 시나리오 A: TOC 없음 — AI가 구조 생성

```
/techdoc-outline "스마트농업 기술 동향 보고서"
```

결과: `./output/draft_outline.json` 생성 (AI가 10개 섹션 자동 설계).

**사용자 검토·수정 후**:
```
/techdoc "스마트농업 기술 동향 보고서" --outline ./output/draft_outline.json --domain tech
```

### 시나리오 B: 기존 TOC 사용 (가장 일반적)

**`my_toc.txt` 준비**:
```
1. 정밀농업 개요
● 정의와 범위
● 기술 구성요소
● 글로벌 시장 동향

2. 관개 자동화 시스템
● 점적관수 시스템
● AI 물수요 예측 알고리즘
● LoRa 기반 센서 네트워크

3. 작물 모니터링
● 드론·위성 영상 분석
● 병해충 조기 감지
● 생육 상태 AI 분석

4. 국내외 주요 프로젝트
● MIT CSAIL SMART-IRRI
● 농진청 스마트팜 실증
● 유럽 H2020 프로젝트

5. 전망과 과제
● 2030 로드맵
● 기술·정책 도전과제
```

**통합 실행**:
```
/techdoc "스마트농업 기술 보고서" --toc ./my_toc.txt --domain tech
```

### 시나리오 C: TOC + AI 보완 모드

```
/techdoc "스마트농업 기술 보고서" --toc ./my_toc.txt --mode enhance --domain tech
```

AI가 기존 subtopic을 보강·재배열. 섹션 제목은 유지.

---

## 3. 단계별 실행 (고급 — 중간 검토·수정 가능)

통합 `/techdoc` 대신 단계별로 호출:

```bash
# Step 1: 목차 확정 (사용자 검토 대기)
/techdoc-outline "제목" --toc ./my_toc.txt
# → draft_outline.json 수동 수정 가능

# Step 2: 자료 조사 (5~8분)
/techdoc-research --outline ./output/draft_outline.json
# → reference_list.json, KeyRef/*.md 생성

# (선택) 수집한 레퍼런스 검토
# 예: cat ./output/KeyRef/023_MIT_LoRaMesh.md

# Step 3: 섹션 작성 (10~15분)
/techdoc-write --outline ./output/draft_outline.json --refs ./output/reference_list.json --style 서술형

# Step 4: 도메인 검토 + 보완 (5~8분)
/techdoc-review --input ./output/document_draft.json --refs ./output/reference_list.json --domain tech

# Step 5: 별첨 심층분석 (선택, 별첨당 10~15분)
/techdoc-deepdive 1.1.1   # LoRa-Mesh 기술 카드를 별첨으로
/techdoc-deepdive 2.3.1   # SMART-IRRI 프로젝트 카드를 별첨으로

# Step 6: 최종 렌더링 (2~3분)
/techdoc-render --input ./output/document_draft.json --refs ./output/reference_list.json --formats html,pdf,docx,md
```

---

## 4. 샘플 예제 (4가지 도메인)

### 예제 1: 기술보고서 (기본)

**입력**:
```
/techdoc "차세대 반도체 기술 동향" --toc ./반도체_toc.txt --domain tech --depth standard
```

**기대 산출물**:
- 본문 100~150p (섹션 10개, 카드 72개 = 기술 38 + 프로젝트 22 + 제품 12)
- 별첨 3~7개 (85~175p)
- 총 185~325p
- REF 225~280건

### 예제 2: 연구보고서 (학술 중심)

**입력**:
```
/techdoc "AI 기반 신약 개발 연구" \
  --toc ./신약개발_toc.txt \
  --style 서술형 \
  --depth deep \
  --domain tech
```

**차이점**: `--depth deep`로 검색량 확대, 학술 카테고리 40건+ 확보.

### 예제 3: 정책보고서

**입력**:
```
/techdoc "한국의 탄소중립 정책 분석" \
  --toc ./탄소중립_toc.txt \
  --domain policy \
  --style 개조식
```

**차이점**:
- `--domain policy`: 법령·시행령·조항 정확성, 이해관계자 분석, 국제 비교
- `--style 개조식`: 공문서 스타일 (명사형 종결, 항목 중심)

### 예제 4: 사용자 참고자료 활용

**입력**:
```
/techdoc "자율주행 기술 백서" \
  --toc ./자율주행_toc.txt \
  --ref file:./previous_report.pdf \
  --ref site:https://www.kiast.or.kr \
  --ref url:https://arxiv.org/abs/2401.12345 \
  --domain tech
```

**동작**:
- `file:`: PDF 텍스트 추출 후 KeyRef로 저장 (pymupdf)
- `site:`: 해당 도메인을 `site:` 연산자로 추가 검색
- `url:`: WebFetch로 내용 확보

---

## 5. 별첨 제어 (v1.4 핵심 기능)

### 자동 선정 (기본)
```
/techdoc "제목" --toc ... --deep-dive-auto 5
```
importance=high 카드 중 상위 5개 자동 선정.

### 수동 지정 (이름)
```
/techdoc "제목" --toc ... --deep-dive "LoRa-Mesh,SMART-IRRI-2024,HBM3e"
```
쉼표로 구분된 이름 매칭.

### 수동 지정 (카드 ID)
```
/techdoc "제목" --toc ... --deep-dive-ids "1.1.1,2.3.2,3.1.1"
```

### 별첨 생략 (빠른 실행)
```
/techdoc "제목" --toc ... --no-deep-dive
```
본문만 생성 → 40~60분으로 단축.

### 사후 별첨 추가
```
/techdoc-deepdive 4.2.1                       # 신규 별첨
/techdoc-deepdive A.2 --skip-research          # 기존 별첨 재작성
/techdoc-deepdive 1.1.1 --instruction "벤치마크 블록에 최근 2024 논문 추가"
```

---

## 6. 카드 재작성 (흔한 케이스)

생성 결과에서 특정 카드만 마음에 안 들면:

```
# 기본 재작성
/techdoc-rewrite 1.1.3

# 지시 추가
/techdoc-rewrite 1.1.3 --instruction "기술 원리 블록을 단계별로 더 상세히. 특히 CSMA/CA 프로토콜 단계 설명"

# 레퍼런스 교체·추가
/techdoc-rewrite 1.1.3 --refs REF-023,REF-041,REF-087
```

**중요**: 다른 카드는 건드리지 않음. 해당 카드만 새로 생성.

---

## 7. 중단·재개

긴 파이프라인(60~130분) 중 Claude Code 세션이 끊기거나 네트워크 문제로 중단된 경우:

```
# 작성 단계부터 재개 (가장 흔한 케이스)
/techdoc-resume --from write

# 렌더링만 다시
/techdoc-resume --from render

# 자료 조사부터
/techdoc-resume --from research
```

`writer_state.json`에 카드 단위 상태가 기록되어 미완료 카드만 재작성.

---

## 8. 결과물 구조

```
output/
├── progress.log               실시간 진행 로그
├── draft_outline.json         Step 1 초안
├── final_outline.json         Step 3 보정
├── reference_list.json        Step 2 REF 목록
├── research_round_A/B/C.json  Step 2 라운드별 결과
├── merged_research.json       Step 2 병합 결과
├── KeyRef/
│   ├── index.json
│   └── 001~087_*.md           수집한 REF 원문·메타
├── sections/
│   └── section_*.json         섹션별 작성 결과
├── appendices/
│   └── appendix_A1.json       별첨별 심층분석
├── figures/
│   └── fig_*.png              matplotlib 차트
├── writer_state.json          카드 단위 상태 (resume용)
├── document_draft.json        Step 5 초안
├── domain_review.json         Step 8 검토 결과
├── quality_report.json        Phase A 23개 지표
├── document_final.json        최종 데이터
├── 제목_202604231430.html     마스터 (카드+별첨 포함)
├── 제목_202604231430.pdf      인쇄용
├── 제목_202604231430.docx     MS Word
└── 제목_202604231430.md       편집 가능 Markdown
```

---

## 9. 모니터링 (별도 터미널)

긴 파이프라인 중 진행 상황 실시간 확인:

```bash
# 탭/터미널 1: /techdoc 실행 (Claude Code)
# 탭/터미널 2: 모니터링 (쉘)
python -m scripts.monitor ./output

# 또는 스냅샷만
python -m scripts.monitor ./output --snapshot
```

## 10. 환경 변수 (선택)

```bash
# .env 또는 셸 환경
TECHDOC_OUTPUT_DIR=./my_reports       # 기본 출력 위치 오버라이드
TECHDOC_DEFAULT_DEPTH=standard        # 기본 depth
TECHDOC_DEFAULT_STYLE=서술형           # 기본 스타일
```

(TechDoc plugin 자체는 ANTHROPIC_API_KEY 불필요. Claude Code 세션 자격증명 사용.)

---

## 11. FAQ

### Q1. 한 보고서에 얼마나 걸리나?
- `--depth quick --no-deep-dive`: 15~25분 (55p 축소판)
- `--depth standard --deep-dive-auto 5` (기본): **60~130분** (185~325p)
- `--depth deep --deep-dive-auto 7`: 100~180분 (300~400p)

### Q2. WebSearch 쿼터가 걱정돼요
`--depth quick` 으로 검색 횟수 축소. 섹션당 21회 → 11회.

### Q3. 특정 섹션의 카드가 부족해 보여요
```
/techdoc-write --outline ... --refs ...
```
를 다시 실행하거나, writer_state.json 확인 후 실패 카드만 `/techdoc-rewrite` 호출.

### Q4. 출처 신뢰도가 낮은 REF가 섞였어요
`KeyRef/*.md`에서 `reliability: 미확인 | AI지식`인 파일은 자동으로 인용 제외됨. 다만 확인됨·단일출처 중에서도 의심되면 해당 REF를 편집하거나 삭제 후 `/techdoc-review --domain tech` 재실행.

### Q5. 한글 폰트 경고가 떠요
matplotlib가 차트 생성 시 한글 폰트를 못 찾음. 운영체제별:
- Windows: 기본 Malgun Gothic 자동 (경고 시 matplotlib 재설치)
- macOS: `brew install font-nanum-gothic`
- Linux: `sudo apt install fonts-nanum`

### Q6. 별첨 분량을 조절하고 싶어요
별첨 분량은 v1.5 기준 기술 15k~40k자 / 프로젝트 20k~50k자 고정. 향후 버전에서 `--appendix-length short|medium|long` 옵션 예정.

### Q7. 생성된 문서를 편집하고 싶어요
`.md` 파일을 직접 수정 후:
```
/techdoc-render --input ./output/document_final.json --formats html,pdf
```

---

## 12. 명령어 전체 목록 (Cheat Sheet)

```
/techdoc-doctor                                        # 환경 진단
/techdoc-demo                                          # 3분 smoke test

/techdoc-outline "제목" [--toc FILE] [--mode exact|enhance]
/techdoc-research --outline FILE [--depth ...] [--ref ...]
/techdoc-write --outline FILE --refs FILE [--style ...]
/techdoc-review --input FILE --refs FILE [--domain tech|market|policy]
/techdoc-render --input FILE [--formats html,pdf,docx,md]

/techdoc-resume --from research|write|review|render
/techdoc-rewrite <card-id> [--instruction ...] [--refs ...]
/techdoc-deepdive <card-id> [--skip-research] [--instruction ...]

/techdoc "제목" [모든 옵션]                              # 통합 파이프라인
```

---

## 13. 실제 사용 예 (end-to-end)

```bash
# 1. 프로젝트 디렉토리에서 시작
cd ~/my-reports
mkdir 2026_스마트농업_보고서 && cd $_

# 2. TOC 파일 작성
cat > toc.txt <<'EOF'
1. 정밀농업 기술 개요
● 정의와 범위
● 4대 핵심 기술

2. 관개·배수 자동화
● 점적관수
● AI 물수요 예측

3. 작물 모니터링
● 드론·위성 영상
● 생육 분석

4. 국내외 주요 프로젝트

5. 전망과 과제
EOF

# 3. Claude Code에서 실행
```

Claude Code 세션에서:

```
/techdoc "스마트농업 기술 보고서 2026" \
  --toc ./toc.txt \
  --domain tech \
  --style 서술형 \
  --depth standard \
  --ref file:./previous_report.pdf
```

약 90분 후 `./output/` 에 HTML + PDF + DOCX + MD 완성.

---

## 더 알아보기

- 설계 의도·요구사항 매핑: [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md)
- 기능 변경 이력: [CHANGELOG.md](CHANGELOG.md)
- 내부 아키텍처: [README.md](README.md) 마지막 섹션
