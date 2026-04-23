"""Techdoc 데이터 모델."""

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


@dataclass
class Document:
    """완성된 문서."""

    title: str
    subtitle: str = ""
    sections: list[DocumentSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    figures: list[dict] = field(default_factory=list)  # ChartGenerator 출력

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "sections": [s.to_dict() for s in self.sections],
            "metadata": self.metadata,
            "figures": self.figures,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Document:
        return cls(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            sections=[DocumentSection.from_dict(s) for s in data.get("sections", [])],
            metadata=data.get("metadata", {}),
            figures=data.get("figures", []),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Document:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


# ── 유틸리티 ──


def save_json(data: Any, path: Path) -> None:
    """JSON 파일로 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    """JSON 파일 로드."""
    return json.loads(path.read_text(encoding="utf-8"))
