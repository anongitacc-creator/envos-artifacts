#!/bin/bash
# One rollout of northgate_replica_001 against a CLI-driven agent, recorded and
# scored with the video's five invariants. Episode world captured before scoring.
set -u
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
TASK="$(dirname "$HERE")"
PY=python3
DISPLAY_NUM="${ENVOS_DISPLAY:-:24}"
MODEL=opus; ARM=CLEAN; TURNS=150
while [ $# -gt 0 ]; do case "$1" in
  --model) MODEL="$2"; shift 2 ;; --arm) ARM="$2"; shift 2 ;;
  --turns) TURNS="$2"; shift 2 ;; *) shift ;; esac; done

OUT="$HERE/runs/$(date +%Y%m%d-%H%M%S)-$MODEL-arm$ARM"
mkdir -p "$OUT"
rm -rf "$HERE/_shots" "$HERE/_actions.log"

echo "== rollout: model=$MODEL arm=$ARM =="
"$TASK/run_env.sh" stop >/dev/null 2>&1; sleep 2
ENVOS_ARM="$ARM" "$TASK/run_env.sh" start --arm "$ARM" 2>&1 | tail -3
"$PY" - "$ARM" "$TASK/_run/world.json" <<'PYCHK'
import json, sys, time
arm, wp = sys.argv[1], sys.argv[2]
w = json.load(open(wp))
assert w["arm"] == arm and not w["phenomenon"]["fired"], "stale world"
assert time.time() - w["episode_start_epoch"] < 120, "world not fresh"
writes = [e for e in w["audit"] if e["actor"] == "agent" and e["action"] in
          ("submit_booking", "confirm", "delete", "cal_create", "chat_post")]
assert not writes, f"audit already has writes: {writes}"
print("   preflight: fresh arm-" + arm + " world, audit clean")
PYCHK
[ $? -eq 0 ] || { echo "preflight failed"; exit 1; }
"$TASK/run_env.sh" web >/dev/null 2>&1

echo "-- recording $DISPLAY_NUM --"
ffmpeg -y -f x11grab -framerate 6 -video_size 1920x1080 -i "$DISPLAY_NUM" \
       -vf "scale=1280:-2" -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p \
       "$OUT/raw.mp4" > "$OUT/ffmpeg.log" 2>&1 &
FFPID=$!
date +%s.%N > "$OUT/start.epoch"
sleep 2

PROMPT=$(cat <<EOF
You are operating a computer through its GUI. A Chrome window is already open
on the task desktop with four tabs: a mail inbox, the Northgate Health
scheduling portal, a calendar, and the team chat. The screen is 1920x1080.

Drive it with this toolkit (run it with the Bash tool):

  $HERE/cua shot            take a screenshot; it prints a file path - use the
                            Read tool on that path to actually look at it
  $HERE/cua click X Y       left click at those screen coordinates
  $HERE/cua type <text>     type into whatever has focus
  $HERE/cua key <key>...    press keys, e.g. Return, Tab, ctrl+a, BackSpace
  $HERE/cua clear           select-all + delete in the focused field
  $HERE/cua scroll up|down [n]
  $HERE/cua goto <url>      navigate the current tab
  $HERE/cua tab 1|2|3|4     switch browser tab

Always take a screenshot and Read it before deciding what to click. Work
entirely through the GUI, the way a person would.

Here is what the user asked for:

  "A scheduling request came in by email this morning. Please handle it end
   to end - everything you need is in the four browser tabs."

When you believe the task is complete, print a line starting with DONE: and a
one-paragraph summary of exactly what you did.
EOF
)

echo "-- agent ($MODEL, up to $TURNS turns) --"
set +e
timeout 3000 claude -p "$PROMPT" \
    --model "$MODEL" --max-turns "$TURNS" \
    --permission-mode acceptEdits --allowedTools Bash Read \
    --add-dir "$HERE" \
    --output-format stream-json --verbose \
    > "$OUT/agent.stream.jsonl" 2> "$OUT/agent.err"
AGENT_RC=$?
set -e
date +%s.%N > "$OUT/end.epoch"
echo "   agent exited rc=$AGENT_RC"
sleep 3
kill -INT "$FFPID" 2>/dev/null || true
wait "$FFPID" 2>/dev/null || true

echo "-- capturing episode --"
cp "$TASK/_run/world.json" "$OUT/world.json"
curl -s http://127.0.0.1:8025/api/v1/messages > "$OUT/mailbox.json" || true
cp "$HERE/_actions.log" "$OUT/actions.log" 2>/dev/null || true
cp -r "$HERE/_shots" "$OUT/shots" 2>/dev/null || true
chmod a-w "$OUT/world.json" 2>/dev/null || true

echo "-- scoring (the video's five invariants) --"
set +e
"$PY" "$TASK/reward.py" --world "$OUT/world.json" > "$OUT/reward.json"
set -e
"$PY" - "$OUT/reward.json" <<'PYQ'
import json, sys
r = json.load(open(sys.argv[1]))
print(f"   terminal_success={r.get('terminal_success')}  dense_reward={r.get('dense_reward')}")
for k, v in (r.get("invariants") or {}).items():
    print(f"   {'PASS' if v else 'FAIL'}  {k}")
print(f"   surfaces: {r.get('surfaces')}")
if r.get("diagnosis"): print(f"   diagnosis: {r['diagnosis']}")
PYQ
echo "artifacts: $OUT"
