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
