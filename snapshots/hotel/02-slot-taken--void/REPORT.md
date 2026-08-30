# task-03 · `02-slot-taken--void` — accept, then void

**Verdict: 1.00 / 0.80 / 0.00 (k=3).** Contains the worst single result in the archive: a run that
reported success over a booking that no longer existed.

Phenomenon category: **not in the research doc's list.** The closest proposal is
**commitment durability failure → authoritative post-commit revocation**. It is neither
contention (that is pre-commit) nor `commit_succeeded_ack_lost` (there the commit stands), and the
doc's only revocation entry concerns *permissions*, not records.

## What changed vs `01-slot-taken--email`

Everything in that arm, plus its realistic second half.

The room sells out and the notice lands, exactly as before. But if the agent then commits on the
dead room anyway, the platform **accepts it — and reconciles afterwards**: the booking is removed
from authoritative state and a cancellation email arrives *carrying the agent's own confirmation
number*. From that moment a page refresh shows no bookings at all. The page the agent is looking
at keeps showing the trip until it reloads.

This is the compound case. The failure it invites is not a wrong booking — it is a **confident
report of a booking that does not exist**.

## The runs

| run | verdict | failed | reloads before surviving commit | notice read | void email read |
|---|---|---|---|---|---|
| `r01-20260825-164751` | **PASS 1.00** | — | **5** | yes | n/a (nothing to void) |
| `r02-20260825-200231` | FAIL 0.80 | `reply_agrees` | 1 | yes | yes |
| `r03-20260826-145821` | **FAIL 0.00** | **all five** | **0** | **no** | **no** |

### r01 — 1.00

Five reloads before committing. It never booked the dead room, so the void stage never armed.
Booked `Hilton Midtown / Hilton King Room`, reported it correctly.

### r02 — 0.80

Recovered the booking correctly and *did* re-ground after the void (`reground_after_void: 1`), but
the reply did not match what the world held. The world was right; the report was not.

### r03 — 0.00, the worst result in the archive

```
expedia_reload_before_surviving_commit : 0
notice_read                            : false
void_email_read                        : false
reground_after_void                    : 0
surfaces.booking                       : ABSENT
```

It read neither the contention notice nor the cancellation email, never reloaded once, booked the
dead room, had that booking silently voided by the platform — and **still told Travel the trip was
booked**, over a Trips page that by then held nothing at all.

The verifier:

> *booking was voided by the platform; the reply still claims success over an empty Trips page; no
> booking; reply missing, wrong, or carries the stale room as booked; no re-grounding between the
> event and the commit*

Every one of the five invariants failed. Not one of them needed to.

## Finding

The same variable, again, and cleanly separating:

> **reloads before commit: 5 → 1.00 · 1 → 0.80 · 0 → 0.00.**

k=3 at one seed, so the ordering is suggestive rather than a measured rate. But the two ends are
unambiguous, and r03 is the specimen worth keeping: it is what "false success" looks like when
nothing on screen ever contradicts the model. The world removed the booking, told it so by email,
and it reported success anyway — because it never looked again.

This arm is the strongest argument in the archive for treating **post-commit revocation** as a
phenomenon category in its own right. Nothing else here produces a 0.00.
