"""Markdown Exporter - Document -> 편집 가능한 Markdown 파일 생성."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

from techdoc_core.models import Document, ReferenceList
from techdoc_core.renderers.paragraph import format_paragraphs

console = Console()


class MarkdownExporter:
    """Document를 편집 가능한 Markdown 파일로 변환."""

    def export(
        self,
        document: Document,
        output_dir: Path,
        filename: str = "document.md",
        ref_list: ReferenceList | None = None,
    ) -> Path:
        """Document -> Markdown 변환.

        Args:
            document: 완성된 문서
            output_dir: 출력 디렉토리
            filename: 출력 파일명
            ref_list: 레퍼런스 목록 (각주용)

        Returns:
            Path: 생성된 Markdown 파일 경로
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        parts = []

        # 표지
        parts.append(self._build_cover(document))

        # 목차
        parts.append(self._build_toc(document))

        # 본문
        for sec in document.sections:
            if sec.html_content:
                md = self._html_to_markdown(sec.html_content)
                md = format_paragraphs(md)  # F10: 단락 break (키워드+길이 ceiling)
                parts.append(md)
                parts.append("")  # 섹션 구분

        # 참고문헌
        parts.append(self._build_references(ref_list))

        # 저장
        content = "\n\n".join(p for p in parts if p)
        output_path = output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        console.print(f"  MD: {output_path}")
        return output_path

    @staticmethod
    def _build_cover(document: Document) -> str:
        """표지 Markdown."""
        title = document.title
        main_title = title
        part_label = ""
        chapter_label = ""

        if " - " in title:
            main_title, rest = title.split(" - ", 1)
            main_title = main_title.strip()

            import re
            part_match = re.search(r'(Part\s*[A-Z]\.\s*[^\d]+?)(?=\d+장|$)', rest, re.IGNORECASE)
            if part_match:
                part_label = part_match.group(1).strip()
            ch_match = re.search(r'(\d+장[\.\s]*.*)', rest)
            if ch_match:
                chapter_label = ch_match.group(1).strip()

        lines = [f"# {main_title}", ""]
        if part_label:
            lines.append(f"## {part_label}")
        if chapter_label:
            lines.append(f"### {chapter_label}")
        if document.metadata.get("date"):
            lines.append(f"\n*{document.metadata['date']}*")
        lines.append("\n---")
        return "\n".join(lines)

    @staticmethod
    def _build_toc(document: Document) -> str:
        """목차 Markdown."""
        lines = ["## 목차", ""]
        for sec in document.sections:
            if sec.html_content:
                # 들여쓰기: ID에 점이 있으면 하위
                indent = "  " if "." in sec.section_id else ""
                lines.append(f"{indent}- [{sec.title}](#{sec.section_id.replace('.', '')})")
        lines.append("")
        lines.append("---")
        return "\n".join(lines)

    @staticmethod
    def _build_references(ref_list: ReferenceList | None) -> str:
        """참고문헌 Markdown."""
        if not ref_list or not ref_list.references:
            return ""

        lines = ["## 참고문헌", ""]
        for ref in ref_list.references:
            url_part = f" [원본]({ref.url})" if ref.url and ref.url.startswith("http") else ""
            lines.append(f"{ref.id}. {ref.source}, \"{ref.title}\", {ref.year}{url_part}  ")
        return "\n".join(lines)

    def _html_to_markdown(self, html: str) -> str:
        """HTML을 Markdown으로 변환."""
        md = html

        # h2 -> ##
        md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', md, flags=re.DOTALL)
        # h3 -> ###
        md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', md, flags=re.DOTALL)
        # h4 -> ####
        md = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', md, flags=re.DOTALL)

        # strong -> **
        md = re.sub(r'<strong>(.*?)</strong>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<b>(.*?)</b>', r'**\1**', md, flags=re.DOTALL)

        # em -> *
        md = re.sub(r'<em>(.*?)</em>', r'*\1*', md, flags=re.DOTALL)

        # 테이블 변환
        md = self._convert_tables(md)

        # 리스트
        md = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', md, flags=re.DOTALL)
        md = re.sub(r'</?[ou]l[^>]*>', '', md)

        # 인용문
        md = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: "\n> " + m.group(1).strip().replace("\n", "\n> "), md, flags=re.DOTALL)

        # 이미지 (figure)
        md = re.sub(r'<img\s+src="([^"]*)"[^>]*>', r'![](\1)', md)
        md = re.sub(r'<figcaption[^>]*>(.*?)</figcaption>', r'*\1*', md, flags=re.DOTALL)

        # sup (각주)
        md = re.sub(r'<sup[^>]*>\s*<a[^>]*>\[(\d+)\]</a>\s*</sup>', r'[\1]', md)

        # div 컴포넌트 -> 인용 블록으로 변환
        # callout
        md = re.sub(r'<div class="callout[^"]*">(.*?)</div>', lambda m: "\n> " + re.sub(r'<[^>]+>', '', m.group(1)).strip().replace("\n", "\n> ") + "\n", md, flags=re.DOTALL)

        # section-summary
        md = re.sub(r'<div class="section-summary[^"]*">(.*?)</div>', lambda m: "\n> **섹션 요약**\n> " + re.sub(r'<[^>]+>', '', m.group(1)).strip().replace("\n", "\n> ") + "\n", md, flags=re.DOTALL)

        # key-point
        md = re.sub(r'<div class="key-point[^"]*">(.*?)</div>', lambda m: "\n> **핵심 포인트**\n> " + re.sub(r'<[^>]+>', '', m.group(1)).strip().replace("\n", "\n> ") + "\n", md, flags=re.DOTALL)

        # insight-box
        md = re.sub(r'<div class="insight-box[^"]*">(.*?)</div>', lambda m: "\n> **인사이트**\n> " + re.sub(r'<[^>]+>', '', m.group(1)).strip().replace("\n", "\n> ") + "\n", md, flags=re.DOTALL)

        # stat-highlight -> 굵은 텍스트
        md = re.sub(r'<div class="stat-value">(.*?)</div>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<div class="stat-label">(.*?)</div>', r'\1', md, flags=re.DOTALL)

        # p 태그
        md = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', md, flags=re.DOTALL)

        # 나머지 태그 제거
        md = re.sub(r'</?div[^>]*>', '', md)
        md = re.sub(r'</?span[^>]*>', '', md)
        md = re.sub(r'</?a[^>]*>', '', md)
        md = re.sub(r'</?figure[^>]*>', '', md)
        md = re.sub(r'<br\s*/?>', '\n', md)

        # 남은 태그 제거
        md = re.sub(r'<[^>]+>', '', md)

        # 빈 줄 정리
        md = re.sub(r'\n{3,}', '\n\n', md)
        md = md.strip()

        return md

    @staticmethod
    def _convert_tables(html: str) -> str:
        """HTML 테이블을 Markdown 테이블로 변환."""
        def table_to_md(match):
            table_html = match.group(0)

            # 헤더 추출
            headers = re.findall(r'<th[^>]*>(.*?)</th>', table_html, re.DOTALL)
            headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]

            # 행 추출
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            data_rows = []
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if cells:
                    cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    data_rows.append(cells)

            if not headers and not data_rows:
                return ""

            lines = []
            if headers:
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

            for row in data_rows:
                # 컬럼 수 맞추기
                while len(row) < len(headers):
                    row.append("")
                lines.append("| " + " | ".join(row[:len(headers)] if headers else row) + " |")

            return "\n" + "\n".join(lines) + "\n"

        return re.sub(r'<table[^>]*>.*?</table>', table_to_md, html, flags=re.DOTALL)
