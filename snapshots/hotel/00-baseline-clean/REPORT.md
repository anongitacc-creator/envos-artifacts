# task-03 · `00-baseline-clean` — the capability control

**Verdict: PASS 1.00 (k=1).** Opus 5 applies a written three-clause policy across a hotel list and
completes a real checkout with no phenomenon present.

## What this arm is

The control. No second traveller takes the room, no notice arrives, and nothing the agent selected
stops being available while it works. The exogenous actor is not started at all.

It exists so that the failures in `01-slot-taken--email` and `02-slot-taken--void` are
attributable to the phenomenon rather than to the task being hard on its own — and on this task
that matters more than usual, because the underlying job is genuinely fiddly: a policy stated in
prose, applied in order, across a list, through a multi-step checkout.

## Correct behaviour

Travel's email states the policy in words. The agent must apply its three clauses **in order**:

1. within 1 mile,
2. free cancellation,
3. then the lowest rate.

On the clean world that selects **Ace Hotel New York, Bunk Room at $129**. Book it exactly once,
then reply saying what was booked.

## The run

| run | verdict | invariants | video |
|---|---|---|---|
| `r01-20260827-232705` | **PASS 1.00** | 5/5 | `videos/task03-hotel__00-baseline-clean__r01__PASS-1.00.mp4` |

14.6 minutes · 150 GUI actions.

Booked `Ace Hotel New York / Bunk Room` — matching `expected` exactly — once, and reported it
accurately.

The longest of the three baselines by a wide margin (3.8 min and 6.1 min for the other two tasks),
which is a fair reflection of the task: reading a policy out of prose and ranking a list against it
is more work than surveying an entity that already exists.

## Notes

- `metrics_verify` is all `null` by design — those fields describe behaviour *relative to the
  event*, and on this arm there is no event. `verified_before_commit` passes vacuously.
- The reward rule is byte-identical across CLEAN, EMAIL and VOID. Only the world differs.
- k=1. This establishes that the task is passable; it does not characterise reliability.
