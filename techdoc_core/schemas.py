"""TechDoc Plugin pydantic 스키마.

모든 JSON 체크포인트·산출물은 이 스키마로 엄격 검증된다.
- schema_version 필드로 마이그레이션 지원 (migrate.py)
- researcher subagent LLM 출력 schema drift 방어
- writer subagent 카드·별첨 상태 추적
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from techdoc_core.constants import SCHEMA_VERSION

Importance = Literal["high", "medium", "low"]
Reliability = Literal["확인됨", "단일출처", "미확인", "AI지식"]
Category = Literal["정부공공", "국제기구", "학술", "기업R&D", "전문연구기관", "산업시장", "뉴스"]
CardType = Literal["tech", "project", "product"]
AppendixType = Literal["tech", "project"]
CardStatus = Literal["pending", "writing", "completed", "failed"]


# ── KeyRef: 레퍼런스 메타데이터 (researcher subagent 출력) ──

class Technology(BaseModel):
    """KeyRef에 등장하는 기술."""
    name: str
    type_tag: str = ""  # 통신·센싱·제어 등
    key_metrics: list[str] = Field(default_factory=list)
    importance: Importance = "medium"


class Project(BaseModel):
    """KeyRef에 등장하는 프로젝트·연구."""
    name: str
    institution: str = ""
    pi: str = ""
    period: str = ""  # "2023.01-2025.12"
    budget: str = ""  # "$3.2M"
    sponsor: str = ""
    importance: Importance = "medium"


class Product(BaseModel):
    """KeyRef에 등장하는 제품·솔루션."""
    name: str
    maker: str = ""
    country: str = ""
    deployed_at: str = ""
    price_range: str = ""
    importance: Importance = "medium"


class KeyRefSchema(BaseModel):
    """개별 KeyRef YAML 메타데이터 스키마 (schemas drift 방어 핵심).

    researcher subagent가 생성하는 각 KeyRef 파일의 frontmatter 검증용.
    잘못된 필드명·타입은 researcher에게 재생성 요청 (최대 2회).
    """
    schema_version: str = SCHEMA_VERSION
    id: str = Field(..., pattern=r"^REF-\d{3}$")
    category: Category
    source: str  # 기관·출판사·사이트
    institution: str = ""  # 연구 소속
    authors: list[str] = Field(default_factory=list)
    year: int = Field(..., ge=1990, le=2100)
    venue: str = ""  # 학회·저널·기업명
    title: str = Field(..., max_length=300)
    url: str = ""
    excerpt: str = Field(default="", max_length=2000)
    key_numbers: list[str] = Field(default_factory=list)
    technologies: list[Technology] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    products: list[Product] = Field(default_factory=list)
    reliability: Reliability
    related_sections: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not v.startswith("REF-"):
            raise ValueError("REF id must start with 'REF-'")
        return v


# ── Research Round: researcher subagent 라운드별 출력 ──

class ResearchRoundSchema(BaseModel):
    """researcher subagent 한 라운드 결과 (5라운드 본문 + 6라운드 별첨)."""
    schema_version: str = SCHEMA_VERSION
    researcher_group: Literal["A", "B", "C"]  # 섹션 범위 분할
    round: int = Field(..., ge=1, le=6)
    round_purpose: str  # "광범위"·"대학타깃"·"기업R&D"·"연구기관"·"인용·최신"·"별첨심화"
    section_range: tuple[int, int]
    queries: list[str]
    refs_found: list[str] = Field(default_factory=list)  # REF id 목록
    new_refs: int = 0
    duration_s: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


# ── Card State: writer subagent 카드 단위 상태 ──

class CardStateSchema(BaseModel):
    """카드 단위 작성 상태 (writer_state.json 엔트리)."""
    id: str  # 예: "1.1.1" (section.card)
    type: CardType
    name: str
    importance: Importance
    status: CardStatus = "pending"
    chars: int = 0
    content_hash: str = ""
    attempts: int = 0
    last_error: str = ""
    refs_used: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AppendixStateSchema(BaseModel):
    """별첨 단위 작성 상태 (writer_state.json의 appendices 엔트리)."""
    id: str  # 예: "A.1" (appendix letter + index)
    source_card_id: str  # 연결된 본문 카드 ID (예: "1.1.1")
    type: AppendixType
    name: str
    status: CardStatus = "pending"
    chars: int = 0
    blocks_completed: int = 0  # 기술 10블록 / 프로젝트 11블록 중 완료 수
    blocks_total: int = 0
    content_hash: str = ""
    attempts: int = 0
    last_error: str = ""
    refs_used: list[str] = Field(default_factory=list)


class SectionStateSchema(BaseModel):
    """섹션 단위 상태 (overview + cards)."""
    overview: CardStateSchema | None = None
    cards: list[CardStateSchema] = Field(default_factory=list)
    analysis_block: CardStateSchema | None = None


class ProgressEventSchema(BaseModel):
    """구조화 진행 이벤트 (monitor.py가 실시간 표시)."""
    ts: datetime = Field(default_factory=datetime.now)
    section: str
    card: str = ""
    appendix: str = ""
    state: Literal["starting", "writing", "verifying", "completed", "failed", "retrying"]
    chars: str = ""  # "1200/2500"
    elapsed_s: float = 0.0


class WriterStateSchema(BaseModel):
    """writer_state.json 전체 스키마 — 카드·별첨 단위 resume의 핵심."""
    schema_version: str = SCHEMA_VERSION
    pipeline_started_at: datetime = Field(default_factory=datetime.now)
    pipeline_updated_at: datetime = Field(default_factory=datetime.now)
    section_states: dict[str, SectionStateSchema] = Field(default_factory=dict)
    appendices: list[AppendixStateSchema] = Field(default_factory=list)
    events: list[ProgressEventSchema] = Field(default_factory=list)

    def touch(self) -> None:
        """업데이트 타임스탬프 갱신."""
        self.pipeline_updated_at = datetime.now()


# ── Document Snapshot: 최종 산출물 메타 ──

class DocumentMetaSchema(BaseModel):
    """document_final.json 메타데이터."""
    schema_version: str = SCHEMA_VERSION
    title: str
    document_type: str = "기술보고서"
    domain: str = ""
    style: Literal["서술형", "개조식"] = "서술형"
    date: str = ""  # "2026년 04월"
    total_sections: int = 0
    total_cards: int = 0
    total_appendices: int = 0
    total_refs: int = 0


# ── Quality Report: check_quality.py 출력 ──

IssueSeverity = Literal["FAIL", "WARNING", "INFO"]


class QualityIssueSchema(BaseModel):
    """품질 검증 이슈."""
    metric: str  # 예: "기술_카드_수"
    severity: IssueSeverity
    section_id: str = ""
    card_id: str = ""
    appendix_id: str = ""
    expected: str = ""
    actual: str = ""
    action: str = ""


class QualityReportSchema(BaseModel):
    """품질 검증 결과 (Phase A 12 + 기술연구 5 + 카드 6 = 23개 측정)."""
    schema_version: str = SCHEMA_VERSION
    phase_a: dict = Field(default_factory=dict)  # 23개 지표 값
    issues: list[QualityIssueSchema] = Field(default_factory=list)
    total_fail: int = 0
    total_warning: int = 0
    overall: float = 0.0  # 0.0~5.0


# ── Reference List: build_reflist.py 출력 ──

class CategoryCoverageSchema(BaseModel):
    """카테고리별 REF 분포."""
    category: Category
    count: int
    target: int
    ratio: float  # 전체 대비 비율


class ReferenceListSchema(BaseModel):
    """reference_list.json — merge_research.py + build_reflist.py 출력."""
    schema_version: str = SCHEMA_VERSION
    document_type: str = "기술보고서"
    total_refs: int = 0
    usable_refs: int = 0  # 확인됨·단일출처
    en_ratio: float = 0.0
    intl_org_count: int = 0
    academic_count: int = 0
    category_coverage: list[CategoryCoverageSchema] = Field(default_factory=list)
    section_coverage: dict[str, int] = Field(default_factory=dict)
    refs: list[KeyRefSchema] = Field(default_factory=list)


# ── Card Self-Check Result: writer 자체 검증 결과 (F2·F4 정합) ──

class SelfCheckResult(BaseModel):
    """writer subagent가 카드 작성 후 수행하는 자체 검증 결과.

    사이즈(S·L1·L2·L3)와 카드 type(tech/project/product) 무관하게 동일 스키마.
    모든 필드 optional — 기존 카드와 호환을 위해. 미기입은 WARN으로만 처리.

    F2(필드 비대칭) 해결: 한 곳에만 기록.
    F4(본문 인라인) 해결: 자체 검증 메모는 본문 텍스트가 아니라 이 객체로 출력.
    """
    model_config = {"extra": "forbid"}

    blocks_filled: bool | None = None
    """tech 7 / project 7 / product 6 블록을 모두 채웠는가."""

    refs_count: int | None = None
    """[REF-xxx] 인용 건수 (최소 5건 권장)."""

    min_length_ok: bool | None = None
    """카드 사이즈별 최소 분량 충족 여부."""

    ai_inference_below_threshold: bool | None = None
    """AI 추정 표현이 30% 미만인가."""

    no_unverified_markers: bool | None = None
    """본문에 [근거 미확인] 마커가 없는가."""

    notes: list[str] = Field(default_factory=list)
    """자유 메모 (필요 시). 본문 텍스트와 분리되어야 함."""


# ── Error Codes (TECHDOC-Exxx) ──

ERROR_CODES = {
    "TECHDOC-E001": "Plugin manifest invalid",
    "TECHDOC-E002": "Missing required environment",
    "TECHDOC-E010": "TOC parse failed",
    "TECHDOC-E020": "Research round produced no refs",
    "TECHDOC-E021": "Research merge failed (schema conflict)",
    "TECHDOC-E022": "KeyRef schema validation failed (drift)",
    "TECHDOC-E030": "Card write attempt failed (max retries)",
    "TECHDOC-E031": "Card below minimum length",
    "TECHDOC-E032": "Card block missing (required field)",
    "TECHDOC-E040": "Appendix write attempt failed",
    "TECHDOC-E041": "Appendix block below minimum length",
    "TECHDOC-E042": "WebSearch quota exhausted",
    "TECHDOC-E043": "WebSearch timeout (round exceeded budget)",
    "TECHDOC-E050": "Chart generation failed (matplotlib error)",
    "TECHDOC-E051": "MathJax/Mermaid rendering failed",
    "TECHDOC-E060": "PDF export failed (playwright missing or error)",
    "TECHDOC-E061": "DOCX export failed (python-docx missing or error)",
    "TECHDOC-E070": "Path traversal rejected (--ref file:)",
    "TECHDOC-E071": "File size exceeds 50MB limit",
    "TECHDOC-E080": "Schema version mismatch (migrate required)",
    "TECHDOC-E081": "Migration failed (unsupported version jump)",
    "TECHDOC-E090": "Quality FAIL gate triggered",
    "TECHDOC-E099": "Internal error (bug)",
}


def format_error(code: str, detail: str = "", fix: str = "", doc: str = "") -> str:
    """표준 에러 메시지 포맷 (TECHDOC-Exxx + 원인 + 수정 + 문서)."""
    title = ERROR_CODES.get(code, "Unknown error")
    lines = [f"ERROR [{code}]: {title}"]
    if detail:
        lines.append(f"\n원인: {detail}")
    if fix:
        lines.append(f"수정: {fix}")
    if doc:
        lines.append(f"문서: {doc}")
    return "\n".join(lines)
