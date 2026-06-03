---
description: halted autopilot 재개. halt_reason 클리어 + /loop 재진입.
allowed-tools: Bash, Read
argument-hint: "[--resume-from-disk] [-o OUTPUT]"
---

# /techdoc-autopilot-resume

`autopilot_state.halt_reason` 클리어 + `autopilot.stop` 삭제 후 /loop 재진입. `quality_fail`·`card_failures_exceeded`의 경우 사용자가 문제 해결(`/techdoc-rewrite` 등) 후 호출하길 권장.

## 중반 재개 (`--resume-from-disk`)

`autopilot_state.json`이 유실되었거나 외부에서 일부 산출물(`/techdoc` 부분 실행 등)을 만든 상태에서 자율 모드로 이어가려면, state 신규 생성 시 디스크 산출물을 스캔해 완료 stage를 자동 마킹할 수 있다.

```bash
python -m scripts.autopilot "<title>" --doc "$OUT" --resume-from-disk --print-loop-prompt
```

`scan_completed_stages`가 `draft_outline.json`(outline)·`reference_list.json`(merge_research)·`research_*.json`(research_A/B/C)·`cards/*_card.json`(write_*)·`reviews/*.md`(review)·`document_final.json`(render)를 검사해 해당 stage를 `completed`로 표시한다. 산출물이 없는 stage는 `pending`을 유지하므로, autopilot은 중단 지점부터 이어서 처리한다. (결정론적·LLM 호출 0회)

```bash
OUT="${OUTPUT_DIR:-./output}"
python -c "
import json
from pathlib import Path

state_path = Path('$OUT') / 'autopilot_state.json'
if not state_path.exists():
    print('오류: autopilot_state.json 없음', flush=True)
    raise SystemExit(1)
s = json.loads(state_path.read_text(encoding='utf-8'))
if not s.get('halt_reason'):
    print('이미 halted 상태가 아닙니다 (halt_reason=null).')
    raise SystemExit(1)
prev = s['halt_reason']
s['halt_reason'] = None
state_path.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')
stop_flag = Path('$OUT') / 'autopilot.stop'
if stop_flag.exists():
    stop_flag.unlink()
lock_path = Path('$OUT') / 'autopilot.lock'
if lock_path.exists():
    lock_path.unlink()
print(f'resume: halt_reason \"{prev}\" 클리어. /loop 재진입 진행.')
"

# /loop prompt 출력 (autopilot.py와 같은 형식)
LOOP_PROMPT="techdoc autopilot loop iteration for output directory: $OUT

1. Run python -m scripts.autopilot_step --doc \"$OUT\"
2. Parse stdout JSON: status, next_wake_up_seconds, reason
3. If \"done\" or \"halt\": stop loop.
4. If \"continue\": ScheduleWakeup with delaySeconds=next_wake_up_seconds, reason=\"techdoc autopilot continuation\"
"
echo "$LOOP_PROMPT"
echo "위 prompt를 /loop dynamic mode로 전달하세요."
```
