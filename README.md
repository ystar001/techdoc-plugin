# TechDoc Plugin

> **Status**: v0.1.0-dev (개발 중, Stage 0 스캐폴딩 단계)

AI 기술보고서 생성 Cowork Plugin. 대학·기업·연구기관 레퍼런스 기반 논문 수준 기술보고서를 자동 생성하며, 핵심 기술·프로젝트는 별첨으로 심층 분석합니다.

## 개발 상태

이 플러그인은 개발 초기 단계입니다. 구현 계획은 프로젝트 루트의 [PLUGIN_PLAN.md](../PLUGIN_PLAN.md) 참조.

## 설치 (예정)

```bash
# 기본 설치
claude plugin install techdoc-plugin

# PDF/DOCX 지원 포함
pip install -e .[pdf,docx]
playwright install chromium
```

## 사용법 (예정)

```bash
/techdoc-doctor                       # 환경 진단 (설치 직후 권장)
/techdoc-demo                         # <3분 smoke test
/techdoc "보고서 제목" --toc ./toc.txt  # 전체 파이프라인
```

자세한 명령 목록과 옵션은 개발 완료 후 이 문서가 채워집니다.
