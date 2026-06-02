"""TechDoc Plugin 상수.

기존 techdoc/config.py에서 API 관련 설정을 제외하고 도메인 상수만 이식.
AI 호출은 Claude Code 네이티브로 전환되어 API 키·모델 설정 불필요.
"""

from __future__ import annotations

import re
from pathlib import Path

# ── 경로 ──
TECHDOC_CORE_DIR: Path = Path(__file__).resolve().parent
DESIGN_TEMPLATE_DIR: Path = TECHDOC_CORE_DIR / "design_templates"

# ── 품질 임계값 ──
QUALITY_THRESHOLD: float = 4.5
MIN_SECTION_LENGTH: int = 300  # HTML 태그 제거 후 최소 텍스트 길이
MIN_REF_PER_SECTION: int = 2  # 섹션당 최소 레퍼런스 인용 수
MAX_AI_ESTIMATE_RATIO: float = 0.3  # AI 추정 비율 상한
MAX_SECTION_RETRY: int = 3  # 섹션 작성 재시도 횟수

# ── 카드 분량 기준 (v1.2) ──
CARD_LENGTH_RULES = {
    "tech": {"min": 1500, "recommended": (2000, 2500), "max": 3500},
    "project": {"min": 1800, "recommended": (2500, 3000), "max": 4000},
    "product": {"min": 1000, "recommended": (1200, 1500), "max": 2000},
}

# ── 카드 중요도별 차등 (v1.2) ──
CARD_LENGTH_BY_IMPORTANCE = {
    "high": {
        "tech": (2500, 3500),
        "project": (3000, 4000),
        "product": (1500, 2000),
    },
    "medium": {
        "tech": (1500, 2500),
        "project": (2000, 3000),
        "product": (1000, 1500),
    },
    "low": {
        "tech": (800, 1500),
        "project": (1200, 2000),
        "product": (600, 1000),
    },
}

# ── 섹션당 카드 수 (v1.2) ──
CARDS_PER_SECTION = {
    "tech": (3, 5),
    "project": (2, 3),
    "product": (1, 2),
}

# ── 별첨 분량 기준 (v1.5 — 2배 확대) ──
APPENDIX_LENGTH_RULES = {
    "tech": {"min": 15000, "recommended": (20000, 25000), "max": 40000},
    "project": {"min": 20000, "recommended": (25000, 30000), "max": 50000},
}

APPENDIX_COUNT_RANGE = (3, 7)  # 문서당 자동 선정 별첨 개수
APPENDIX_REFS_PER = (20, 30)  # 별첨당 전용 REF 개수

# ── 문서 유형별 참고자료 기준 (v1.3 기술연구 강화) ──
REF_TARGETS = {
    "기술보고서": {
        "min_total": 85,  # 본문 REF 목표 (별첨 제외)
        "per_section": 18,
        "min_en_ratio": 0.5,
        "min_intl_org": 4,
        "min_academic": 30,
        "queries_ko": 10,
        "queries_en": 11,
        "search_rounds": 5,  # v1.3 — 5라운드 심층 조사
        "category_targets": {
            "정부공공": 5,
            "국제기구": 4,
            "학술": 30,
            "기업R&D": 20,
            "전문연구기관": 15,
            "산업시장": 6,
            "뉴스": 5,
        },
    },
    "사업계획서": {
        "min_total": 35,
        "per_section": 6,
        "min_en_ratio": 0.35,
        "min_intl_org": 2,
        "min_academic": 3,
        "queries_ko": 4,
        "queries_en": 4,
        "search_rounds": 3,  # 정책·사업은 기존 라운드 유지
        "category_targets": {
            "정부공공": 5,
            "국제기구": 3,
            "학술": 5,
            "산업시장": 10,
            "기업기관": 8,
            "뉴스": 4,
        },
    },
    "정책보고서": {
        "min_total": 45,
        "per_section": 7,
        "min_en_ratio": 0.35,
        "min_intl_org": 5,
        "min_academic": 5,
        "queries_ko": 5,
        "queries_en": 4,
        "search_rounds": 3,
        "category_targets": {
            "정부공공": 15,
            "국제기구": 8,
            "학술": 8,
            "산업시장": 4,
            "기업기관": 3,
            "뉴스": 7,
        },
    },
    "연구보고서": {
        "min_total": 90,  # v1.3 — 기술연구 강화로 상향
        "per_section": 20,
        "min_en_ratio": 0.5,
        "min_intl_org": 4,
        "min_academic": 40,
        "queries_ko": 8,
        "queries_en": 13,
        "search_rounds": 5,
        "category_targets": {
            "정부공공": 5,
            "국제기구": 5,
            "학술": 40,
            "기업R&D": 20,
            "전문연구기관": 15,
            "산업시장": 5,
            "뉴스": 5,
        },
    },
    "교육자료": {
        "min_total": 30,
        "per_section": 5,
        "min_en_ratio": 0.3,
        "min_intl_org": 2,
        "min_academic": 3,
        "queries_ko": 4,
        "queries_en": 3,
        "search_rounds": 3,
        "category_targets": {
            "정부공공": 8,
            "국제기구": 3,
            "학술": 5,
            "산업시장": 3,
            "기업기관": 5,
            "뉴스": 6,
        },
    },
}


