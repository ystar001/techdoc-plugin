from techdoc_core.models import Document, DocumentSection
from techdoc_core.renderers.md_export import MarkdownExporter
from techdoc_core.renderers.paragraph import enforce_length, format_paragraphs


def test_keyword_break_inserts_paragraph():
    # "본 " / "한편" / "또한" 등 단락 시작 키워드 앞에서 분리
    text = "앞 문장이다. 한편 새로운 논점이 시작된다."
    out = format_paragraphs(text)
    assert "\n\n" in out


def test_enforce_length_splits_long_paragraph():
    # 800자 ceiling 초과 시 문장 경계에서 분리
    long_para = ("이것은 한 문장이다. " * 60).strip()  # ~700+자
    out = enforce_length(long_para, max_chars=200)
    assert out.count("\n\n") >= 1


def test_already_broken_text_is_idempotent():
    text = "첫 단락.\n\n둘째 단락."
    assert format_paragraphs(format_paragraphs(text)) == format_paragraphs(text)


def test_short_single_paragraph_unchanged():
    assert format_paragraphs("짧은 한 문장.") == "짧은 한 문장."


def test_md_export_applies_paragraph_break(tmp_path):
    # MarkdownExporter.export(document, output_dir, filename, ref_list) -> Path:
    # 파일에 기록하고 경로를 반환한다. tmp_path에 저장 후 읽어 검증한다.
    sec = DocumentSection(
        section_id="1",
        title="섹션",
        html_content="<p>앞 문장이다. 한편 새로운 논점이 길게 이어진다.</p>",
    )
    doc = Document(title="T", sections=[sec])
    out_path = MarkdownExporter().export(doc, tmp_path, filename="document.md")
    md = out_path.read_text(encoding="utf-8")
    # 키워드 '한편' 앞에서 단락 분리(F10)가 적용됨
    assert "한편" in md
    assert "앞 문장이다.\n\n한편" in md
