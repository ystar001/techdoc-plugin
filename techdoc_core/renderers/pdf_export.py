"""PDF Exporter — HTML → PDF 변환."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()


class PDFExporter:
    """HTML 파일을 PDF로 변환."""

    def export(self, html_path: Path, output_dir: Path, filename: str = "document.pdf") -> Path | None:
        """HTML → PDF 변환.

        playwright 또는 weasyprint 사용. 미설치 시 건너뜀.
        """
        output_path = output_dir / filename

        # 방법 1: playwright
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f"file:///{html_path.resolve()}")
                page.pdf(
                    path=str(output_path),
                    format="A4",
                    margin={"top": "25mm", "bottom": "25mm", "left": "25mm", "right": "20mm"},
                    print_background=True,
                )
                browser.close()
            console.print(f"  PDF: {output_path}")
            return output_path
        except ImportError:
            pass
        except Exception as e:
            console.print(f"  [yellow]playwright PDF 실패: {str(e)[:50]}[/yellow]")

        # 방법 2: weasyprint
        try:
            from weasyprint import HTML
            HTML(filename=str(html_path)).write_pdf(str(output_path))
            console.print(f"  PDF: {output_path}")
            return output_path
        except ImportError:
            pass
        except Exception as e:
            console.print(f"  [yellow]weasyprint PDF 실패: {str(e)[:50]}[/yellow]")

        console.print("  [dim]PDF 변환 건너뜀 (playwright 또는 weasyprint 필요)[/dim]")
        return None
