# agent/ — the harness that runs the agent under test

## The loop

`run_agent.sh` (or `./envctl rollout`) runs one complete evaluation episode:

1. `envctl stop` + `envctl start --arm $ENVOS_ARM` — fresh instance, actor armed
2. ffmpeg starts recording the isolated display (x11grab)
3. the **`claude` CLI** is invoked headlessly:
   `claude -p "<prompt>" --model $ENVOS_MODEL --max-turns $ENVOS_TURNS
   --allowedTools Bash Read --output-format stream-json`
   under a `timeout $ENVOS_TIMEOUT` wall-clock cap
4. the episode is **snapshotted before scoring** (states + provenance +
   phenomenon → `episode_snapshot.json`, chmod a-w) — the next `start` would
   otherwise truncate it
5. `rewards/reward.py --snapshot` scores it; everything lands in `runs/<stamp>/`

## `cua` — the computer-use toolkit

The agent gets no browser API — it drives the GUI exactly as a person would,
through a ~50-line shell toolkit pinned to the task display: `shot` (numbered
screenshots, so a re-read is always a genuinely new observation), `click`,
`type`, `key`, `scroll`, `goto`, `tab`. The prompt tells it to screenshot and
Read before every action. The numbered-screenshot detail matters for
measurement: shots taken vs shots actually Read is the image-delivery metric.

## What the prompt does and does not say

The prompt states the task in the user's words and the toolkit. It does NOT
mention the phenomenon, re-checking, or emails arriving later — the discipline
under test must come from the agent, not the prompt.

## `make_atlas.py` — the failure-atlas video

Renders `runs/<stamp>/raw.mp4` into an annotated teaching cut: task card,
phenomenon card (with the correct recovery), a live evaluator panel showing
step-by-step beats (the partial commit, the stale window, the calendar
repair or its absence, the reply, stalls ≥60 s), a why-it-failed card
derived from this run's own verdict, and the invariant scoreboard. **Every beat is derived from the run's
own logged timestamps** — actions.log, provenance, phenomenon record,
reward.json — never scripted by hand. The header is derived from the run
directory's name so a re-render can never mislabel whose episode it is.

    ./envctl atlas runs/<stamp>     ->  runs/<stamp>/atlas.mp4
