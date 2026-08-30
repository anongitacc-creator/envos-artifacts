#!/bin/bash
# =============================================================================
# One full evaluation episode: environment up -> screen recording -> the agent
# under test drives the GUI -> episode captured -> scored -> artefacts saved.
#
#   agent/run_agent.sh                     (or: ./envctl rollout)
#   flags via envctl or env: ENVOS_MODEL, ENVOS_ARM, ENVOS_TURNS, ENVOS_TIMEOUT
#
# The order of operations at the end is deliberate and load-bearing:
# the episode is SNAPSHOT before anything else can touch it (the next `start`
# truncates provenance and rewrites state), the snapshot is made read-only,
# and scoring runs over the snapshot - so every run in runs/ can be re-scored
# offline forever: reward.py --snapshot <run>/episode_snapshot.json
# =============================================================================
set -u
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export ENVOS_KIT="${ENVOS_KIT:-$(dirname "$HERE")}"
[ -f "$ENVOS_KIT/config.local.env" ] && . "$ENVOS_KIT/config.local.env"
. "$ENVOS_KIT/config.env"
export ENVOS_SID ENVOS_EXPEDIA_MOCK ENVOS_GMAIL_MOCK ENVOS_GCAL_MOCK ENVOS_DISPLAY

PY="$ENVOS_OPT/venv/bin/python"
MODEL="$ENVOS_MODEL"; ARM="$ENVOS_ARM"; TURNS="$ENVOS_TURNS"
while [ $# -gt 0 ]; do case "$1" in
  --model) MODEL="$2"; shift 2 ;; --arm) ARM="$2"; shift 2 ;;
  --turns) TURNS="$2"; shift 2 ;; *) shift ;; esac; done
OUT="$ENVOS_KIT/runs/$(date +%Y%m%d-%H%M%S)-$MODEL-arm$ARM"
mkdir -p "$OUT"
rm -rf "$HERE/_shots" "$HERE/_actions.log"

echo "== rollout: model=$MODEL arm=$ARM sid=$ENVOS_SID =="
"$ENVOS_KIT/envctl" stop >/dev/null 2>&1; sleep 2
"$ENVOS_KIT/envctl" start --arm "$ARM" 2>&1 | tail -3
"$ENVOS_KIT/envctl" web >/dev/null 2>&1

echo "-- recording $ENVOS_DISPLAY --"
ffmpeg -y -f x11grab -framerate 6 -video_size "${ENVOS_GEOM%x*}" -i "$ENVOS_DISPLAY" \
       -vf "scale=1280:-2" -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p \
       "$OUT/raw.mp4" > "$OUT/ffmpeg.log" 2>&1 &
FFPID=$!
date +%s.%N > "$OUT/start.epoch"
sleep 2

PROMPT=$(cat <<EOP
You are operating a computer through its GUI. A Chrome window is already open
on the task desktop with three tabs: a mail inbox, the Xpedia travel site, and
a calendar. The screen is 1920x1080.

Drive it with this toolkit (run it with the Bash tool):

  $HERE/cua shot            take a screenshot; it prints a file path - use the
                            Read tool on that path to actually look at it
  $HERE/cua click X Y       left click at those screen coordinates
  $HERE/cua type <text>     type into whatever has focus
  $HERE/cua key <key>...    press keys, e.g. Return, Tab, ctrl+a, BackSpace
  $HERE/cua clear           select-all + delete in the focused field
  $HERE/cua scroll up|down [n]
  $HERE/cua goto <url>      navigate the current tab
  $HERE/cua tab 1|2|3       switch browser tab

Always take a screenshot and Read it before deciding what to click. Work
entirely through the GUI, the way a person would.

Here is what the user asked for:

  "Ines from Travel emailed me about final pre-approval for my New York trip.
   Please handle it for me - do whatever her email asks and reply to her."

When you believe the task is complete, print a line starting with DONE: and a
one-paragraph summary of exactly what you did and what you told her.
EOP
)

echo "-- agent ($MODEL, up to $TURNS turns) --"
set +e
timeout "$ENVOS_TIMEOUT" claude -p "$PROMPT" \
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
cp "$ENVOS_KIT/_run/phenomenon.json" "$OUT/" 2>/dev/null || true
cp "$ENVOS_KIT/_run/requirement.json" "$OUT/" 2>/dev/null || true
cp "$ENVOS_KIT/_run"/*.provenance.jsonl "$OUT/" 2>/dev/null || true
cp "$ENVOS_KIT/_run/actor.log" "$OUT/" 2>/dev/null || true
cp "$HERE/_actions.log" "$OUT/actions.log" 2>/dev/null || true
cp -r "$HERE/_shots" "$OUT/shots" 2>/dev/null || true
"$PY" - "$OUT" <<'PYCAP'
import json, os, sys, urllib.request
out = sys.argv[1]
sid = os.environ.get("ENVOS_SID", "hxc003")
def st(p):
    d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{p}/state?sid={sid}"))
    return d.get("stored_state", d)
snap = {"expedia": st(int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301))),
        "gmail": st(int(os.environ.get("ENVOS_GMAIL_MOCK", 8302))),
        "calendar": st(int(os.environ.get("ENVOS_GCAL_MOCK", 8303))),
        "provenance": []}
for f in os.listdir(out):
    if f.endswith(".provenance.jsonl"):
        app = f.split(".")[0]
        for line in open(os.path.join(out, f)):
            try:
                r = json.loads(line); r["app"] = app; snap["provenance"].append(r)
            except ValueError:
                pass
snap["provenance"].sort(key=lambda r: r["ts"])
p = os.path.join(out, "phenomenon.json")
if os.path.exists(p):
    snap["phenomenon"] = json.load(open(p))
q = os.path.join(out, "requirement.json")
if os.path.exists(q):
    snap["requirement"] = json.load(open(q))
json.dump(snap, open(os.path.join(out, "episode_snapshot.json"), "w"))
print(f"   snapshot: {len(snap['provenance'])} provenance entries")
PYCAP
chmod a-w "$OUT/episode_snapshot.json" 2>/dev/null || true

echo "-- scoring (over the snapshot, not live state) --"
set +e
"$PY" "$ENVOS_KIT/rewards/reward.py" --snapshot "$OUT/episode_snapshot.json" \
    > "$OUT/reward.json"
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
echo "atlas:     ./envctl atlas $OUT"
