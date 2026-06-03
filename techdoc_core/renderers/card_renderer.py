"""Card & Appendix HTML Renderer.

본문 카드 (tech/project/product) + 별첨 심층분석 (tech/project) 렌더링.
v1.4/v1.5 구조.
"""

from __future__ import annotations

import html

from techdoc_core.models import (
    ProductCard,
    ProjectAppendix,
    ProjectCard,
    TechAppendix,
    TechCard,
)

BLOCK_LABELS_TECH = {
    "overview": "기술 개요·배경",
    "principle": "작동 원리",
    "components": "구성 요소",
    "performance": "성능 지표",
    "pros_cons": "기술적 장단점",
    "differentiation": "차별점·한계·발전방향",
    "references": "근거·인용",
}

BLOCK_LABELS_PROJECT = {
    "background": "프로젝트 배경·목적",
    "organization": "수행 체계",
    "methodology": "연구 방법론",
    "results": "핵심 결과",
    "implications": "시사점·기술 기여",
    "followup": "후속 연구·파급 효과",
    "references": "근거·인용",
}

BLOCK_LABELS_PRODUCT = {
    "background": "배경·개발 동기",
    "features": "핵심 기능·차별점",
    "specifications": "기술 사양",
    "deployment": "실제 도입 사례",
    "market": "가격대·시장 위치",
    "references": "근거·인용",
}

BLOCK_LABELS_TECH_APPENDIX = {
    "overview": "기술 개요·연구사",
    "theory": "수학·물리 원리",
    "algorithms": "상세 알고리즘·프로토콜",
    "architecture": "구현 아키텍처",
    "benchmark": "성능 벤치마크",
    "implementations": "주요 구현체·오픈소스",
    "timeline": "연구 동향 타임라인",
    "limitations": "한계·미해결 과제",
    "future": "미래 연구 방향",
    "references": "전문 참고문헌",
}

BLOCK_LABELS_PROJECT_APPENDIX = {
    "chronicle": "프로젝트 연대기",
    "structure": "연구 체계",
    "phases": "단계별 기술 접근",
    "experiment": "실험 설계 상세",
    "datasets": "데이터셋·리소스",
    "results_deep": "핵심 결과 심층 분석",
    "followup": "파생·후속 연구",
    "comparison": "경쟁·보완 프로젝트 비교",
    "industry": "상업화·산업 응용",
    "researchers": "핵심 연구자 프로필",
    "references": "전문 참고문헌",
}


def render_card_visuals(card) -> str:
    """카드의 figures·diagrams를 HTML로 출력 (F22). 비어 있으면 빈 문자열.

    path·caption은 평문 메타데이터이므로 escape한다. mermaid 소스는 mermaid.js가
    파싱하는 다이어그램 코드이므로 escape하지 않는다.
    """
    parts: list[str] = []
    for fig in getattr(card, "figures", []) or []:
        if not isinstance(fig, dict):
            continue
        path = fig.get("path", "")
        caption = fig.get("caption", "")
        if not path:
            continue
        esc_path, esc_cap = html.escape(path, quote=True), html.escape(caption, quote=True)
        cap_html = f"<figcaption>{esc_cap}</figcaption>" if caption else ""
        parts.append(f'<figure class="card-figure"><img src="{esc_path}" alt="{esc_cap}">{cap_html}</figure>')
    for dia in getattr(card, "diagrams", []) or []:
        if not isinstance(dia, dict):
            continue
        src = dia.get("mermaid", "")
        caption = dia.get("caption", "")
        if not src:
            continue
        cap_html = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
        parts.append(f'<figure class="card-diagram"><pre class="mermaid">{src}</pre>{cap_html}</figure>')
    if not parts:
        return ""
    return '<div class="card-visuals">\n' + "\n".join(parts) + "\n</div>"


def render_tech_card(card: TechCard) -> str:
    """본문 기술 카드 HTML 렌더링 (섹션 내 배치용)."""
    importance_class = f"importance-{card.importance}"
    name_en = f' <span class="name-en">({card.name_en})</span>' if card.name_en else ""
    appendix_link = (
        f'<div class="card-footer">→ 본 기술의 수식·알고리즘·구현체 상세는 '
        f'<a href="#appendix-tech-{card.id}">부록 참조</a></div>'
    )

    blocks_html = ""
    for key, label in BLOCK_LABELS_TECH.items():
        content = getattr(card, key, "")
        if content:
            blocks_html += f'<div class="card-block block-{key}">'
            blocks_html += f'<h4>{label}</h4>{content}'
            blocks_html += "</div>\n"
    blocks_html += render_card_visuals(card)   # F22: 시각 자산을 본문 끝에

    return f"""
<section class="tech-card {importance_class}" id="card-{card.id}">
  <header class="card-header">
    <span class="card-type">[기술]</span>
    <h3>{card.id} {card.name}{name_en}</h3>
  </header>
  <div class="card-body">
    {blocks_html}
  </div>
  {appendix_link}
</section>
""".strip()


