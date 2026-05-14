---
description: TechDoc 보고서를 자율 모드(walk-away)로 실행. /loop 기반 self-paced 에이전트. 매 wake-up 1 chunk (섹션 그룹) 처리. 6 safety 트리거 + 이상 시 chat 알림.
allowed-tools: Bash, Read, Write, Agent
argument-hint: "\"<title>\" --toc FILE --domain tech|market|policy [--max-wall-clock 4h] [--max-warnings 10] [--notify anomalies_only|each-wake-up] [--push-notion <id>] [--export-wiki <vault>] [-o OUTPUT]"
---

# /techdoc-autopilot — 자율 보고서 생성

`/techdoc`이 60~130분 동기 실행이라 사용자가 watching해야 하는 부담을 해소. autopilot은 매 wake-up마다 1 chunk(섹션 그룹)를 처리하고 다음 wake-up을 스스로 스케줄. 사용자는 walk-away 가능.

## 사용법

```bash
/techdoc-autopilot "AI 반도체 기술보고서" \
  --toc ./toc.txt \
  --domain tech \
  --deep-dive-auto 5 \
  --push-notion 2f1a9b8c4d5e6f7a8b9c0d1e2f3a4b5c
```

## 흐름

1. **Setup** — `python -m scripts.autopilot "<title>" --doc $OUTPUT_DIR ...` 호출.
   - `autopilot_state.json` 초기화 (stage tracker + config)
   - `autopilot.lock` 생성 (동시 실행 방지)
   - `/loop` prompt를 stdout에 출력 (다음 단계가 사용)

2. **`/loop` 진입** — 위 prompt를 superpowers loop 스킬 dynamic mode에 전달.
   - 매 wake-up마다 `python -m scripts.autopilot_step --doc $OUTPUT_DIR` 실행
   - JSON 결과(`status`·`next_wake_up_seconds`)에 따라 ScheduleWakeup 또는 종료

3. **모니터링** — 사용자는 walk-away. 필요 시:
   - `/techdoc-autopilot-status` — 진행률 확인
   - `tail -f $OUTPUT_DIR/autopilot.log` — 실시간 로그
   - `/techdoc-autopilot-stop` — graceful halt 요청

## 인자

| 인자 | 기본값 | 효과 |
|---|---|---|
| `"<title>"` | 필수 | 보고서 제목 |
| `--toc FILE` | (없음) | TOC 파일 경로 (`/techdoc`과 동일) |
| `--domain tech\|market\|policy` | (없음) | 도메인 |
| `--style 서술형\|개조식` | `서술형` | 문체 |
| `--deep-dive-auto N`·`--deep-dive ...`·`--no-deep-dive` | — | 별첨 제어 |
| `--depth quick\|standard\|deep` | `standard` | 조사 깊이 |
| `--ref file:...\|url:...\|site:...` | — | 사용자 참고자료 |
| `-o DIR` | `./output` | 출력 디렉토리 |
| `--max-wall-clock 4h` | `4h` | 최대 실행 시간 (h/m/s 또는 숫자) |
| `--max-warnings 10` | `10` | quality WARN 임계 (초과 시 halt) |
| `--notify anomalies_only\|each-wake-up` | `anomalies_only` | 알림 모드 |
| `--push-notion <id>` | (없음) | render 단계에서 Notion publish |
| `--export-wiki <vault>` | (없음) | render 단계에서 wiki export |

## 자동 정지 트리거 (6)

| 트리거 | 조건 |
|---|---|
| `quality_fail` | check_quality FAIL > 0 |
| `quality_warn_exceeded` | WARN > `--max-warnings` |
| `card_failures_exceeded` | 누적 카드 retry 3회 초과 카드 수 > 5 |
| `wall_clock_exceeded` | 시작 후 `--max-wall-clock` 초과 |
| `state_corruption` | `writer_state.json` 또는 `autopilot_state.json` parse 실패 |
| `manual_stop` | `$OUTPUT_DIR/autopilot.stop` 파일 생성 |

halt 시 chat 알림 + state 보존. `/techdoc-autopilot-resume`으로 재개.

## 종료 코드

- `0`: 정상 완료.
- `1`: 시작 실패 (인자 오류·lock 충돌·NOTION_TOKEN 미설정 등).
- `2`: halt (state.halt_reason 참조).
