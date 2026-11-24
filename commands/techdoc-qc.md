---
description: 품질 게이트 — 렌더 트리·카드 경로만 받아 게이트를 돌리고, 결과마다 규칙 번호·층·대상 수·판정·집행 수준을 단다
argument-hint: <project_root> [--config techdoc.project.yaml] [--gates V8,V13] [--selftest]
---

# /techdoc-qc — 품질 게이트 (v1.11)

문서 프로젝트 폴더 하나를 받아 본체·문서 종류·분야·시리즈 묶음의 게이트를 돌린다. LLM 호출은 0회이고 결정론적이다. 같은 입력이면 같은 결과가 나온다.

```bash
cd ${CLAUDE_PLUGIN_ROOT}
python -m scripts.qc "$PROJECT_ROOT"                     # 전부
python -m scripts.qc "$PROJECT_ROOT" --gates V8,V68      # 일부만
python -m scripts.qc "$PROJECT_ROOT" --selftest          # 게이트 자기검사만
```

결과는 `<카드 폴더의 부모>/qc_report.json`(기본 `output/qc_report.json`)과 화면 표로 나온다.

## 판정과 집행 수준 — 서로 다른 두 축

| 판정 | 뜻 |
|---|---|
| `pass` | 대상을 읽었고 지적 없음 |
| `fail` | 지적 있음, 또는 문서 종류상 **있어야 할 대상이 없음** |
| `no-target` | 읽은 대상 0 — **통과가 아니다**. 따로 보고한다 |
| `skip` | 설정으로 끔, 또는 명세는 있으나 아직 구현 없음 |

| 수준 | `fail`일 때 | 합계 |
|---|---|---|
| 막음 | 종료 코드 1 | `blocking_total` |
| 경고 | 진행 | `warning_total` |
| 기록만 | 진행 | `record_total` |
| 시범 | 진행 | `pilot_total` (합계 밖) |
| 구조 | 종료 코드 1 | `blocking_total` |

## 종료 코드

| 코드 | 뜻 |
|---|---|
| 0 | 막음 수준 실패 없음 |
| 1 | 막음 수준 실패 있음 |
| 2 | 입력 없음 — 카드도 렌더 트리도 못 찾음(경로 설정 확인) |
| 3 | 게이트 자기검사 실패(게이트 코드 결함) |

## 프로젝트 설정 `techdoc.project.yaml` (선택)

없으면 플러그인 출력 관례(`output/cards`·`output/render/tree`·`output/reference_list.json`)로 돈다.

```yaml
schema: techdoc-project/1
kind: methodology              # 문서 종류 묶음 (기본 tech_report)
domain: ../_bundles/agriculture   # 분야 묶음 경로 (선택)
series: ../my-series/rules        # 시리즈 묶음 경로 (선택)
numbering: {section: arabic, appendix: letter}   # arabic(1.1) · roman(II.6) · letter_middle(2.A.7)
paths:
  cards: output/cards
  render_tree: output/render/tree
  references: output/reference_list.json
  draft: output/draft            # md 직접 저작 원고가 있으면 산문 게이트가 트리 대신 본다
gates:
  off: [V45]                     # 끌 게이트
  exempt: {"1.1": [V13]}         # 카드별 면제
  level: {V68: 경고}             # 집행 수준 덮어쓰기
extra:
  citation:
    internal_files: [PLAN.md]    # 참고문헌에 나오면 안 되는 내부 작업 파일 이름
    nonprimary_ok: {REF-012: "1차 문헌이 없는 사실"}   # 백과사전 출처 면제(사유 필수)
```

설정이 부르는 게이트 id가 없는 id면 경고가 나온다(조용히 무시하지 않음).

## 게이트 (v1.11-a)

| id | 검사 | 층 | 수준 |
|---|---|---|---|
| V8 | 인용한 REF가 참고문헌 목록에 있나 · 목록에 있는데 어디서도 안 부르는 고아 REF | 본체 | 막음 |
| V13 | 같은 문헌 중복 등록 · 비원전(백과사전) 출처 · 카드 말미 인용 목록 정합 | 본체 | 막음 |
| V45 | `[REF-n](덧말)`처럼 인용 뒤 괄호가 링크로 읽히는 꼴 | 본체 | 막음 |
| V68 | 참고문헌 목록의 내부 작업 파일 · 지은이 자리표시·빈칸 · 국문/영문 묶음과 정렬 | 문서종류 | 막음 |

나머지 게이트는 v1.11-b에서, `check_quality`·`format_gate`·`verify_cards` 흡수는 v1.11-c에서 들어온다.