def render_project_card(card: ProjectCard) -> str:
    """본문 프로젝트 카드 HTML 렌더링."""
    importance_class = f"importance-{card.importance}"
    name_en = f' <span class="name-en">({card.name_en})</span>' if card.name_en else ""

    # 메타 박스
    meta_items = []
    if card.institution:
        meta_items.append(f"<dt>기관</dt><dd>{card.institution}</dd>")
    if card.pi:
        meta_items.append(f"<dt>PI</dt><dd>{card.pi}</dd>")
    if card.period:
        meta_items.append(f"<dt>기간</dt><dd>{card.period}</dd>")
    if card.budget:
        meta_items.append(f"<dt>예산</dt><dd>{card.budget}</dd>")
    if card.sponsor:
        meta_items.append(f"<dt>자금원</dt><dd>{card.sponsor}</dd>")
    meta_html = (
        f'<dl class="project-meta">{"".join(meta_items)}</dl>' if meta_items else ""
    )

    blocks_html = ""
    for key, label in BLOCK_LABELS_PROJECT.items():
        content = getattr(card, key, "")
        if content:
            blocks_html += f'<div class="card-block block-{key}"><h4>{label}</h4>{content}</div>\n'
    blocks_html += render_card_visuals(card)   # F22: 시각 자산을 본문 끝에

    appendix_link = (
        f'<div class="card-footer">→ 본 프로젝트의 단계별 방법·상세 결과는 '
        f'<a href="#appendix-project-{card.id}">부록 참조</a></div>'
    )

    return f"""
<section class="project-card {importance_class}" id="card-{card.id}">
  <header class="card-header">
    <span class="card-type">[프로젝트]</span>
    <h3>{card.id} {card.name}{name_en}</h3>
  </header>
  {meta_html}
  <div class="card-body">
    {blocks_html}
  </div>
  {appendix_link}
</section>
""".strip()


def render_product_card(card: ProductCard) -> str:
    """본문 제품 카드 HTML 렌더링."""
    importance_class = f"importance-{card.importance}"

    meta_items = []
    if card.model:
        meta_items.append(f"<dt>모델</dt><dd>{card.model}</dd>")
    if card.maker:
        maker_country = f"{card.maker} ({card.country})" if card.country else card.maker
        meta_items.append(f"<dt>제조사</dt><dd>{maker_country}</dd>")
    meta_html = (
        f'<dl class="product-meta">{"".join(meta_items)}</dl>' if meta_items else ""
    )

    blocks_html = ""
    for key, label in BLOCK_LABELS_PRODUCT.items():
        content = getattr(card, key, "")
        if content:
            blocks_html += f'<div class="card-block block-{key}"><h4>{label}</h4>{content}</div>\n'
    blocks_html += render_card_visuals(card)   # F22: 시각 자산을 본문 끝에

    return f"""
<section class="product-card {importance_class}" id="card-{card.id}">
  <header class="card-header">
    <span class="card-type">[제품]</span>
    <h3>{card.id} {card.name}</h3>
  </header>
  {meta_html}
  <div class="card-body">
    {blocks_html}
  </div>
</section>
""".strip()


def render_tech_appendix(appendix: TechAppendix) -> str:
    """기술 심층분석 별첨 HTML 렌더링 (문서 말미 Appendix)."""
    name_en = f' <span class="name-en">({appendix.name_en})</span>' if appendix.name_en else ""
    back_link = (
        f'<div class="appendix-header"><a href="#card-{appendix.source_card_id}">'
        f'← 본문 {appendix.source_card_id} 카드로 돌아가기</a></div>'
    )

    blocks_html = ""
    for key, label in BLOCK_LABELS_TECH_APPENDIX.items():
        content = getattr(appendix, key, "")
        if content:
            blocks_html += f'<div class="appendix-block block-{key}">'
            blocks_html += f'<h3>{label}</h3>{content}'
            blocks_html += "</div>\n"

    return f"""
<section class="tech-appendix" id="appendix-tech-{appendix.source_card_id}">
  <header class="appendix-cover">
    <div class="appendix-id">부록 {appendix.id}</div>
    <span class="appendix-type">[기술 심층분석]</span>
    <h2>{appendix.name}{name_en}</h2>
  </header>
  {back_link}
  <div class="appendix-body">
    {blocks_html}
  </div>
</section>
""".strip()


