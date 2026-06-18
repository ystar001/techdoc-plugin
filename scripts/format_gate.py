"""서식 게이트 — self_model 카드 본문 markdown 형식 품질 측정 (LLM 0회·결정론적).

verify_rewrite.py(openfieldtech) 게이트 로직 이식. 스키마 무지: 추출된 텍스트만 받는다.
전부 WARNING 기본, ``strict`` 시 "렌더가 깨지는 구조 결함 + REF 회귀"만 FAIL로 승격.
``markdown`` 모듈은 optional(미설치 시 render_nesting만 생략).
"""

from __future__ import annotations

import re

REF_RE = re.compile(r"REF-\d{3,4}")
NUM_RE = re.compile(r"\d[\d,.]*")
INLINE_ROMAN = re.compile(r"\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)")
INLINE_ALPHA = re.compile(r"\([a-z]-\d\)")
TOP_PLAIN = re.compile(r"(?:^|[\s.])\([a-h]\)\s")
LIST_LINE = re.compile(r"^( *)([-*]|\d+\.)\s")
NONBULLET_INDENT = re.compile(r"^ {2,3}(?![-*] |\d+\. )\S", re.M)
REDUNDANT_SUMMARY = re.compile(r"종합하면|정리하면|종합적으로")

# --strict 에서 FAIL로 승격되는 "렌더가 깨지는 구조 결함 + REF 회귀"
STRICT_FAIL_METRICS = {
    "inline_hierarchy",
    "top_plain_label",
    "nonbullet_indent",
    "flatten_risk_indent",
    "ref_loss",
}


def analyze_lists(text: str) -> tuple[int, int]:
    """리스트 줄 들여쓰기 분석 → (4배수 중첩 수, 4배수 아님=평탄화 위험 수)."""
    indent4 = bad = 0
    for line in text.split("\n"):
        m = LIST_LINE.match(line)
        if not m:
            continue
        n = len(m.group(1))
        if n == 0:
            continue
        if n % 4 == 0:
            indent4 += 1
        else:
            bad += 1
    return indent4, bad


def count_nonbullet_indent(text: str) -> int:
    """불릿 아닌 2·3칸 들여쓰기 텍스트 줄 수 (설명을 리스트에 욱여넣은 흔적)."""
    return len(NONBULLET_INDENT.findall(text))


def count_inline_hierarchy(text: str) -> int:
    """인라인 계층번호 (i)(ii)/(a-1) 등장 수."""
    return len(INLINE_ROMAN.findall(text)) + len(INLINE_ALPHA.findall(text))


def count_top_plain(text: str) -> int:
    """상위 평문 분류 라벨 (a)(b)(c) 등장 수 (줄머리/마침표 뒤)."""
    return len(TOP_PLAIN.findall(text))


def count_redundant_summary(text: str) -> int:
    """중복 요약 단락 신호어(종합하면/정리하면/종합적으로) 등장 수."""
    return len(REDUNDANT_SUMMARY.findall(text))


def list_ratio_by_section(sections: dict[str, str]) -> dict[str, int]:
    """섹션별 불릿 줄 비율이 50% 초과인 섹션만 {키: 퍼센트(정수)}."""
    out: dict[str, int] = {}
    for k, v in sections.items():
        lines = [ln for ln in v.split("\n") if ln.strip()]
        bullets = [ln for ln in lines if re.match(r"^ *[-*] ", ln)]
        if lines and len(bullets) / len(lines) > 0.5:
            out[k] = len(bullets) * 100 // len(lines)
    return out


def refs(text: str) -> set[str]:
    """본문 내 REF-xxx 식별자 집합."""
    return set(REF_RE.findall(text))


def nums(text: str) -> set[str]:
    """숫자 토큰 집합(콤마·소수점 포함). REF 번호는 제외."""
    return set(NUM_RE.findall(REF_RE.sub("", text)))


