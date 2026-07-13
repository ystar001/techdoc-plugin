"""KeyRefSchema 제약 완화 테스트 (v1.9.0 워크스트림 G — F33·F35·F46)."""
import pytest
from pydantic import ValidationError

from techdoc_core.schemas import KeyRefSchema


def _base_ref(**over):
    d = dict(
        id="REF-001",
        category="학술",
        source="s",
        year=2020,
        title="t",
        reliability="확인됨",
    )
    d.update(over)
    return d


def test_keyref_accepts_four_digit_id():
    """F35 — 4자리 이상 REF id 허용 (REF-1000+)."""
    ref = KeyRefSchema(**_base_ref(id="REF-1000"))
    assert ref.id == "REF-1000"


def test_keyref_still_rejects_two_digit_id():
    """F35 — 3자리 미만은 여전히 거부 (완화가 과하지 않도록)."""
    with pytest.raises(ValidationError):
        KeyRefSchema(**_base_ref(id="REF-12"))


def test_keyref_accepts_pre_1990_classic():
    """F33 — 1990 이전 고전 문헌 허용 (농학·표준 도메인)."""
    ref = KeyRefSchema(**_base_ref(year=1965))
    assert ref.year == 1965


def test_keyref_accepts_category_etc():
    """F46 — category enum에 '기타' 추가."""
    ref = KeyRefSchema(**_base_ref(category="기타"))
    assert ref.category == "기타"


def test_document_style_accepts_mixed():
    """F24 — style에 '혼합형'(서술+개조 혼용) 허용."""
    from techdoc_core.schemas import DocumentMetaSchema

    meta = DocumentMetaSchema(title="t", style="혼합형")
    assert meta.style == "혼합형"


def test_document_style_existing_values_unchanged():
    """회귀 — 기존 서술형·개조식 유지."""
    from techdoc_core.schemas import DocumentMetaSchema

    assert DocumentMetaSchema(title="t", style="서술형").style == "서술형"
    assert DocumentMetaSchema(title="t", style="개조식").style == "개조식"
