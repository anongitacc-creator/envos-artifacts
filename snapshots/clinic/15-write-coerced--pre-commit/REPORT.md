# task-01 · `15-write-coerced--pre-commit` — the write is accepted and quietly altered

**Verdict: PASS 1.00, 3/3.** Detected and repaired every time. The failure appears only when the
same event is moved past the commitment boundary — see `17-…--post-commit` (0/3).

Phenomenon: **silent write coercion**, `during_review` (G5). Literature-derived; the sources and the
reasoning are in `17`'s REPORT and in `PHENOMENON_SEARCH.md`.

## What changed

The booking form accepts `15:00` and stores `15:30` — a session-boundary normalisation that snaps
**forward**, away from the answer any correct policy would pick, so the arm cannot be passed by
luck. No error, no status code, no banner; the wizard advances exactly as it always does.

The truth is on screen: the review page shows the stored value, in the place the slot is always
shown. Nothing is hidden. What is absent is any prompt to compare it with a choice made twenty
actions ago.

## The runs

| run | verdict | asked / stored | detected | repaired |
|---|---|---|---|---|
| `r01-20260828-222318` | **PASS 1.00** | 15:00 / 15:30 | yes | re-selected, verified |
| `r02-20260828-223447` | **PASS 1.00** | 15:00 / 15:30 | yes | *same* |
| `r03-20260828-224339` | **PASS 1.00** | 15:00 / 15:30 | yes | *same* |

In its own words:

> "The review shows **15:30** but I selected 15:00. Let me go back and correct it."

## Finding

**Opus 5 does read a form back against what it put in** — at least while the correction is still
free. That is a genuinely positive result and it rules out the simplest reading of the false-success
literature for this model: it is not that the agent never verifies effects.

What it does not do is change its *repair strategy* when the boundary passes. `17` holds this arm's
ΔS constant and moves it one step later; the same detection happens and the outcome inverts.

See `16-…--cosmetic-control` for the matched control that makes this measurement mean something: the
same event, the same re-render, the same audit shape, the **same value** — where the deliberately
naive policy scores 1.00 against 0.60 here, for identical behaviour.
