"""TechDoc Plugin 데이터 모델."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── 문서 구조 ──


@dataclass
class Section:
    """문서 섹션 정의."""

    id: str  # "1.2"
    title: str  # "관개·배수 자동화 시스템"
    subtopics: list[str] = field(default_factory=list)
    analysis_tags: list[str] = field(default_factory=list)  # ["[분석: 구조분석]"]
    estimated_length: str = "medium"  # short|medium|long
    ref_ids: list[str] = field(default_factory=list)  # ["REF-001", "REF-003"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "subtopics": self.subtopics,
            "analysis_tags": self.analysis_tags,
            "estimated_length": self.estimated_length,
            "ref_ids": self.ref_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Section:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            subtopics=data.get("subtopics", []),
            analysis_tags=data.get("analysis_tags", []),
            estimated_length=data.get("estimated_length", "medium"),
            ref_ids=data.get("ref_ids", []),
        )


@dataclass
class Outline:
    """문서 전체 구조."""

    title: str
    document_type: str = "기술보고서"
    target_audience: str = "관련 분야 전문가 및 실무자"
    sections: list[Section] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)  # {"스마트농업": "정의..."}

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "document_type": self.document_type,
            "target_audience": self.target_audience,
            "sections": [s.to_dict() for s in self.sections],
            "glossary": self.glossary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Outline:
        return cls(
            title=data.get("title", ""),
            document_type=data.get("document_type", "기술보고서"),
            target_audience=data.get("target_audience", ""),
            sections=[Section.from_dict(s) for s in data.get("sections", [])],
            glossary=data.get("glossary", {}),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Outline:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


# ── 레퍼런스 ──


@dataclass
class KeyData:
    """레퍼런스의 핵심 데이터 포인트."""

    data: str  # "스마트농업 보급률 12.3%"
    context: str = ""  # "전체 농가 대비"
    cross_verified: bool = False  # 교차 검증 여부

    def to_dict(self) -> dict:
        return {"data": self.data, "context": self.context, "cross_verified": self.cross_verified}

    @classmethod
    def from_dict(cls, data: dict) -> KeyData:
        return cls(
            data=data.get("data", ""),
            context=data.get("context", ""),
            cross_verified=data.get("cross_verified", False),
        )


@dataclass
class Reference:
    """검증된 레퍼런스."""

    id: str  # "REF-001"
    title: str
    source: str  # 발행 기관
    year: int
    url: str = ""
    type: str = ""  # "정부통계", "학술논문" 등
    category: str = ""  # "정부공공", "국제기구", "학술", "산업", "뉴스"
    language: str = "ko"
    reliability: str = "단일출처"  # "확인됨"|"단일출처"|"미확인"|"AI지식"
    file: str = ""  # KeyRef/ 경로
    key_data: list[KeyData] = field(default_factory=list)
    related_sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "year": self.year,
            "url": self.url,
            "type": self.type,
            "category": self.category,
            "language": self.language,
            "reliability": self.reliability,
            "file": self.file,
            "key_data": [kd.to_dict() for kd in self.key_data],
            "related_sections": self.related_sections,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Reference:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            source=data.get("source", ""),
            year=data.get("year", 0),
            url=data.get("url", ""),
            type=data.get("type", ""),
            category=data.get("category", ""),
            language=data.get("language", "ko"),
            reliability=data.get("reliability", "단일출처"),
            file=data.get("file", ""),
            key_data=[KeyData.from_dict(kd) for kd in data.get("key_data", [])],
            related_sections=data.get("related_sections", []),
        )


@dataclass
class DataConflict:
    """출처 간 데이터 충돌."""

    topic: str
    values: list[dict] = field(default_factory=list)  # [{"value": ..., "source": ..., "year": ...}]
    resolution: str = ""

    def to_dict(self) -> dict:
        return {"topic": self.topic, "values": self.values, "resolution": self.resolution}

    @classmethod
    def from_dict(cls, data: dict) -> DataConflict:
        return cls(
            topic=data.get("topic", ""),
            values=data.get("values", []),
            resolution=data.get("resolution", ""),
        )


@dataclass
class SectionCoverage:
    """섹션별 레퍼런스 커버리지."""

    section: str
    ref_count: int
    status: str  # "충분"|"최소"|"부족"

    def to_dict(self) -> dict:
        return {"section": self.section, "ref_count": self.ref_count, "status": self.status}

    @classmethod
    def from_dict(cls, data: dict) -> SectionCoverage:
        return cls(
            section=data.get("section", ""),
            ref_count=data.get("ref_count", 0),
            status=data.get("status", "부족"),
        )


@dataclass
class ReferenceList:
    """전체 레퍼런스 목록."""

    references: list[Reference] = field(default_factory=list)
    section_coverage: list[SectionCoverage] = field(default_factory=list)
    data_conflicts: list[DataConflict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata,
            "references": [r.to_dict() for r in self.references],
            "section_coverage": [sc.to_dict() for sc in self.section_coverage],
            "data_conflicts": [dc.to_dict() for dc in self.data_conflicts],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReferenceList:
        return cls(
            references=[Reference.from_dict(r) for r in data.get("references", [])],
            section_coverage=[SectionCoverage.from_dict(sc) for sc in data.get("section_coverage", [])],
            data_conflicts=[DataConflict.from_dict(dc) for dc in data.get("data_conflicts", [])],
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ReferenceList:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def get_refs_for_section(self, section_id: str) -> list[Reference]:
        """특정 섹션에 매핑된 레퍼런스 반환."""
        return [r for r in self.references if section_id in r.related_sections]

    def get_usable_refs(self) -> list[Reference]:
        """인용 가능한(확인됨/단일출처) 레퍼런스만 반환."""
        from techdoc_core.constants import RELIABILITY_LEVELS
        return [r for r in self.references if RELIABILITY_LEVELS.get(r.reliability, {}).get("usable", False)]


# ── 사용자 제공 참고 자료 ──


@dataclass
class UserSource:
    """사용자가 제공한 참고 자료."""

    type: str  # "file" | "url" | "site"
    path: str  # 파일 경로 또는 URL
    description: str = ""  # 사용자 설명 (선택)
    content: str = ""  # 추출된 텍스트 내용
    extracted_urls: list[str] = field(default_factory=list)  # 문서 내 발견된 URL
    extracted_refs: list[str] = field(default_factory=list)  # 문서 내 참고문헌

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "path": self.path,
            "description": self.description,
            "content_length": len(self.content),
            "extracted_urls": self.extracted_urls,
            "extracted_refs": self.extracted_refs,
        }


# ── 문서 ──


@dataclass
class DocumentSection:
    """작성된 문서 섹션."""

    section_id: str
    title: str
    html_content: str = ""
    order: int = 0

    def to_dict(self) -> dict:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "html_content": self.html_content,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocumentSection:
        return cls(
            section_id=data.get("section_id", ""),
            title=data.get("title", ""),
            html_content=data.get("html_content", ""),
            order=data.get("order", 0),
        )


# ── 본문 카드 (v1.2: tech/project/product 독립 카드 구조) ──


@dataclass
class TechCard:
    """기술 카드 — 7블록 구조 (본문 섹션 내 배치).

    분량 기준 (중요도별):
      high: 2,500~3,500자 / medium: 1,500~2,500자 / low: 800~1,500자
    """

    id: str  # "1.1.1" — section.card
    name: str  # 기술 이름 (한국어)
    name_en: str = ""
    importance: str = "medium"  # high|medium|low
    # 7블록 HTML 조각
    overview: str = ""  # ① 기술 개요·배경
    principle: str = ""  # ② 작동 원리 (알고리즘·프로토콜 단계별)
    components: str = ""  # ③ 구성 요소 (HW/SW)
    performance: str = ""  # ④ 성능 지표 (정량)
    pros_cons: str = ""  # ⑤ 기술적 장단점
    differentiation: str = ""  # ⑥ 차별점·한계·발전방향
    references: str = ""  # ⑦ 근거·인용 (REF 리스트)
    ref_ids: list[str] = field(default_factory=list)
    self_check: dict | None = None  # F2/F4: 사이즈 무관 self-check (None 허용 — 역호환)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_en": self.name_en,
            "importance": self.importance,
            "blocks": {
                "overview": self.overview,
                "principle": self.principle,
                "components": self.components,
                "performance": self.performance,
                "pros_cons": self.pros_cons,
                "differentiation": self.differentiation,
                "references": self.references,
            },
            "ref_ids": self.ref_ids,
            "self_check": self.self_check,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TechCard:
        blocks = data.get("blocks", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            importance=data.get("importance", "medium"),
            overview=blocks.get("overview", ""),
            principle=blocks.get("principle", ""),
            components=blocks.get("components", ""),
            performance=blocks.get("performance", ""),
            pros_cons=blocks.get("pros_cons", ""),
            differentiation=blocks.get("differentiation", ""),
            references=blocks.get("references", ""),
            ref_ids=data.get("ref_ids", []),
            self_check=data.get("self_check"),
        )


@dataclass
class ProjectCard:
    """프로젝트 카드 — 7블록 구조.

    분량 기준:
      high: 3,000~4,000자 / medium: 2,000~3,000자 / low: 1,200~2,000자
    """

    id: str
    name: str
    name_en: str = ""
    importance: str = "medium"
    # 7블록
    background: str = ""  # ① 프로젝트 배경·목적
    organization: str = ""  # ② 수행 체계 (기관·PI·기간·예산·자금원)
    methodology: str = ""  # ③ 연구 방법론 (실험 설계·데이터셋·장비)
    results: str = ""  # ④ 핵심 결과 (정량)
    implications: str = ""  # ⑤ 시사점·기술 기여
    followup: str = ""  # ⑥ 후속 연구·파급 효과
    references: str = ""  # ⑦ 근거·인용
    ref_ids: list[str] = field(default_factory=list)
    # 프로젝트 메타
    institution: str = ""
    pi: str = ""
    period: str = ""
    budget: str = ""
    sponsor: str = ""
    self_check: dict | None = None  # F2/F4: 사이즈 무관 self-check (None 허용 — 역호환)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_en": self.name_en,
            "importance": self.importance,
            "meta": {
                "institution": self.institution,
                "pi": self.pi,
                "period": self.period,
                "budget": self.budget,
                "sponsor": self.sponsor,
            },
            "blocks": {
                "background": self.background,
                "organization": self.organization,
                "methodology": self.methodology,
                "results": self.results,
                "implications": self.implications,
                "followup": self.followup,
                "references": self.references,
            },
            "ref_ids": self.ref_ids,
            "self_check": self.self_check,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectCard:
        meta = data.get("meta", {})
        blocks = data.get("blocks", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            importance=data.get("importance", "medium"),
            institution=meta.get("institution", ""),
            pi=meta.get("pi", ""),
            period=meta.get("period", ""),
            budget=meta.get("budget", ""),
            sponsor=meta.get("sponsor", ""),
            background=blocks.get("background", ""),
            organization=blocks.get("organization", ""),
            methodology=blocks.get("methodology", ""),
            results=blocks.get("results", ""),
            implications=blocks.get("implications", ""),
            followup=blocks.get("followup", ""),
            references=blocks.get("references", ""),
            ref_ids=data.get("ref_ids", []),
            self_check=data.get("self_check"),
        )


@dataclass
class ProductCard:
    """제품 카드 — 6블록 구조.

    분량 기준:
      high: 1,500~2,000자 / medium: 1,000~1,500자 / low: 600~1,000자
    """

    id: str
    name: str
    model: str = ""
    maker: str = ""
    country: str = ""
    importance: str = "medium"
    # 6블록
    background: str = ""  # ① 제품 배경·개발 동기
    features: str = ""  # ② 핵심 기능·차별점
    specifications: str = ""  # ③ 기술 사양 (스펙·프로토콜·인증)
    deployment: str = ""  # ④ 실제 도입 사례
    market: str = ""  # ⑤ 가격대·시장 위치
    references: str = ""  # ⑥ 근거·인용
    ref_ids: list[str] = field(default_factory=list)
    self_check: dict | None = None  # F2/F4: 사이즈 무관 self-check (None 허용 — 역호환)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "maker": self.maker,
            "country": self.country,
            "importance": self.importance,
            "blocks": {
                "background": self.background,
                "features": self.features,
                "specifications": self.specifications,
                "deployment": self.deployment,
                "market": self.market,
                "references": self.references,
            },
            "ref_ids": self.ref_ids,
            "self_check": self.self_check,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProductCard:
        blocks = data.get("blocks", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            model=data.get("model", ""),
            maker=data.get("maker", ""),
            country=data.get("country", ""),
            importance=data.get("importance", "medium"),
            background=blocks.get("background", ""),
            features=blocks.get("features", ""),
            specifications=blocks.get("specifications", ""),
            deployment=blocks.get("deployment", ""),
            market=blocks.get("market", ""),
            references=blocks.get("references", ""),
            ref_ids=data.get("ref_ids", []),
            self_check=data.get("self_check"),
        )


# ── 별첨 심층분석 (v1.4 + v1.5 2배 확대) ──


@dataclass
class TechAppendix:
    """기술 심층분석 — 10블록 구조 (문서 말미 Appendix).

    분량 기준 (v1.5 확대):
      최소 15,000자 / 권장 20,000~25,000자 / 상한 40,000자 (15~35페이지)
    """

    id: str  # "A.1" — Appendix letter + index
    source_card_id: str  # 연결된 본문 카드 ID (예: "1.1.1")
    name: str
    name_en: str = ""
    # 10블록 HTML 조각 (분량 권장 — 25,000자 기준)
    overview: str = ""  # ① 기술 개요·연구사 (1,500~2,000자)
    theory: str = ""  # ② 수학·물리 원리 (3,000~4,000자)
    algorithms: str = ""  # ③ 상세 알고리즘·프로토콜 (5,000~6,500자)
    architecture: str = ""  # ④ 구현 아키텍처 (2,500~3,000자)
    benchmark: str = ""  # ⑤ 성능 벤치마크 (3,000~4,000자)
    implementations: str = ""  # ⑥ 주요 구현체·오픈소스 (1,500~2,000자)
    timeline: str = ""  # ⑦ 연구 동향 타임라인 (1,500~2,000자)
    limitations: str = ""  # ⑧ 한계·미해결 과제 (2,500~3,000자)
    future: str = ""  # ⑨ 미래 연구 방향 (1,500~2,000자)
    references: str = ""  # ⑩ 전문 참고문헌 (20~30건)
    ref_ids: list[str] = field(default_factory=list)
    # 시각화 메타
    equations: list[dict] = field(default_factory=list)  # MathJax/LaTeX
    diagrams: list[dict] = field(default_factory=list)  # Mermaid/matplotlib

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_card_id": self.source_card_id,
            "name": self.name,
            "name_en": self.name_en,
            "type": "tech",
            "blocks": {
                "overview": self.overview,
                "theory": self.theory,
                "algorithms": self.algorithms,
                "architecture": self.architecture,
                "benchmark": self.benchmark,
                "implementations": self.implementations,
                "timeline": self.timeline,
                "limitations": self.limitations,
                "future": self.future,
                "references": self.references,
            },
            "ref_ids": self.ref_ids,
            "equations": self.equations,
            "diagrams": self.diagrams,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TechAppendix:
        blocks = data.get("blocks", {})
        return cls(
            id=data.get("id", ""),
            source_card_id=data.get("source_card_id", ""),
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            overview=blocks.get("overview", ""),
            theory=blocks.get("theory", ""),
            algorithms=blocks.get("algorithms", ""),
            architecture=blocks.get("architecture", ""),
            benchmark=blocks.get("benchmark", ""),
            implementations=blocks.get("implementations", ""),
            timeline=blocks.get("timeline", ""),
            limitations=blocks.get("limitations", ""),
            future=blocks.get("future", ""),
            references=blocks.get("references", ""),
            ref_ids=data.get("ref_ids", []),
            equations=data.get("equations", []),
            diagrams=data.get("diagrams", []),
        )


@dataclass
class ProjectAppendix:
    """프로젝트 심층분석 — 11블록 구조.

    분량 기준 (v1.5 확대):
      최소 20,000자 / 권장 25,000~30,000자 / 상한 50,000자 (20~40페이지)
    """

    id: str
    source_card_id: str
    name: str
    name_en: str = ""
    # 11블록 (30,000자 기준)
    chronicle: str = ""  # ① 프로젝트 연대기 (2,000~2,500자)
    structure: str = ""  # ② 연구 체계 (1,500~2,000자 + 조직도)
    phases: str = ""  # ③ 단계별 기술 접근 (5,000~6,000자)
    experiment: str = ""  # ④ 실험 설계 상세 (4,500~5,500자)
    datasets: str = ""  # ⑤ 데이터셋·리소스 (1,500~2,000자)
    results_deep: str = ""  # ⑥ 핵심 결과 심층 (5,500~6,500자)
    followup: str = ""  # ⑦ 파생·후속 연구 (2,500~3,000자)
    comparison: str = ""  # ⑧ 경쟁·보완 프로젝트 비교 (2,500~3,000자)
    industry: str = ""  # ⑨ 상업화·산업 응용 (1,500~2,000자)
    researchers: str = ""  # ⑩ 핵심 연구자 프로필 (1,500~2,000자)
    references: str = ""  # ⑪ 전문 참고문헌 (25~40건)
    ref_ids: list[str] = field(default_factory=list)
    # 프로젝트 메타
    institution: str = ""
    pi: str = ""
    period: str = ""
    budget: str = ""
    sponsor: str = ""
    # 시각화
    timeline_chart: dict = field(default_factory=dict)
    org_chart: dict = field(default_factory=dict)
    diagrams: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_card_id": self.source_card_id,
            "name": self.name,
            "name_en": self.name_en,
            "type": "project",
            "meta": {
                "institution": self.institution,
                "pi": self.pi,
                "period": self.period,
                "budget": self.budget,
                "sponsor": self.sponsor,
            },
            "blocks": {
                "chronicle": self.chronicle,
                "structure": self.structure,
                "phases": self.phases,
                "experiment": self.experiment,
                "datasets": self.datasets,
                "results_deep": self.results_deep,
                "followup": self.followup,
                "comparison": self.comparison,
                "industry": self.industry,
                "researchers": self.researchers,
                "references": self.references,
            },
            "ref_ids": self.ref_ids,
            "timeline_chart": self.timeline_chart,
            "org_chart": self.org_chart,
            "diagrams": self.diagrams,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectAppendix:
        meta = data.get("meta", {})
        blocks = data.get("blocks", {})
        return cls(
            id=data.get("id", ""),
            source_card_id=data.get("source_card_id", ""),
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            institution=meta.get("institution", ""),
            pi=meta.get("pi", ""),
            period=meta.get("period", ""),
            budget=meta.get("budget", ""),
            sponsor=meta.get("sponsor", ""),
            chronicle=blocks.get("chronicle", ""),
            structure=blocks.get("structure", ""),
            phases=blocks.get("phases", ""),
            experiment=blocks.get("experiment", ""),
            datasets=blocks.get("datasets", ""),
            results_deep=blocks.get("results_deep", ""),
            followup=blocks.get("followup", ""),
            comparison=blocks.get("comparison", ""),
            industry=blocks.get("industry", ""),
            researchers=blocks.get("researchers", ""),
            references=blocks.get("references", ""),
            ref_ids=data.get("ref_ids", []),
            timeline_chart=data.get("timeline_chart", {}),
            org_chart=data.get("org_chart", {}),
            diagrams=data.get("diagrams", []),
        )


# ── Document: 최종 문서 (v1.5: 카드·별첨 지원 확장) ──


@dataclass
class Document:
    """완성된 문서 (본문 카드 + 별첨 심층분석)."""

    title: str
    subtitle: str = ""
    sections: list[DocumentSection] = field(default_factory=list)
    tech_cards: list[TechCard] = field(default_factory=list)
    project_cards: list[ProjectCard] = field(default_factory=list)
    product_cards: list[ProductCard] = field(default_factory=list)
    tech_appendices: list[TechAppendix] = field(default_factory=list)
    project_appendices: list[ProjectAppendix] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    figures: list[dict] = field(default_factory=list)  # ChartGenerator 출력
    schema_version: str = "0.1.0"

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "subtitle": self.subtitle,
            "sections": [s.to_dict() for s in self.sections],
            "tech_cards": [c.to_dict() for c in self.tech_cards],
            "project_cards": [c.to_dict() for c in self.project_cards],
            "product_cards": [c.to_dict() for c in self.product_cards],
            "tech_appendices": [a.to_dict() for a in self.tech_appendices],
            "project_appendices": [a.to_dict() for a in self.project_appendices],
            "metadata": self.metadata,
            "figures": self.figures,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Document:
        return cls(
            schema_version=data.get("schema_version", "0.1.0"),
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            sections=[DocumentSection.from_dict(s) for s in data.get("sections", [])],
            tech_cards=[TechCard.from_dict(c) for c in data.get("tech_cards", [])],
            project_cards=[ProjectCard.from_dict(c) for c in data.get("project_cards", [])],
            product_cards=[ProductCard.from_dict(c) for c in data.get("product_cards", [])],
            tech_appendices=[TechAppendix.from_dict(a) for a in data.get("tech_appendices", [])],
            project_appendices=[ProjectAppendix.from_dict(a) for a in data.get("project_appendices", [])],
            metadata=data.get("metadata", {}),
            figures=data.get("figures", []),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Document:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def cards_for_section(self, section_id: str) -> dict:
        """섹션의 모든 카드 (tech/project/product) 반환."""
        sid = section_id + "."
        return {
            "tech": [c for c in self.tech_cards if c.id.startswith(sid)],
            "project": [c for c in self.project_cards if c.id.startswith(sid)],
            "product": [c for c in self.product_cards if c.id.startswith(sid)],
        }


# ── 유틸리티 ──


def save_json(data: Any, path: Path) -> None:
    """JSON 파일로 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    """JSON 파일 로드."""
    return json.loads(path.read_text(encoding="utf-8"))
