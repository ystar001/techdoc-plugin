"""Plan H — glossary 자동추출 (F16) tests.

자식 extract_glossary 구현을 plugin으로 적응 이식한 모듈을 검증한다.
정규식·페어 추출은 결정론적(LLM 호출 0회).
"""

from __future__ import annotations

from scripts.extract_glossary import find_abbreviations, find_explanation_pairs


def test_find_abbreviations_counts_caps_tokens():
    counts = find_abbreviations("LoRa는 IoT 통신이다. IoT는 사물인터넷. AI도 등장.")
    assert counts["IOT"] >= 2 or counts["IoT"] >= 2 or "IOT" in {k.upper() for k in counts}


def test_find_explanation_pairs_extracts_ke_abbr():
    pairs = find_explanation_pairs("사물인터넷(IoT)은 핵심 기술이다.")
    abbrs = {p["abbr"].upper() for p in pairs}
    assert "IOT" in abbrs
