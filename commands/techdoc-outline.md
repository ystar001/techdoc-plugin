---
description: Step 1 - 문서 구조 설계. TOC 파싱 또는 AI 생성. draft_outline.json 저장 후 사용자 검토 대기
allowed-tools: Bash, Read, Write
argument-hint: "<문서 제목> [--toc FILE] [--mode exact|enhance] [--domain tech|market|policy] [--style 서술형|개조식] [-o OUTPUT]"
---

# /techdoc-outline — 문서 구조 설계

`prompts/outline_draft.md` 지시를 따라 3가지 시나리오 중 하나로 문서 구조를 생성합니다.

## 입력 분석

사용자 인자 `$ARGUMENTS`에서 다음을 추출:
- **문서 제목** (필수)
- `--toc FILE` (사용자 TOC 파일, 옵션)
- `--mode exact|enhance` (기본: exact — TOC 그대로 / enhance — AI 보완)
- `--domain tech|market|policy` (옵션)
- `--style 서술형|개조식` (기본: 서술형)
- `-o DIR` (기본: `./output`)

## 시나리오 분기

### Case 1: `--toc` 없음 (AI가 구조 생성)
1. `prompts/outline_draft.md` + `prompts/_shared/analysis_tags.md` 로드
2. 문서 유형 자동 판별 (제목 키워드):
   ```bash
   python -m scripts.select_design --title "제목"
   ```
3. Claude가 10개 섹션 구조 직접 생성 (JSON)
4. 저장: `$OUTPUT_DIR/draft_outline.json`

### Case 2: `--toc` + `--mode enhance` (AI 보완)
1. `parse_toc.py`로 1차 파싱:
   ```bash
   python -m scripts.parse_toc --toc "$TOC_FILE" --title "제목" -o "$OUTPUT_DIR"
   ```
2. 결과 JSON 로드
3. Claude가 subtopics 보강·재배열 (섹션 제목 유지)
4. glossary 자동 추출 (반복 용어)
5. 저장: `$OUTPUT_DIR/draft_outline.json`

### Case 3: `--toc` + `--mode exact` (기본, TOC 그대로)
1. `parse_toc.py`로 파싱 후 그대로 사용:
   ```bash
   python -m scripts.parse_toc --toc "$TOC_FILE" --title "제목" -o "$OUTPUT_DIR"
   ```
2. AI 개입 없음

## 분석 태그 자동 부여
`parse_toc.py::assign_analysis_tag()`가 자동 수행하므로 별도 처리 불필요.

## 용어집 (glossary) 추출
Case 1/2에서 Claude가 직접 수행:
- 섹션 제목·subtopics에서 반복 등장 용어
- 영문 약어 + 한국어 풀이 쌍

## 사용자 검토 대기

완료 후 **다음 단계 자동 진행 금지**. 사용자가 `draft_outline.json` 검토 후 수동으로:
```
/techdoc-research --outline "$OUTPUT_DIR/draft_outline.json"
# 또는
/techdoc "제목" --outline "$OUTPUT_DIR/draft_outline.json"
```

## 출력 보고

```
[techdoc-outline 완료]
- 시나리오: Case 1 (AI 생성) | Case 2 (보완) | Case 3 (TOC 그대로)
- 섹션: 10개
- 총 subtopics: 42개
- 자동 분석 태그: 개념정의 2, 구조분석 3, 현황분석 1, 비교분석 1, 사례분석 2, 시나리오 1
- glossary: 12개 용어

파일:
  $OUTPUT_DIR/draft_outline.json

다음 단계: draft_outline.json을 검토·수정 후
  /techdoc-research --outline "$OUTPUT_DIR/draft_outline.json"
```
