"""시각화 밀도 + 열거 strict 승격 테스트 (v1.9.0 — F50·F49)."""
from scripts.format_gate import count_visual_elements, measure_format


def test_count_visual_elements_counts_table_mermaid_image():
    """F50 — 본문의 표·mermaid·이미지를 시각 요소로 계수."""
    text = (
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "```mermaid\ngraph TD\nA-->B\n```\n\n"
        "![그림 1](img.png)\n"
    )
    assert count_visual_elements(text) == 3


def test_count_visual_elements_zero_for_plain_text():
    """F50 — 표·그림 없는 산문은 0."""
    assert count_visual_elements("그냥 문단입니다. 표도 그림도 mermaid도 없습니다.") == 0


def test_visual_density_warns_on_long_sparse_body():
    """F50 — 긴 본문(≥3000자)에 시각 요소가 희소하면 WARNING."""
    res = measure_format({"s1": "가나다라마바사아자차" * 500})  # 5000자, 시각요소 0
    vd = [i for i in res["issues"] if i["metric"] == "visual_density"]
    assert vd and vd[0]["severity"] == "WARNING"


def test_visual_density_ok_when_rich():
    """F50 — 시각 요소가 충분하면 경고 없음."""
    body = ("| a | b |\n|---|---|\n| 1 | 2 |\n\n" + "가나다라마 " * 100)
    res = measure_format({"s1": body})
    vd = [i for i in res["issues"] if i["metric"] == "visual_density"]
    assert not vd


def test_inline_enumeration_promoted_to_fail_under_strict():
    """F49 — 인라인 병렬 열거가 strict 모드에서 FAIL로 승격."""
    text = "핵심은 세 가지다. 첫째, 정확성이다. 둘째, 재현성이다. 셋째, 견고성이다."
    res = measure_format({"s1": text}, strict=True)
    enum = [i for i in res["issues"] if i["metric"] == "inline_enumeration"]
    assert enum and enum[0]["severity"] == "FAIL"
