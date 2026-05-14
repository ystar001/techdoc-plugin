---
description: techdoc-autopilot 진행 상태 표시. 실행 중·halted·완료 모두 동일 출력.
allowed-tools: Bash, Read
argument-hint: "[-o OUTPUT]"
---

# /techdoc-autopilot-status

`autopilot_state.json`을 기반으로 진행률·stage별 상태·최근 quality·다음 예정 wake-up을 출력.

```bash
python -c "
import json
from pathlib import Path
from datetime import datetime, timezone

OUT = Path('$OUTPUT_DIR' if '$OUTPUT_DIR' else './output')
state_path = OUT / 'autopilot_state.json'
if not state_path.exists():
    print('autopilot_state.json 없음 — autopilot이 시작된 적 없거나 다른 디렉토리.')
    raise SystemExit(1)
s = json.loads(state_path.read_text(encoding='utf-8'))

print('techdoc-autopilot status')
print('=' * 24)
print(f\"title:    {s.get('title')}\")
started = s.get('started_at')
if started:
    elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(started)
    print(f\"started:  {started} ({int(elapsed.total_seconds()//60)}m ago)\")
if s.get('completed_at'):
    print(f\"completed: {s['completed_at']}\")
elif s.get('halt_reason'):
    print(f\"halt:     {s['halt_reason']}\")
else:
    print('state:    in_progress')
stages = s.get('stages', {})
total = len(stages)
done = sum(1 for v in stages.values() if v in ('completed', 'skipped'))
print(f\"progress: {done}/{total}\")
print()
for k, v in stages.items():
    mark = {'completed': 'v', 'skipped': '-', 'in_progress': '*', 'pending': '.', 'failed': 'x'}.get(v, '?')
    print(f\"  {k:.<22} [{mark}] {v}\")
print()
wakes = s.get('wake_ups', [])
if wakes:
    last = wakes[-1]
    print(f\"last wake-up: chunk={last.get('chunk')} duration={last.get('duration_s')}s result={last.get('result')}\")
print(f\"log: {OUT / 'autopilot.log'}\")
"
```