def get_ref_targets(document_type: str) -> dict:
    """문서 유형에 맞는 참고자료 기준 반환."""
    return REF_TARGETS.get(document_type, REF_TARGETS["기술보고서"])


# ── 분석 방법론 키워드 (우선순위순) ──
ANALYSIS_TAGS = [
    {"priority": 1, "keywords": ["개요", "정의", "핵심 원리", "원리"], "tag": "[분석: 개념정의]"},
    {"priority": 2, "keywords": ["구조", "시스템", "아키텍처", "구성"], "tag": "[분석: 구조분석]"},
    {"priority": 3, "keywords": ["현황", "동향", "추이", "시장"], "tag": "[분석: 현황분석]"},
    {"priority": 4, "keywords": ["비교", "차이", "대비", "vs"], "tag": "[분석: 비교분석]"},
    {"priority": 5, "keywords": ["사례", "적용", "도입", "실증"], "tag": "[분석: 사례분석]"},
    {"priority": 6, "keywords": ["도전", "과제", "한계", "문제"], "tag": "[분석: SWOT]"},
    {"priority": 7, "keywords": ["전망", "미래", "로드맵", "향후"], "tag": "[분석: 시나리오]"},
]
DEFAULT_ANALYSIS_TAG = "[분석: 인과관계]"

# ── 레퍼런스 신뢰도 등급 ──
RELIABILITY_LEVELS = {
    "확인됨": {"usable": True, "description": "2개 이상 독립 출처에서 교차 확인"},
    "단일출처": {"usable": True, "description": "공신력 있는 1개 출처에서만 확인"},
    "미확인": {"usable": False, "description": "출처를 찾았으나 원본 접근 불가 — 인용 금지"},
    "AI지식": {"usable": False, "description": "검색으로 확인 못 함 — 인용 금지"},
}

# ── 디자인 타입 자동 판별 키워드 ──
DESIGN_TYPE_KEYWORDS = {
    "tech_report": ["기술", "기술분석", "기술동향", "R&D", "연구개발"],
    "business_plan": ["사업", "투자", "BM", "비즈니스", "사업계획"],
    "policy_report": ["정책", "제도", "규제", "법령", "거버넌스"],
    "research_report": ["연구", "논문", "학술", "실험", "조사"],
    "education_material": ["교육", "가이드", "매뉴얼", "안내서", "교재"],
}

# ── 스키마 버전 (v1.4 — self-model 카드 표준화) ──
SCHEMA_VERSION = "0.2.0"

# self-model 카드 섹션 키: 위치만(sec1~sec6) 표준. 서술명·헤딩은 섹션 title로 (F3).
SECTION_KEY_RE = re.compile(r"^sec[1-6]$")

# 위치별 기본 한글 헤딩 (migrate 시 섹션 title이 비어 있으면 채움; F12에서 정제).
DEFAULT_SECTION_TITLES = {
    "sec1": "정의·범위",
    "sec2": "원리·구조",
    "sec3": "국내외 동향",
    "sec4": "구성요소·방법론",
    "sec5": "한계·도전",
    "sec6": "전망",
}

# ── Researcher 섹션 범위 분할 (v1.3) ──
RESEARCHER_SECTION_GROUPS = {
    "A": (1, 4),  # 섹션 1~4
    "B": (5, 7),  # 섹션 5~7
    "C": (8, 10),  # 섹션 8~10
}
