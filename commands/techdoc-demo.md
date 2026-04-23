---
description: TechDoc smoke test - <3분 이내 미니 보고서 생성 (2섹션×2카드, fixtures 활용, WebSearch 없음)
allowed-tools: Bash, Read, Write
argument-hint: "[--output DIR]"
---

# /techdoc-demo — 3분 smoke test

TechDoc 플러그인이 정상 동작하는지 **3분 이내**로 확인하는 미니 파이프라인. WebSearch·Subagent 없이 fixtures JSON을 활용해 렌더링까지만 실행.

## 목적

- 신규 사용자가 "이 플러그인이 내 환경에서 실제로 동작하는가?"를 **3분 안에** 확인
- 복잡한 전체 파이프라인(40~60분) 전에 검증 단계

## 실행 단계

### 1. 출력 디렉토리 준비
```bash
OUTPUT_DIR="${1:-./demo_output}"
mkdir -p "$OUTPUT_DIR"
```

### 2. Fixtures 로드
`tests/fixtures/document_draft_mock.json` 에 미리 준비된 3섹션 × 카드 포함 Document를 복사:
```bash
cd "$CLAUDE_PROJECT_DIR"
cp tests/fixtures/document_draft_mock.json "$OUTPUT_DIR/document_final.json"
cp tests/fixtures/reference_list_mock.json "$OUTPUT_DIR/reference_list.json" 2>/dev/null || true
```

### 3. 품질 검증 (결정론적)
```bash
python -m scripts.check_quality \
  --input "$OUTPUT_DIR/document_final.json" \
  --refs "$OUTPUT_DIR/reference_list.json" \
  --output "$OUTPUT_DIR/quality_report.json"
```

### 4. 렌더링 (HTML + MD, PDF/DOCX는 선택)
```bash
python -m scripts.render \
  --input "$OUTPUT_DIR/document_final.json" \
  --refs "$OUTPUT_DIR/reference_list.json" \
  --output "$OUTPUT_DIR" \
  --formats html,md
```

PDF·DOCX는 playwright·python-docx 설치 시에만 활성화.

### 5. 결과 보고
출력 파일 경로·크기·페이지 수(HTML 추정)를 표로 제시. 예:

```
[techdoc-demo 완료] (2분 14초)
- 섹션: 3개
- 카드: 기술 3, 프로젝트 2, 제품 1
- HTML: demo_output/TechDocDemo_202604231400.html (142 KB)
- MD:   demo_output/TechDocDemo_202604231400.md (45 KB)
- 품질: overall 4.2/5.0, FAIL 0, WARN 2

다음 단계:
  실제 보고서 생성: /techdoc "제목" --toc ./toc.txt
  환경 진단: /techdoc-doctor
```

## Fixtures 미존재 시

`tests/fixtures/document_draft_mock.json`이 없으면:
1. 경고 출력
2. Stage 5.0 완료 안내: "Fixtures가 아직 구축되지 않았습니다. 개발 초기 버전이므로 `/techdoc`으로 전체 파이프라인 실행해주세요."

## 실패 처리

- playwright 미설치 → HTML·MD만 생성 (정상 종료)
- Python·의존성 오류 → `/techdoc-doctor` 실행 권장
