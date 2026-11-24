"""용어·표기·기타 게이트 — V22·V37·V42·V46·V47·V48·V49·V51·V64·V7·V14 (v1.11-b, F85).

시리즈 check_v2(카드 게이트 V22·V7·V14)와 prose_gates(산문 게이트 나머지)에서 판정 로직을 그대로
옮기고 입력만 DocModel로 바꿨다. 산문 게이트의 입력은 `model.prose()`(draft가 있으면 draft, 없으면
렌더 트리). V48의 수식 판정은 `techdoc_core.qc.math_hangul`(원본 math_hangul.py를 옮김)이 맡는다.

- **시리즈 고유 값은 설정으로**(E17): V64를 켜는 규약 문장(원본 「장마다 처음 나오는 곳에서」)은
  `extra.terms.abbr_rule_sentence`(정규식 조각). 플러그인 기본은 없음 — 규약 문장을 선언한 문서만
  검사한다(원본도 규약 문장이 없는 편은 켜지 않았다).
- **이미지 라이선스 대장**(V7): `paths.image_license`(기본 `output/assets/images/LICENSE.tsv`).
  원본처럼 대장이 없으면 이미지마다 1건. 원본은 면제를 적용하지 않았다(`exemptable: false`).
- **번호 꼴**: V64의 장 안 파일 차례는 roman이면 로마 숫자 마디를 값으로 정렬한다(arabic은 원본 그대로).
"""
from __future__ import annotations

import re
from pathlib import Path

from techdoc_core.qc import math_hangul
from techdoc_core.qc.card_text import card_texts, sections_of
from techdoc_core.qc.gates.structure import goal_questions, is_goal_form
from techdoc_core.qc.model import DocModel
from techdoc_core.qc.prose import is_cap_line
from techdoc_core.qc.registry import Finding, GateOutput, Sample, gate, sample_model

PROSE_SKIP = re.compile(r"^\s*(?:\||```)")


def _style(model: DocModel) -> str:
    return (model.numbering or {}).get("section") or "arabic"


def _texts(model: DocModel) -> dict[str, str]:
    """산문 게이트 입력(원본 prose_gates.run의 texts)."""
    return {tf.rel: tf.text for tf in model.prose()}


def _card(body: str, title: str = "", **extra) -> dict:
    return {"sections": {"s1": {"title": title, "body": body}}, **extra}


def _outside_fence(text: str):
    """(0부터 줄 번호, 줄) — 코드 펜스 밖 줄만(펜스 여닫는 줄도 뺌)."""
    infence = False
    for i, line in enumerate(text.split("\n")):
        if line.lstrip().startswith("```"):
            infence = not infence
            continue
        if not infence:
            yield i, line


# ═══ V22 콜아웃 본문의 들여쓰기 (check_v2 638 · 722-740 · 1139-1141) ═══
# python-markdown의 admonition은 본문을 4칸 들여쓰기로 잡는다. 1~3칸이면 본문이 상자에서 떨어져
# 「빈 제목 상자 + 그 아래 맨 문단」으로 렌더된다.

CALLOUT = re.compile(r"^(\s*)!!!\s+\S+", re.M)


def callout_errors(body: str) -> list[str]:
    out: list[str] = []
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if not CALLOUT.match(ln):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines):
            out.append(f"본문 없음: {ln.strip()[:40]}")
            continue
        nxt = lines[j]
        indent = len(nxt) - len(nxt.lstrip(" "))
        if 0 < indent < 4:
            out.append(f"본문 들여쓰기 {indent}칸(4칸이어야 한다): {ln.strip()[:34]}")
        elif indent == 0:
            out.append(f"본문이 상자 밖: {ln.strip()[:40]}")
    return out


