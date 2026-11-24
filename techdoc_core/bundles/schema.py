"""묶음 명세 스키마 — 규칙(RuleSpec)·게이트(GateSpec) (v1.11 — F85·F104).

RuleSpec은 시리즈 규칙 대장(rules.yaml)의 필드를 그대로 받는다(필수 7개 검증, 나머지 허용).
GateSpec의 판정 수준(level)과 판정(verdict, 엔진이 계산)은 서로 다른 축이다(설계 D17).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Level = Literal["막음", "경고", "기록만", "시범", "구조"]
Layer = Literal["본체", "문서종류", "분야", "시리즈", "프로젝트"]
Core = Literal["품질", "일관성", "쉬운 말"]
Scope = Literal["문서 안", "문서 사이", "산출물"]
Input = Literal["cards", "tree", "references", "reference_md"]


class RuleSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., pattern=r"^(P|W|Q[1-9])-\d{3}[a-z]?$")
    title: str
    rule: str
    core: list[Core]
    area: str
    layer: Layer
    status: str
    enforce: list[dict] = Field(default_factory=list)
    rel: dict = Field(default_factory=dict)


class GateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    rules: list[str] = Field(default_factory=list)
    # 아래 층(문서 종류·분야·시리즈) 규칙 id — 공개 본체 규칙 묶음(bundles/core/rules.yaml)에 없고
    # private 묶음에 있다. `rules:`에는 공개 본체 규칙만 둔다 (v1.11-c, E15)
    lower_rules: list[str] = Field(default_factory=list)
    layer: Layer
    core: list[Core] = Field(default_factory=list)
    level: Level
    scope: Scope = "문서 안"
    inputs: list[Input]
    expects: dict[str, str] = Field(default_factory=dict)
    promotion: dict | None = None
    override: bool = False
    # 원본이 hit()를 거치지 않아 면제가 먹지 않던 게이트(V6·V7·V8·V12 일부·V13·V59)는 false
    exemptable: bool = True
    # 적용 문서 종류 — 비면 모든 종류. 밖의 종류면 엔진이 skip(「문서 종류 밖」)으로 둔다
    kinds: list[str] = Field(default_factory=list)
