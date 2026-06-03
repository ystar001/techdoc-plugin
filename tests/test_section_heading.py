from techdoc_core.renderers.section_heading import section_key_to_heading


def test_canonical_sec_keys_map_to_korean():
    assert section_key_to_heading("sec1") == "정의·범위"
    assert section_key_to_heading("sec6") == "전망"


def test_legacy_descriptive_key_falls_back_to_position():
    # sec3_trends_international 같은 구 키도 위치(sec3)로 매핑
    assert section_key_to_heading("sec3_trends_international") == "국내외 동향"


def test_unknown_key_uses_fallback_title():
    assert section_key_to_heading("misc", fallback="기타 절") == "기타 절"
    assert section_key_to_heading("misc") == "misc"
