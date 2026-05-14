---
description: halted autopilot 재개. halt_reason 클리어 + /loop 재진입.
allowed-tools: Bash, Read
argument-hint: "[-o OUTPUT]"
---

# /techdoc-autopilot-resume

`autopilot_state.halt_reason` 클리어 + `autopilot.stop` 삭제 후 /loop 재진입. `quality_fail`·`card_failures_exceeded`의 경우 사용자가 문제 해결(`/techdoc-rewrite` 등) 후 호출하길 권장.

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
