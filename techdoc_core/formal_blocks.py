"""정형 사양 블록 — SW 정형화용 카드 블록 (F32).

방법론·표준 카드가 함수 명세·상태벡터 스키마·파라미터 표준표를 구조화 JSON으로
담아, 본문에는 markdown 정형 박스로 렌더하고 코드/데이터로 추출(CSV·JSON Schema)한다.

카드 스키마(additive, optional):
    card["formal_blocks"] = {
      "function_spec": [{name, signature, io, unit, range, default, source}, ...],
      "param_table": {"columns": [...], "rows": [[...], ...]},
      "state_vector_schema": { ...JSON Schema... },
    }
"""
from __future__ import annotations

import io as _io
import json
from csv import writer as _csv_writer

_FUNC_COLS = [
    ("name", "이름"), ("signature", "시그니처"), ("io", "입출력"),
    ("unit", "단위"), ("range", "유효범위"), ("default", "기본값"), ("source", "출처"),
]


def render_function_spec(specs: list[dict]) -> str:
    """함수 명세 리스트 → markdown 표."""
    if not specs:
        return ""
    header = "| " + " | ".join(label for _k, label in _FUNC_COLS) + " |"
    sep = "|" + "|".join(["---"] * len(_FUNC_COLS)) + "|"
    rows = [
        "| " + " | ".join(str(s.get(k, "")) for k, _label in _FUNC_COLS) + " |"
        for s in specs
    ]
    return "\n".join([header, sep, *rows])


def render_param_table(table: dict) -> str:
    """파라미터 표준표 → markdown 표."""
    cols = table.get("columns") or []
    rows = table.get("rows") or []
    if not cols:
        return ""
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    body = ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def param_table_to_csv(table: dict) -> str:
    """파라미터 표준표 → CSV 문자열 (추출용)."""
    buf = _io.StringIO()
    w = _csv_writer(buf, lineterminator="\n")
    if table.get("columns"):
        w.writerow(table["columns"])
    for row in table.get("rows") or []:
        w.writerow(row)
    return buf.getvalue()


def render_formal_blocks(card: dict) -> str:
    """카드의 formal_blocks → markdown 정형 박스 (없으면 빈 문자열)."""
    fb = card.get("formal_blocks")
    if not isinstance(fb, dict) or not fb:
        return ""
    parts: list[str] = []
    if fb.get("function_spec"):
        parts.append("### 함수 명세\n\n" + render_function_spec(fb["function_spec"]))
    if fb.get("param_table"):
        parts.append("### 파라미터 표준표\n\n" + render_param_table(fb["param_table"]))
    if fb.get("state_vector_schema"):
        schema = json.dumps(fb["state_vector_schema"], ensure_ascii=False, indent=2)
        parts.append("### 상태벡터 스키마\n\n```json\n" + schema + "\n```")
    return "\n\n".join(parts)
