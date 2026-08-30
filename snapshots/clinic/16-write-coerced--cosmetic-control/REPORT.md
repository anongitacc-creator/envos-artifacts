# task-01 · `16-write-coerced--cosmetic-control` — everything moved except the thing that matters

**Verdict: PASS 1.00, 3/3.** This is a **control**, not a phenomenon, and it is what makes `15` and
`17` mean anything (README §12: controls are mandatory).

## What it is

The same event as `15-…--pre-commit`, at the same moment, writing the same audit entries and the
same `channel_emit` record, re-rendering the same page — and leaving the **value** alone.

```
15  COERCE    asked 15:00  ·  stored 15:30
16  COSMETIC  asked 15:00  ·  stored 15:00
```

Certification asserts the two arms emit an identical environment-audit sequence, so the only thing
that separates them is the value.

## Why it is here

It separates four explanations of any result on `15`/`17`:

| candidate cause | ruled out by |
|---|---|
| the page re-rendered / something visibly happened | this arm — same re-render, no effect |
| the timing of the event | same moment in both |
| an extra audit or channel record leaking a cue | identical sequence, asserted |
| the naive policy is simply bad | it scores **1.00** here and on CLEAN, **0.60** on `15` |

## The runs

| run | verdict |
|---|---|
| `r01-20260828-225419` | **PASS 1.00** |
|  `r02-20260828-230342` | **PASS 1.00** |
|  `r03-20260828-231242` | **PASS 1.00** |

Three passes in a world that held still is exactly what a control should produce. Reported because a
control that is never reported is not a control.
