---
description: TechDoc 플러그인 환경 진단 (Python·의존성·디자인 템플릿·한글 폰트·Playwright)
allowed-tools: Bash
argument-hint: "[--output DIR]"
---

# /techdoc-doctor — 환경 진단

플러그인이 정상 동작할 수 있는지 15개 항목을 검사합니다. 설치 직후 첫 실행을 **강력 권장**합니다.

## 실행

`scripts/doctor.py`를 실행해 환경 상태를 보고하세요:

```bash
cd "$CLAUDE_PROJECT_DIR" && python -m scripts.doctor $ARGUMENTS
```

또는 techdoc-plugin 디렉토리가 별도 경로인 경우:

```bash
cd <plugin-install-dir> && python -m scripts.doctor $ARGUMENTS
```

## 해석 가이드

결과 테이블 중:
- **[OK]**: 정상
- **[WARN]**: 선택 기능 일부 제한 (예: playwright 없으면 PDF 비활성)
- **[FAIL]**: 필수 항목 누락 — 수정 제안 참조

## 주요 점검 항목

1. Python 버전 ≥3.10
2. 필수 의존성 (pydantic, rapidfuzz, matplotlib, pyyaml, jinja2, rich, httpx)
3. techdoc_core 모듈 import
4. 디자인 템플릿 5종 (tech_report, business_plan, policy_report, research_report, education_material)
5. _shared CSS 2개 (cards.css, appendix.css)
6. 한글 폰트 (Malgun Gothic / Pretendard / NanumGothic)
7. Playwright chromium (선택, PDF 생성용)
8. python-docx (선택, DOCX 생성용)
9. 출력 디렉토리

## 문제 해결

- **FAIL**: 수정 제안 섹션의 명령 실행 후 재진단
- **Playwright chromium 없음**: `playwright install chromium` 실행
- **한글 폰트 없음**: 운영체제별 Pretendard 또는 NanumGothic 설치

환경 진단 결과를 사용자에게 표 형태로 보고하고, FAIL 항목이 있으면 구체 수정 방법을 안내하세요.
