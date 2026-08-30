# task-03 · `06-write-coerced--cosmetic-control` — the control, and it is not clean

**Verdict: 0.80, 1.00, 1.00 — 2/3.** Reported as a control that partly failed, because a control
that is quietly dropped is worse than no control.

## What it is

The matched cosmetic control for `05-…--room-substituted` (README §12). The same write is
intercepted on the same path, the same provenance record is written — and the room is left **alone**.
Certification asserts `from_room == to_room` and that the booking stores the room that was chosen.

It exists to separate "the write was touched" from "the write was changed". The deliberately naive
policy scores **1.00** here and **0.60** on the treatment, for identical behaviour.

## The runs

| run | verdict | booked | note |
|---|---|---|---|
| `r01-20260829-021557` | **FAIL 0.80** | LUMA Hotel · Urban King · $289 | ⚠️ a plain policy error in an unchanged world |
| `r02-20260829-023130` | **PASS 1.00** | Ace Hotel · Bunk Room · $129 | correct |
| `r03` | **PASS 1.00** | Ace Hotel · Bunk Room | correct |

`r01` applied the reimbursement rules wrongly and booked a $289 room where the policy selects a $129
one. Nothing in its world had moved: no substitution, no contention, no reissue. That is a baseline
failure, not a phenomenon failure.

## What it means for the treatment

It means the causal claim on `05` is weaker than task-01's, and `05`'s REPORT says so. The base rate
for this task is not a reliable 1.00 at k=3 for this agent, and its `00-baseline-clean` arm was only
ever run at **k=1**.

**Open action: run task-03's CLEAN baseline at k≥5** before any rate from this task is quoted. Until
then `05` is reported as a mechanism — the coercion applied in 3/3 and the store held a room the
agent had not booked in 3/3 — and not as a failure rate attributable to the phenomenon.
