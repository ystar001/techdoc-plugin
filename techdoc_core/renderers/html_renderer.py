"""HTML Renderer — Document + DesignSystem → HTML 파일 생성."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

from techdoc_core.models import Document, ReferenceList

console = Console()


class HTMLRenderer:
    """HTML 문서 렌더링."""

    def render(
        self,
        document: Document,
        css: str,
        output_dir: Path,
        filename: str = "document.html",
        ref_list: ReferenceList | None = None,
    ) -> Path:
        """Document를 HTML 파일로 렌더링.

        Args:
            document: 완성된 문서
            css: 디자인 CSS (components + cover + print)
            output_dir: 출력 디렉토리
            filename: 출력 파일명

        Returns:
            Path: 생성된 HTML 파일 경로
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 표지 메타데이터 추출
        title_parts = self._parse_title(document.title)

        # 본문 섹션 HTML
        sections_html = self._build_sections(document)

        # 상호 참조 해소
        sections_html = self._resolve_cross_refs(sections_html, document)

        # 표/그림 자동 번호 부여 + 목록 수집
        sections_html, table_list, figure_list = self._number_tables_figures(sections_html)

        # 인용 [REF-xxx]를 각주 인덱스로 변환
        sections_html, footnotes = self._convert_citations(sections_html, ref_list)

        # 목차 생성
        toc_html = self._build_toc(document, table_list, figure_list)

        # 표 목차 + 그림 목차
        table_toc_html = self._build_table_figure_toc(table_list, figure_list)

        # 약어 목록
        abbreviations_html = self._build_abbreviations(document)

        # 참고문헌 (ReferenceList가 있으면 링크 포함)
        references_html = self._build_references(document, ref_list)

        # 각주 섹션
        footnotes_html = self._build_footnotes(footnotes)

        # 전체 HTML 조립
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{document.title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" rel="stylesheet">
    <style>
{css}
    </style>
</head>
<body>

<!-- 표지 -->
<div class="cover-page">
    <div class="cover-content">
        <h1 class="cover-title">{title_parts['main_title']}</h1>
        {f'<div class="cover-divider"></div>' if title_parts['part'] else ''}
        {f'<p class="cover-part">{title_parts["part"]}</p>' if title_parts['part'] else ''}
        {f'<p class="cover-chapter">{title_parts["chapter"]}</p>' if title_parts['chapter'] else ''}
    </div>
    <div class="cover-meta">
        <p>{document.metadata.get('date', '')}</p>
    </div>
</div>

<!-- 목차 -->
{toc_html}

{table_toc_html}

{abbreviations_html}

<!-- 본문 -->
{sections_html}

<!-- 각주 -->
{footnotes_html}

<!-- 참고문헌 -->
{references_html}

</body>
</html>"""

        # 저장
        output_path = output_dir / filename
        output_path.write_text(html, encoding="utf-8")
        console.print(f"  HTML: {output_path}")
        return output_path

    # ── 내부 유틸리티 ──

    @staticmethod
    def _parse_title(title: str) -> dict:
        """제목에서 Part/장 정보 추출."""
        result = {"main_title": title, "part": "", "chapter": ""}

        # "제목 - Part A. 기반 인프라 1장 인프라 기술" 형식 파싱
        if " - " in title:
            parts = title.split(" - ", 1)
            result["main_title"] = parts[0].strip()
            rest = parts[1].strip()

            part_match = re.search(r'(Part\s*[A-Z]\.\s*[^\d]+?)(?=\d+장|$)', rest, re.IGNORECASE)
            if part_match:
                result["part"] = part_match.group(1).strip()

            ch_match = re.search(r'(\d+장[\.\s]*.*)', rest)
            if ch_match:
                result["chapter"] = ch_match.group(1).strip()

        return result

    @staticmethod
    def _build_toc(document: Document, table_list: list = None, figure_list: list = None) -> str:
        """목차 HTML 생성."""
        items = []
        for sec in document.sections:
            if sec.html_content:
                items.append(
                    f'        <li><a href="#section-{sec.section_id}">{sec.title}</a></li>'
                )

        appendix_links = []
        if table_list:
            appendix_links.append('<a href="#table-list">표 목차</a>')
        if figure_list:
            appendix_links.append('<a href="#figure-list">그림 목차</a>')
        appendix_links.append('<a href="#references">참고문헌</a>')

        appendix_html = " | ".join(appendix_links)

        return f"""<div class="toc" style="page-break-after: always;">
    <h2>목차</h2>
    <ul style="list-style:none; padding:0;">
{chr(10).join(items)}
    </ul>
    <p style="margin-top:1em; border-top:1px solid #e2e8f0; padding-top:0.8em; font-size:0.9rem;">
        <span style="color:#64748B;">{appendix_html}</span>
    </p>
</div>"""

    @staticmethod
    def _number_tables_figures(html: str) -> tuple[str, list, list]:
        """본문 HTML에서 표/그림에 자동 번호를 부여하고 목록을 수집.

        Returns:
            (수정된 HTML, 표 목록, 그림 목록)
        """
        table_list = []
        figure_list = []
        table_counter = 0
        figure_counter = 0

        # 표 번호 부여: <table 앞에 캡션이 없으면 자동 생성
        def replace_table(match):
            nonlocal table_counter
            table_counter += 1
            table_id = f"table-{table_counter}"
            caption = f"[표 {table_counter}]"
            table_list.append({"id": table_id, "number": table_counter, "caption": caption})
            return f'<div id="{table_id}" class="table-wrapper">\n<p class="table-caption"><strong>{caption}</strong></p>\n{match.group(0)}\n</div>'

        # class가 있는 테이블 (data-table, comparison-matrix)
        html = re.sub(
            r'<table\s+class="(data-table|comparison-matrix)"',
            lambda m: f'<table class="{m.group(1)}" id="table-{len(table_list) + 1}"',
            html
        )

        # figcaption에서 [표 X] 패턴 수집
        for match in re.finditer(r'<(?:p class="table-caption"|figcaption)[^>]*>.*?\[표\s*(\d+)\]([^<]*)', html):
            num = match.group(1)
            caption_text = match.group(2).strip()
            table_list.append({"id": f"table-{num}", "number": int(num), "caption": f"[표 {num}] {caption_text}"})

        # figure/figcaption에서 [그림 X] 패턴 수집
        for match in re.finditer(r'<figcaption[^>]*>.*?\[그림[^\]]*\]\s*([^<]*)', html):
            figure_counter += 1
            caption_text = match.group(1).strip()
            figure_list.append({"id": f"figure-{figure_counter}", "number": figure_counter, "caption": f"[그림 {figure_counter}] {caption_text}"})

        return html, table_list, figure_list

    @staticmethod
    def _build_table_figure_toc(table_list: list, figure_list: list) -> str:
        """표 목차 + 그림 목차 HTML 생성."""
        parts = []

        if table_list:
            items = "\n".join(
                f'        <li><a href="#{t["id"]}" style="color:#1E293B; text-decoration:none;">{t["caption"]}</a></li>'
                for t in table_list
            )
            parts.append(f"""<div id="table-list" style="page-break-after: always;">
    <h2>표 목차</h2>
    <ol style="font-size:0.9rem; line-height:2;">
{items}
    </ol>
</div>""")

        if figure_list:
            items = "\n".join(
                f'        <li><a href="#{f["id"]}" style="color:#1E293B; text-decoration:none;">{f["caption"]}</a></li>'
                for f in figure_list
            )
            parts.append(f"""<div id="figure-list" style="page-break-after: always;">
    <h2>그림 목차</h2>
    <ol style="font-size:0.9rem; line-height:2;">
{items}
    </ol>
</div>""")

        return "\n\n".join(parts)

    @staticmethod
    def _convert_citations(html: str, ref_list) -> tuple[str, list]:
        """[REF-xxx]를 각주 인덱스 <sup>로 변환.

        Returns:
            (변환된 HTML, 각주 목록)
        """
        if not ref_list or not ref_list.references:
            return html, []

        # REF-ID → 인덱스 매핑
        ref_index = {}
        for i, ref in enumerate(ref_list.references, 1):
            ref_index[ref.id] = i

        footnotes = []
        used_indices = set()

        def replace_ref(match):
            ref_id = match.group(1)
            full_id = f"REF-{ref_id}"
            idx = ref_index.get(full_id, 0)
            if idx == 0:
                return match.group(0)  # 매핑 안 되면 그대로

            if idx not in used_indices:
                used_indices.add(idx)
                # 해당 레퍼런스 정보 수집
                ref = next((r for r in ref_list.references if r.id == full_id), None)
                if ref:
                    footnotes.append({
                        "index": idx,
                        "ref_id": full_id,
                        "text": f"{ref.source}, \"{ref.title}\", {ref.year}",
                        "url": ref.url,
                    })

            return f'<sup class="cite-ref"><a href="#fn-{idx}" id="fnref-{idx}">[{idx}]</a></sup>'

        html = re.sub(r'\[REF-(\d+)\]', replace_ref, html)

        # 인덱스 순으로 정렬
        footnotes.sort(key=lambda x: x["index"])

        return html, footnotes

    @staticmethod
    def _build_footnotes(footnotes: list) -> str:
        """각주 섹션 HTML 생성."""
        if not footnotes:
            return ""

        items = []
        for fn in footnotes:
            url_link = f' <a href="{fn["url"]}" target="_blank" style="font-size:0.75rem; color:#2D6A9F;">원본</a>' if fn.get("url") and fn["url"].startswith("http") else ""
            items.append(
                f'        <li id="fn-{fn["index"]}" style="margin-bottom:0.3rem;">'
                f'<a href="#fnref-{fn["index"]}" style="text-decoration:none;">^</a> '
                f'[{fn["ref_id"]}] {fn["text"]}{url_link}</li>'
            )

        return f"""<div class="footnotes" style="border-top:1px solid #E2E8F0; margin-top:2rem; padding-top:1rem;">
    <h3 style="font-size:1rem; color:#64748B;">주석</h3>
    <ol style="font-size:0.8rem; line-height:1.6; color:#64748B;">
{chr(10).join(items)}
    </ol>
</div>"""

    @staticmethod
    def _build_sections(document: Document) -> str:
        """본문 섹션 HTML 생성."""
        parts = []
        for sec in document.sections:
            if sec.html_content:
                parts.append(
                    f'<div class="doc-section" id="section-{sec.section_id}">\n'
                    f'{sec.html_content}\n'
                    f'</div>'
                )
        return "\n\n".join(parts)

    @staticmethod
    def _build_references(document: Document, ref_list: ReferenceList | None = None) -> str:
        """참고문헌 HTML 생성. ReferenceList가 있으면 원본 URL + KeyRef 링크 포함."""

        # ReferenceList가 있으면 풍부한 참고문헌 생성
        if ref_list and ref_list.references:
            items = []
            for ref in ref_list.references:
                # 기본 텍스트
                text = f"[{ref.id}] {ref.source}, 「{ref.title}」, {ref.year}"

                # 신뢰도 배지
                badge_color = {"확인됨": "#059669", "단일출처": "#D97706"}.get(ref.reliability, "#64748B")
                badge = f'<span style="display:inline-block; padding:1px 6px; border-radius:3px; font-size:0.7rem; background:{badge_color}20; color:{badge_color}; font-weight:600; margin-left:4px;">{ref.reliability}</span>'

                # 원본 URL 링크
                url_link = ""
                if ref.url and ref.url.startswith("http"):
                    url_link = f' <a href="{ref.url}" target="_blank" style="font-size:0.75rem; color:#2D6A9F; text-decoration:none;" title="원본 보기">📄 원본</a>'

                # KeyRef 파일 링크
                keyref_link = ""
                if ref.file:
                    keyref_link = f' <a href="{ref.file}" target="_blank" style="font-size:0.75rem; color:#0891B2; text-decoration:none;" title="요약 보기">📋 요약</a>'

                # 핵심 데이터 미리보기
                key_data_preview = ""
                if ref.key_data:
                    previews = [kd.data for kd in ref.key_data[:2]]
                    key_data_preview = f'<br><span style="font-size:0.75rem; color:#64748B; margin-left:2rem;">핵심: {" | ".join(previews)}</span>'

                items.append(
                    f'        <li style="margin-bottom:0.6rem;">'
                    f'{text}{badge}{url_link}{keyref_link}'
                    f'{key_data_preview}'
                    f'</li>'
                )

            items_html = "\n".join(items)
            return f"""<div class="references" id="references" style="border-top:2px solid var(--color-primary,#1B3A5C); margin-top:3rem; padding-top:1.5rem;">
    <h2>참고문헌</h2>
    <p style="font-size:0.8rem; color:#64748B; margin-bottom:1rem;">📄 원본: 출처 원문 링크 | 📋 요약: KeyRef 요약 파일</p>
    <ol style="font-size:0.9rem; line-height:1.6;">
{items_html}
    </ol>
</div>"""

        # ReferenceList 없으면 기존 방식 (단순 텍스트)
        sources = document.metadata.get("sources", [])
        if not sources:
            return ""

        items = "\n".join(f"        <li>{src}</li>" for src in sources)
        return f"""<div class="references" id="references" style="border-top:2px solid var(--color-primary,#1B3A5C); margin-top:3rem; padding-top:1.5rem;">
    <h2>참고문헌</h2>
    <ol style="font-size:0.9rem; line-height:1.8;">
{items}
    </ol>
</div>"""

    @staticmethod
    def _build_abbreviations(document: Document) -> str:
        """약어 목록 HTML 생성."""
        # 본문에서 약어 패턴 추출: "풀네임(약어)" 형식
        all_html = " ".join(sec.html_content or "" for sec in document.sections)
        pattern = r'([가-힣A-Za-z\s]+)\(([A-Z]{2,}[^)]*)\)'
        matches = re.findall(pattern, all_html)

        if not matches:
            return ""

        # 중복 제거
        abbr_dict = {}
        for fullname, abbr in matches:
            abbr = abbr.strip()
            fullname = fullname.strip()
            if abbr not in abbr_dict and len(abbr) <= 15:
                abbr_dict[abbr] = fullname

        if not abbr_dict:
            return ""

        rows = "\n".join(
            f"        <tr><td><strong>{abbr}</strong></td><td>{full}</td></tr>"
            for abbr, full in sorted(abbr_dict.items())
        )

        return f"""<div style="page-break-after: always;">
    <h2>약어 목록</h2>
    <table class="data-table">
        <thead><tr><th>약어</th><th>풀네임</th></tr></thead>
        <tbody>
{rows}
        </tbody>
    </table>
</div>"""

    @staticmethod
    def _resolve_cross_refs(html: str, document: Document) -> str:
        """상호 참조 해소: [→섹션 X.Y] → 실제 링크."""
        def replace_ref(match):
            sec_id = match.group(1)
            return f'<a href="#section-{sec_id}">{sec_id}절</a>'

        return re.sub(r'\[→섹션\s*(\d+(?:\.\d+)*)\]', replace_ref, html)