def render_project_appendix(appendix: ProjectAppendix) -> str:
    """프로젝트 심층분석 별첨 HTML 렌더링."""
    name_en = f' <span class="name-en">({appendix.name_en})</span>' if appendix.name_en else ""
    back_link = (
        f'<div class="appendix-header"><a href="#card-{appendix.source_card_id}">'
        f'← 본문 {appendix.source_card_id} 카드로 돌아가기</a></div>'
    )

    # 메타 박스 (프로젝트 정보)
    meta_items = []
    for label, value in [
        ("수행 기관", appendix.institution),
        ("연구 책임자", appendix.pi),
        ("기간", appendix.period),
        ("예산", appendix.budget),
        ("자금원", appendix.sponsor),
    ]:
        if value:
            meta_items.append(f"<dt>{label}</dt><dd>{value}</dd>")
    meta_html = f'<dl class="appendix-meta">{"".join(meta_items)}</dl>' if meta_items else ""

    blocks_html = ""
    for key, label in BLOCK_LABELS_PROJECT_APPENDIX.items():
        content = getattr(appendix, key, "")
        if content:
            blocks_html += f'<div class="appendix-block block-{key}">'
            blocks_html += f'<h3>{label}</h3>{content}'
            blocks_html += "</div>\n"

    return f"""
<section class="project-appendix" id="appendix-project-{appendix.source_card_id}">
  <header class="appendix-cover">
    <div class="appendix-id">부록 {appendix.id}</div>
    <span class="appendix-type">[프로젝트 심층분석]</span>
    <h2>{appendix.name}{name_en}</h2>
  </header>
  {meta_html}
  {back_link}
  <div class="appendix-body">
    {blocks_html}
  </div>
</section>
""".strip()


def render_all_appendices(
    tech_appendices: list[TechAppendix],
    project_appendices: list[ProjectAppendix],
) -> str:
    """전체 별첨 섹션 렌더링 (문서 말미 "부록" 블록)."""
    if not tech_appendices and not project_appendices:
        return ""

    # 부록 TOC
    toc_items = []
    for a in tech_appendices:
        toc_items.append(
            f'<li><a href="#appendix-tech-{a.source_card_id}">부록 {a.id} [기술] {a.name}</a></li>'
        )
    for a in project_appendices:
        toc_items.append(
            f'<li><a href="#appendix-project-{a.source_card_id}">부록 {a.id} [프로젝트] {a.name}</a></li>'
        )
    toc_html = f'<nav class="appendix-toc"><h2>부록 목차</h2><ol>{"".join(toc_items)}</ol></nav>'

    body = ""
    for a in tech_appendices:
        body += render_tech_appendix(a) + "\n"
    for a in project_appendices:
        body += render_project_appendix(a) + "\n"

    return f"""
<section class="appendices" id="appendices">
  <header class="appendices-cover">
    <h1>부록 (Appendices)</h1>
    <p class="appendices-note">핵심 기술·프로젝트의 상세 리뷰 — 수식·알고리즘·벤치마크·비판 포함</p>
  </header>
  {toc_html}
  {body}
</section>
""".strip()


def render_mathjax_header() -> str:
    """MathJax CDN 로더 (수식 렌더링)."""
    return """
<script>
  MathJax = {
    tex: {
      inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
      displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
      processEscapes: true
    }
  };
</script>
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
<script id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
""".strip()


def render_mermaid_header() -> str:
    """Mermaid CDN 로더 (시퀀스·상태·컴포넌트 다이어그램)."""
    return """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'default' });
</script>
""".strip()


def has_math_or_mermaid(appendices: list, cards: list | None = None) -> bool:
    """별첨·본문 카드에 MathJax/Mermaid 필요 여부 확인."""
    for a in appendices:
        blocks_content = ""
        if isinstance(a, TechAppendix):
            blocks_content = a.theory + a.algorithms + a.architecture
        elif isinstance(a, ProjectAppendix):
            blocks_content = a.phases + a.experiment + a.results_deep
        if "$$" in blocks_content or "\\(" in blocks_content:
            return True
        if "```mermaid" in blocks_content or "<pre class=\"mermaid\"" in blocks_content:
            return True
    for c in cards or []:
        for dia in getattr(c, "diagrams", []) or []:
            if dia.get("mermaid"):
                return True
    return False
