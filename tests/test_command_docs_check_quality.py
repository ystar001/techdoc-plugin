"""명령 문서의 `scripts.check_quality` 호출이 CLI 인자 계약을 지키는지 (findings F107).

`check_quality`는 위치 인자를 받지 않는다 — 입력은 `-i/--input`(output 폴더 또는
document_*.json). 위치 인자로 부르면 argparse 오류로 멈춘다(`/techdoc-enrich` 재현 경로).
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC_DIRS = ("commands", "agents", "prompts")
_CALL = re.compile(r"python -m scripts\.check_quality\b(?P<args>(?:[^\n]*\\\n)*[^\n]*)")
_FLAGS_WITH_VALUE = {"-i", "--input", "--refs", "-o", "--output", "--baseline", "--tolerance"}
_FLAGS_BARE = {"--strict", "-h", "--help"}


def _calls() -> list[tuple[str, str]]:
    out = []
    for d in DOC_DIRS:
        for p in sorted((ROOT / d).rglob("*.md")):
            text = p.read_text(encoding="utf-8")
            for m in _CALL.finditer(text):
                args = m.group("args").replace("\\\n", " ")
                args = re.split(r"\s(?:2>|\||>|&&|#)", args, maxsplit=1)[0]
                out.append((f"{p.relative_to(ROOT).as_posix()}", args.strip()))
    return out


def _problems(args: str) -> list[str]:
    toks = shlex.split(args, posix=True)
    probs, i, has_input = [], 0, False
    while i < len(toks):
        t = toks[i]
        if t in _FLAGS_WITH_VALUE:
            has_input |= t in ("-i", "--input")
            i += 2
            continue
        if t in _FLAGS_BARE:
            i += 1
            continue
        probs.append(f"위치 인자 또는 모르는 인자: {t}")
        i += 1
    if not has_input:
        probs.append("-i/--input 없음")
    return probs


def test_f107_command_docs_call_check_quality_with_input_flag():
    calls = _calls()
    assert calls, "명령 문서에서 check_quality 호출을 하나도 못 찾음 — 정규식 점검"
    bad = {f"{where}: {args}": _problems(args) for where, args in calls if _problems(args)}
    assert not bad, bad


def test_f107_problem_detector_catches_positional_call():
    assert _problems('"$OUTPUT_DIR/cards"')
    assert not _problems('-i "$OUTPUT_DIR"')
    assert not _problems('--input "$O/document_draft.json" --refs "$O/r.json" -o "$O/q.json"')
