---
description: autopilot에게 graceful halt 요청. autopilot.stop flag 파일 생성.
allowed-tools: Bash, Write
argument-hint: "[-o OUTPUT]"
---

# /techdoc-autopilot-stop

다음 wake-up이 시작될 때 manual_stop 트리거로 graceful halt. 이미 실행 중인 chunk는 완료까지 진행.

```bash
OUT="${OUTPUT_DIR:-./output}"
touch "$OUT/autopilot.stop"
echo "autopilot.stop 생성: $OUT/autopilot.stop"
echo "다음 wake-up에 graceful halt됩니다."
```