@gate("V22", samples=[
    Sample(sample_model(cards={"1.1": _card('!!! note "가"\n  두 칸 본문이다.')}), expect=1),
    Sample(sample_model(cards={"1.1": _card('!!! note "가"\n\n    네 칸 본문이다.')}), expect=0),
])
def v22_callout_indent(model: DocModel) -> GateOutput:
    """콜아웃(!!!) 본문이 4칸 들여쓰기가 아니어서 상자 밖으로 떨어짐·본문 없음."""
    out: list[Finding] = []
    seen = 0
    for cid, key, _title, body in model.card_items():
        seen += sum(1 for ln in body.split("\n") if CALLOUT.match(ln))
        for e in callout_errors(body):
            out.append(Finding(f"{cid}|{key}: 콜아웃", f"{cid}·{key} {e}"))
    return GateOutput(seen, out)


# ═══ V37 수식 손상 (prose_gates 166-169 · 807-810) ═══
# 정규식 치환의 역참조(`\1`)가 LaTeX 명령을 덮어쓴 흔적. `$$` 줄·펜스 안도 보려고 원문 전체를 본다.

MATH_BROKEN = re.compile(r"\$[^$\n]*\\[1-9](?![0-9])[^$\n]*\$")


@gate("V37", samples=[
    Sample(sample_model(tree={"a.md": "$$\\1 = f\\1(Y)$$\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "$\\pi = f(Y)$\n"}), expect=0),
])
def v37_math_broken(model: DocModel) -> GateOutput:
    """수식 손상 — $…$ 안에 정규식 역참조 흔적(\\1~\\9)."""
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for m in MATH_BROKEN.finditer(text):
            ln = text.count("\n", 0, m.start()) + 1
            out.append(Finding(f"{name}:{ln}", f"역참조 흔적 — {m.group(0)[:50]}"))
    return GateOutput(len(texts), out)


# ═══ V42 사적 기호 (prose_gates 288 · 844-853) ═══
# 본문 산문(표·펜스 밖)의 【분기】 꼴 꺾쇠 태그·★·⚠. 표 칸의 ★ 등급은 범례가 있으면 허용.

PRIVATE_MARK = re.compile(r"【[^】\n]{1,12}】|★|⚠")


@gate("V42", samples=[
    Sample(sample_model(tree={"a.md": "★ 눈에 띄는 값\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "| 중요도 | ★★ |\n"}), expect=0),
])
def v42_private_mark(model: DocModel) -> GateOutput:
    """사적 기호 — 본문 산문의 【분기】 꼴 꺾쇠 태그·★·⚠."""
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for i, line in _outside_fence(text):
            if PROSE_SKIP.match(line):
                continue
            for m in PRIVATE_MARK.finditer(line):
                out.append(Finding(f"{name}:{i + 1}",
                                   f"사적 기호 {m.group(0)} — 말로 풀거나 주의 상자로"))
    return GateOutput(len(texts), out)


# ═══ V46·V47 글꼴 한 벌 · V49 통화 $ · V51 저작 도구 표시 (prose_gates 299-308 · 869-880) ═══
# 펜스 밖 모든 줄(표 칸 포함)을 본다 — 원본 V45와 같은 줄 순회.

INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
ITAL_KO = re.compile(r"(?<![*\w\\])\*(?!\s)([^*\n]*[가-힣][^*\n]*?)(?<!\s)\*(?![*\w])")
CURRENCY_BARE = re.compile(r"(?<!\\)(?:(?<=US)\$(?![\d{\\])|\$(?=/))")
AUTHOR_TAG = re.compile(r"\[분석:\s[^\]]*\]")


def _line_gate(model: DocModel, scan) -> GateOutput:
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for i, line in _outside_fence(text):
            for msg in scan(line):
                out.append(Finding(f"{name}:{i + 1}", msg))
    return GateOutput(len(texts), out)


@gate("V46", samples=[
    Sample(sample_model(tree={"a.md": "값은 `미판정`이다\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "필드 `measured` 와 `quality_flag`\n"}), expect=0),
])
def v46_hangul_inline_code(model: DocModel) -> GateOutput:
    """한글이 든 인라인 코드(`…`) — 본문 글꼴을 깸."""
    return _line_gate(model, lambda line: [
        f"한글이 든 인라인 코드 — {m.group(0)[:30]}"
        for m in INLINE_CODE.finditer(line) if re.search(r"[가-힣]", m.group(1))])


@gate("V47", samples=[
    Sample(sample_model(tree={"a.md": "*기울인 말*\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "*Pseudomonas syringae*\n"}), expect=0),
])
def v47_hangul_italic(model: DocModel) -> GateOutput:
    """한글 기울임(*…*) — 한글 글꼴엔 기울임체가 없어 가짜 기울임."""
    return _line_gate(model, lambda line: [
        f"한글 기울임 — {m.group(0)[:30]}" for m in ITAL_KO.finditer(line)])


@gate("V49", samples=[
    Sample(sample_model(tree={"a.md": "약 22억 US$는\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "US\\$로\n"}), expect=0),
])
def v49_currency_bare(model: DocModel) -> GateOutput:
    """이스케이프 안 된 통화 $ — 「US$는」·「$/m³」를 MathJax가 수식으로 짝짓는다(인라인 코드 밖)."""
    return _line_gate(model, lambda line: [
        f"이스케이프 안 된 통화 $ — {m.group(0)} (\\$ 로)"
        for m in CURRENCY_BARE.finditer(INLINE_CODE.sub("", line))])


@gate("V51", samples=[
    Sample(sample_model(tree={"a.md": "[분석: 비교분석] 농업 FL\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "[REF-1] 분석: 비교\n"}), expect=0),
])
def v51_author_tag(model: DocModel) -> GateOutput:
    """저작 도구 표시 — 「[분석: 비교분석]」 태그가 본문에 남음."""
    return _line_gate(model, lambda line: [
        f"저작 도구 표시 — {m.group(0)}" for m in AUTHOR_TAG.finditer(line)])


# ═══ V48 수식 안 한글 (prose_gates 884-892 + math_hangul.py) ═══

@gate("V48", samples=[
    Sample(sample_model(tree={"a.md": "$$영농 = a + b$$\n"}), expect=1),
    Sample(sample_model(tree={"a.md": "$$ET_c = K_c \\quad \\text{(작물 증발산)}$$\n"}), expect=0),
])
def v48_math_hangul(model: DocModel) -> GateOutput:
    """수식 안 한글 — 첨자·묶음 설명 안(작아짐), \\text{} 밖 맨 한글(명조로 떨어짐)."""
    texts = _texts(model)
    out: list[Finding] = []
    for name, text in texts.items():
        for ln, kind, frag in math_hangul.scan_md(text):
            why = "첨자·묶음 설명 안(0.707배로 작아짐)" if kind == "작은" else "\\text 밖(명조로 떨어짐)"
            out.append(Finding(f"{name}:{ln}", f"수식 안 한글 {why} — {frag[:20]}"))
    return GateOutput(len(texts), out)


# ═══ V64 약어의 장 첫 등장 풀이 (prose_gates 1053 · 1059-1163) ═══

ABBR_ROW = re.compile(r"^\|[^|]*\|\s*([^|]+?)\s*\|")
# 화학식(NO₃⁻·NH₄⁺·CO₂)은 약어가 아니다 — 아래·위 첨자 숫자·전하가 바로 붙으면 뺀다
ABBR_TOKEN = re.compile(r"(?<![A-Za-z0-9\-])([A-Z][A-Za-z0-9\-]*[A-Z][A-Za-z0-9\-]*)"
                        r"(?![A-Za-z0-9₀-₉⁰-⁹²³¹⁺⁻])")
# 인용 괄호·코드·주소·링크·수식($…$)·인용한 항 이름(「…」)은 풀지 않는다
ABBR_MASK = re.compile(r"\[REF-[^\]]*\]|`[^`]*`|https?://\S+|\]\([^)]*\)|\$[^$\n]+\$|「[^」\n]*」")


def _open_paren(before: str):
    depth, start = 0, None
    for i, c in enumerate(before):
        if c == "(":
            depth += 1
            if depth == 1:
                start = i
        elif c == ")" and depth:
            depth -= 1
    return before[start + 1:] if depth else None


def abbr_expanded(line: str, a: int, b: int) -> bool:
    """「풀이(ABBR」·「ABBR(풀이」·「(풀이, ABBR」 꼴이면 풀린 것이다."""
    before, after = line[:a], line[b:]
    # 「센서(IoT·드론)」은 풀이가 아니라 나열이다 — 약어가 괄호를 홀로 채울 때만(뒤에 `)`·`,`)
    if (re.search(r"[가-힣A-Za-z][^()\n]{0,40}\((?:[A-Z][A-Za-z0-9\-]*\s+)?$", before)
            and re.match(r"(?:\s+[A-Z][A-Za-z0-9\-]*)?\s*[),]", after)):
        return True
    inside = _open_paren(before)
    if inside is not None and re.search(r"[가-힣]", inside):
        return True
    # 「변량처리(Variable Rate Technology, VRT)」 — 우리말 풀이(영문 원어, 약어) 꼴
    if (inside is not None and re.search(r"[A-Za-z][A-Za-z \-/]+,\s*$", inside)
            and re.search(r"[가-힣]\s*\($", before[:len(before) - len(inside)])):
        return True
    return bool(re.match(r"\s*\((?!REF)[^)]{2,}", after))


def _abbr_chapter(key: str) -> str:
    """장 = 경로 2단(트리 「부/장/절.md」), 2단 트리는 첫 단, 평평한 원고는 파일 하나."""
    parts = key.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0] if len(parts) > 1 else key


_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _roman_value(s: str) -> int:
    total = 0
    for i, ch in enumerate(s):
        v = _ROMAN[ch]
        total += -v if i + 1 < len(s) and _ROMAN[s[i + 1]] > v else v
    return total


def _nat(k: str, style: str = "arabic"):
    """「5.10」이 「5.2」 뒤에 오게 — 글자 순이면 첫 등장이 바뀐다. roman은 「V.1」이 「IX.1」 앞."""
    if style == "roman":
        toks = re.split(r"(\d+|(?<![A-Za-z])[IVXLC]+(?=\.))", k)
        return [(0, int(x), "") if x.isdigit()
                else (0, _roman_value(x), "") if x and re.fullmatch(r"[IVXLC]+", x)
                and i % 2 == 1 else (1, 0, x) for i, x in enumerate(toks)]
    return [(0, int(x), "") if x.isdigit() else (1, 0, x) for x in re.split(r"(\d+)", k)]


def _abbr_rule(model: DocModel) -> re.Pattern | None:
    pat = ((model.extra or {}).get("terms") or {}).get("abbr_rule_sentence")
    return re.compile(pat) if pat else None


def abbr_first_use(texts: dict[str, str], rule: re.Pattern | None,
                   style: str = "arabic") -> tuple[int, list[tuple[str, str]]]:
    """(검사한 파일 수, [(위치, 메시지)]). 규약 문장이 있는 파일이 없으면 (0, [])."""
    out: list[tuple[str, str]] = []
    # 규약 문장이 있는 앞부분 파일의 표 — 편마다 약어표 꼴이 달라 표의 모든 칸에서 약어를 모은다
    table_key = next((k for k, t in texts.items() if rule.search(t)), None) if rule else None
    if not table_key:
        return 0, out
    abbrs: set[str] = set()
    for line in texts[table_key].split("\n"):
        if line.strip().startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", line.strip()):
            for cell in line.strip().strip("|").split("|"):
                cell = re.sub(r"\([^)]*\)", "", cell)  # 괄호 속 원어(영문 풀이)는 약어가 아니다
                if not re.search(r"[가-힣]", cell):  # 약어 칸만 — 풀이 칸의 단체·제품 이름은 빼고
                    # 대문자가 절반 넘는 것만 — 인명(Penman-Monteith)·인용 번호(REF-212)는 약어가 아니다
                    for t in ABBR_TOKEN.findall(cell):
                        lt = [c for c in t if c.isalpha()]
                        if not t.startswith("REF-") and lt and sum(c.isupper() for c in lt) / len(lt) > 0.5:
                            abbrs.add(t)
    abbrs.discard("ISO")  # 표준 번호(ISO 11783)와 이름이 겹쳐 첫 등장을 가를 수 없다
    chapters: dict[str, list[str]] = {}
    for k in texts:
        if k == table_key or k.endswith("INDEX.md"):  # 목차는 본문이 아니다
            continue
        chapters.setdefault(_abbr_chapter(k), []).append(k)
    seen_files = 0
    for keys in chapters.values():
        keys = sorted(keys, key=lambda k: _nat(k, style))
        seen_files += len(keys)
        notes = "\n".join(ln for k in keys for ln in texts[k].split("\n") if ln.startswith("주: "))
        seen: set[str] = set()
        for k in keys:
            fence = False
            for n, line in enumerate(texts[k].split("\n"), 1):
                st = line.strip()
                if st.startswith("```"):
                    fence = not fence
                    continue
                # 요약 상자(<div …>)·수식 줄은 본문 산문이 아니다
                if (fence or not st or st.startswith(("#", "!!! ", "주: ", ">", "<", "$$"))
                        or re.match(r"\*\*(표|그림|차트)\s", st) or is_cap_line(st, style)):
                    continue
                masked = ABBR_MASK.sub(lambda m: "\x00" * len(m.group(0)), line)
                for m in ABBR_TOKEN.finditer(masked):
                    t = m.group(1)
                    if t not in abbrs or t in seen:
                        continue
                    # 출처 표기 괄호 「REF-016(USDA ERS, …)」는 서지라 풀이 대상이 아니다
                    b = line[:m.start()]
                    p = b.rfind("(")
                    if _open_paren(b) is not None and re.search(r"REF-\d+$", b[:p]):
                        continue
                    seen.add(t)
                    if abbr_expanded(line, m.start(), m.end()):
                        continue
                    # 그 장의 「주:」 줄이 풀었으면 된다
                    if re.search(rf"(?<![A-Za-z]){re.escape(t)}(?:\([^)\n]*\))?(?: —|:)", notes):
                        continue
                    where = "(표·괄호 → 주:)" if st.startswith("|") or _open_paren(b) is not None else ""
                    out.append((f"{k}:{n}",
                                f"약어 장 첫 등장 풀이 없음{' ' + where if where else ''} {t}"))
    return seen_files, out


_V64_SAMPLE_EXTRA = {"terms": {"abbr_rule_sentence": "장마다 처음 나오는 곳에서"}}


@gate("V64", samples=[
    Sample(sample_model(tree={"0.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n| FAO | 식량농업기구 |",
                              "p/c/1.1. 가.md": "FAO가 정했다."}, extra=_V64_SAMPLE_EXTRA), expect=1),
    Sample(sample_model(tree={"0.md": "약어는 장마다 처음 나오는 곳에서 푼다.\n\n| FAO | 식량농업기구 |",
                              "p/c/1.1. 가.md": "식량농업기구(FAO)가 정했다."},
                        extra=_V64_SAMPLE_EXTRA), expect=0),
])
def v64_abbr_first_use(model: DocModel) -> GateOutput:
    """약어 장 첫 등장 풀이 — 장마다 처음 나오는 약어에 풀이가 없음(규약 문장을 선언한 문서만)."""
    n, items = abbr_first_use(_texts(model), _abbr_rule(model), _style(model))
    return GateOutput(n, [Finding(loc, msg) for loc, msg in items])


# ═══ V7 이미지 라이선스 (check_v2 823 · 1460-1467) ═══

IMG = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")


@gate("V7", samples=[
    Sample(sample_model(cards={"1.1": _card("![가](assets/images/a.png)")}), expect=1),
    Sample(sample_model(cards={"1.1": _card("![가](assets/images/a.png)")},
                        image_license="a.png\tCC-BY\n"), expect=0),
])
def v7_image_license(model: DocModel) -> GateOutput:
    """본문 이미지(![]())가 라이선스 대장에 없음 — 대장이 없으면 이미지마다 1건."""
    lic = model.image_license
    out: list[Finding] = []
    n = 0
    for cid, card in model.cards.items():
        whole = "\n".join(b for _, _, b in card_texts(card))
        for m in IMG.finditer(whole):
            n += 1
            parts = m.group(1).split()
            # 원본은 빈 주소 「![]()」에서 멈춘다(split()[0]) — 여기서는 빈 이름으로 본다
            name = Path(parts[0].strip("\"'")).name if parts else ""
            if lic is None or name not in lic:
                out.append(Finding(f"{cid} 이미지: {name}", f"{cid} 이미지 {name} — 라이선스 대장에 없음"))
    return GateOutput(n, out)


# ═══ V14 요약·본문 일치 (check_v2 460 · 1378-1389 · 1446-1458) ═══
# 요약의 영문 고유명·소수 수치가 그 카드 본문(섹션)에 실재하는가. 본문에 없는 것 하나가 1건.

QS_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}|\d+\.\d+(?:%|배)?")
# 절·장·도표 번호는 다른 절을 가리키는 것이 정상이므로 뺀다
QS_REF = re.compile(r"\d+\.\d+\s*(?:절|장)|(?:그림|표|차트)\s*[\dA-Za-z][\w.\-]*")


def _qs_text(q) -> str:
    """quick_summary 두 꼴(목표 상자 goal/questions · summary dict)과 문자열·목록 → 값만 이은 글."""
    if is_goal_form(q):
        return " ".join([str(q.get("goal") or ""), *goal_questions(q)])
    if isinstance(q, dict):
        return " ".join(str(v) for v in q.values())
    if isinstance(q, list):
        return " ".join(str(v) for v in q)
    return str(q)


def summary_ghosts(card: dict) -> list[str]:
    qs = _qs_text(card.get("quick_summary", ""))
    if not qs:
        return []
    body_all = "\n".join(b for _, _, b in sections_of(card))
    qs_wo_ref = QS_REF.sub("", qs)
    return sorted(t for t in set(QS_TOKEN.findall(qs_wo_ref))
                  if t not in body_all and not t.startswith(("REF", "http"))
                  and t.lower() not in ("quick", "summary"))


@gate("V14", samples=[
    Sample(sample_model(cards={"1.1": _card("본문은 NDVI를 쓴다.", quick_summary="NDVI와 EVI")}),
           expect=1),
    Sample(sample_model(cards={"1.1": _card("본문은 NDVI를 쓴다.", quick_summary="NDVI를 본다")}),
           expect=0),
])
def v14_summary_body(model: DocModel) -> GateOutput:
    """요약·본문 일치 — 핵심요약(목표 상자 포함)의 영문 고유명·소수 수치가 그 카드 본문에 없음."""
    out: list[Finding] = []
    n = 0
    for cid, card in model.cards.items():
        if _qs_text(card.get("quick_summary", "")):
            n += 1
        ghosts = summary_ghosts(card)
        msg = f"{cid} 요약에만 있고 본문에 없음 {len(ghosts)}건: {', '.join(ghosts[:6])}"
        # 원본은 한 자리를 n건으로 센다(hit(…, len(ghosts))) — 엔진 건수 = 지적 수라 n개를 낸다
        out += [Finding(f"{cid}|-: 요약", msg) for _ in ghosts]
    return GateOutput(n, out)
