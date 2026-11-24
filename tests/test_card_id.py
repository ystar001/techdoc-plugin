"""카드 ID 파서 — 구분자 분해 후 역할 추론 (v1.10.2 — F58·F70·F73·F79·F81)."""
import pytest

from techdoc_core.card_id import parse_card_id_parts, size_id


@pytest.mark.parametrize("stem,kind,size", [
    ("1.1_card", "body", "S"), ("1.1.L2", "body", "L2"), ("0.3", "front", "P0"),
    ("1.1.1", "body", "S"),
    ("A-14.1", "appendix", "S"), ("G-1", "appendix", "S"),
    ("D-2.XL3", "appendix", "XL3"), ("E-1", "appendix", "S"),
    ("J-4", "appendix", "S"), ("H-2.L1", "appendix", "L1"),
    ("C3.XL2", "appendix", "XL2"),
    ("2.A.7", "body", "S"), ("2.A.7.L1", "body", "L1"),
    ("1.1.S", "body", "S"),
    ("부록-가", "unknown", "?"),
])
def test_parse_and_size(stem, kind, size):
    cid = parse_card_id_parts(stem)
    assert cid.kind == kind
    assert size_id(cid) == size
