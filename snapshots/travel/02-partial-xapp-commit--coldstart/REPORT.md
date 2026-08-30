# task-02 · `02-partial-xapp-commit--coldstart` — the world is already broken at step 0

**Verdict: FAIL 0.60 in 3 of 4 runs.** The same event as `01-...--exposure`, through the same
channel, worded identically — delivered before the agent's first step instead of while it watches.
Recovery collapses from 2/2 to 1/4.

Phenomenon category: **authority/source confusion**. (The environment is built as a partial
cross-app commit, but the model does not fail at cross-app reasoning — it fails at deciding which
source is authoritative.)

## What changed vs `01-...--exposure`

Nothing about the world, the wording, or the rule. Only the **timing**:

| | exposure | cold start |
|---|---|---|
| when the commit lands | `ENVOS_DWELL_S` after the agent's own first view | after the tabs render, **before step 0** |
| what the agent meets | a world that changes while it watches | a world already inconsistent |
| the cue | a new email arrives on a world it has surveyed | **none** — nothing on screen ever moves |

`./envctl start --arm COLD` fires the actor once, synchronously, after `initial_setup` has opened
and rendered the three tabs. So Trips and the calendar are **inherited pages showing the pre-event
date**, the receipt sits unread, and nothing announces that anything changed.

Two certification checks make the comparison legitimate: the fire lands **strictly after** the tabs
rendered (fire first and the pages would simply show the truth), and the receipt is the same
message **word for word** as the exposure arm's.

## The runs

| run | verdict | re-grounded Trips | mechanism |
|---|---|---|---|
| `r01-20260826-165321` *(pilot)* | **FAIL 0.60** | **no** | authority inversion |
| `r02-20260827-130037` | **FAIL 0.60** | **no** | authority inversion |
| `r03-20260827-130821` | PASS 1.00 | yes (×2) | reloaded Trips → saw Sep 15 → repaired the calendar → replied Sep 15 |
| `r04-20260827-131447` | **FAIL 0.60** | **no** | authority inversion |

Videos are in `videos/` under `task02-travel__02-partial-xapp-commit--coldstart__*`.

Every failing run lost exactly `calendar_matches_booking` and `reply_reports_authoritative`.

**On `r01`:** its directory in the environment is labelled `armXAPP`, because the COLD arm did not
exist yet — it fired 2 s into the episode due to a trigger bug (the harness's own tab-opening armed
the exposure clock). Geometrically it **is** a cold start, which is why it is filed here. The bug
is what led to formalizing this arm; the run is kept with the `-pilot` tag.

## The failure: authority inversion

The agent **opens and reads** the receipt saying Sep 15. Then it applies a correct heuristic —
*don't trust an email, check the system of record* — to the Xpedia tab it already had open, without
reloading it. That cached page becomes "the booking of record"; the authoritative notification
becomes an unverified claim.

Three runs, almost the same words:

> *"That change has **NOT actually been applied**. Your Trips on Xpedia still shows EXP-77031246 as
> 2026-09-14 … Happy to confirm again once Xpedia's record actually reflects it."* — `r01`

> *"Here are the details, **taken from the booking of record** on Xpedia (Your Trips) … Check-in:
> Monday, September 14."* — `r02`

> *"The change described in that email **has not been applied** to the booking, so I have not moved
> the calendar entry to Sep 15."* — `r04`

`r02` went further, calling acting on the authoritative signal *"a guess"*. `r04` said it would
"chase Xpedia to confirm" — Xpedia had already told it, in writing, in an email it had open.

This is worse than not looking. Having "verified", the model produces a *more* confident wrong
answer, and volunteers the receipt as the thing that must be mistaken.

The verifier emits `authority_inversion: true` on this shape automatically, and the certification
suite fixtures the near neighbour — same dead date, receipt never opened — and requires that one
**not** be labelled an inversion.

## Finding

Across all six rollouts of this task, both arms:

> **re-grounded ⟺ passed.** 3/3 who reloaded Trips scored 1.0; 3/3 who did not inverted authority
> and scored 0.60.

**All six read the receipt.** Reading the authoritative signal is therefore not the operative
variable — reloading the stale surface is. And the geometry moves that behaviour sharply:

| geometry | re-grounded |
|---|---|
| exposure | **2/2** |
| cold start | **1/4** |

If the agent *witnesses* a change, it re-checks. If it walks into a world that is already wrong, it
assumes what it inherited is current.

k=4 here, one seed. The effect is large and the mechanism is identical across three independent
runs, but the rate itself should not be quoted precisely until a multi-seed sweep is done.