def render_nesting(sections: dict[str, str]) -> dict[str, int] | None:
    """python-markdown(sane_lists)로 섹션별 중첩 <ul> 수. markdown 미설치 시 None."""
    try:
        import markdown
    except ImportError:
        return None
    out: dict[str, int] = {}
    for k, v in sections.items():
        html = markdown.markdown(v, extensions=["sane_lists", "tables"])
        out[k] = len(re.findall(r"<li>(?:(?!</li>).)*?<ul>", html, re.S))
    return out


def measure_format(
    sections: dict[str, str],
    baseline: dict[str, str] | None = None,
    strict: bool = False,
    tolerance: float = 0.15,
) -> dict:
    """서식 지표 측정 + issue 목록 생성. 전부 WARNING 기본, strict 시 구조 결함 FAIL."""
    alltext = "\n".join(sections.values())
    metrics: dict = {}
    issues: list[dict] = []

    def sev(metric: str) -> str:
        return "FAIL" if (strict and metric in STRICT_FAIL_METRICS) else "WARNING"

    def emit(metric: str, msg: str) -> None:
        issues.append({"severity": sev(metric), "metric": metric, "msg": msg})

    inline = count_inline_hierarchy(alltext)
    metrics["inline_hierarchy"] = inline
    if inline:
        emit("inline_hierarchy", f"인라인 계층번호 (i)(ii)/(a-1) {inline}건 — 중첩 md 리스트로")

    top = count_top_plain(alltext)
    metrics["top_plain_label"] = top
    if top:
        emit("top_plain_label", f"상위 평문 라벨 (a)(b)(c) {top}건 — 리스트/표로")

    nb = count_nonbullet_indent(alltext)
    metrics["nonbullet_indent"] = nb
    if nb:
        emit("nonbullet_indent", f"비-불릿 2·3칸 들여쓰기 텍스트 {nb}건 — 논문형 서술로")

    _indent4, bad = analyze_lists(alltext)
    metrics["flatten_risk_indent"] = bad
    if bad:
        emit("flatten_risk_indent", f"4배수 아닌 들여쓰기(평탄화 위험) {bad}건 — 2·3칸→4칸")

    ratio = list_ratio_by_section(sections)
    metrics["high_list_ratio"] = ratio
    if ratio:
        emit(
            "high_list_ratio",
            "리스트 비율 과다: " + ", ".join(f"{k}={v}%" for k, v in ratio.items())
            + " (설명형이면 서술로)",
        )

    redundant = count_redundant_summary(alltext)
    metrics["redundant_summary"] = redundant
    if redundant:
        emit(
            "redundant_summary",
            f"중복 요약 단락(종합하면/정리하면) {redundant}건 — 위 설명 반복이면 삭제",
        )

    metrics["render_nesting"] = render_nesting(sections)

    # baseline 회귀 (미제공 시 None)
    metrics["ref_loss"] = None
    metrics["num_token_loss"] = None
    metrics["length_delta"] = None
    if baseline is not None:
        basetext = "\n".join(baseline.values())
        lost = refs(basetext) - refs(alltext)
        metrics["ref_loss"] = len(lost)
        if lost:
            emit("ref_loss", f"REF 손실 {len(lost)}: {sorted(lost)}")
        num_lost = nums(basetext) - nums(alltext)
        metrics["num_token_loss"] = len(num_lost)
        if num_lost:
            emit("num_token_loss", f"수치 토큰 {len(num_lost)}개 baseline에만 존재(확인)")
        bl, cl = len(basetext), len(alltext)
        if bl:
            delta = (cl - bl) / bl
            metrics["length_delta"] = round(delta, 3)
            if abs(delta) > tolerance:
                emit(
                    "length_delta",
                    f"분량 {bl}->{cl} ({delta * 100:+.1f}% > ±{tolerance * 100:.0f}%)",
                )

    return {"metrics": metrics, "issues": issues}
