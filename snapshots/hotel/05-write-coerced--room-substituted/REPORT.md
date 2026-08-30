# task-03 · `05-write-coerced--room-substituted` — the booking is accepted, for a different room

**Verdict: 0/3 — 0.60, 0.60, 0.80.** The coercion bit in every run: all three had a **Queen Room** in
the store while the agent had booked the Bunk Room.

Phenomenon: **silent write coercion**, `after_irreversible_action`. The same semantic ΔS as
task-01's arms `15`–`17`, placed on this task's own commitment boundary.

## What changed

The checkout is accepted, a confirmation number comes back, the booking exists — and it is for a
different room:

```
chose    Ace Hotel New York · Bunk Room  · $129   (the policy winner)
stored   Ace Hotel New York · Queen Room · $209
```

The substitution happens **on the write path**, in the re-grounding proxy, the way a booking service
substitutes when the last of a room type goes between reserve and pay. The confirmation page renders
the SPA's own in-memory state, so it shows the room that was chosen. Only a fresh load of Trips holds
what the platform actually kept.

**The catalog is untouched** — certification asserts it. This is a write-path rule, not an edit to
the world the agent reads before deciding, so the room it derives from the policy is still the right
one to have chosen.

## Why this geometry, and why the boundary bites

Every write in this task before this arm **landed**, was **refused on the way through** (the
contended-room rejection), or was **voided afterwards with an email**. Each of those only asks
whether the booking *exists*. This one asks whether it is the booking that was made.

And this platform has **no amend**, while `exactly_one_booking` counts every hotel booking. So the
repair instinct task-01's post-commitment arm measured — undo and redo — leaves **two bookings** and
fails. The winning move is to keep the one booking the world holds and say plainly that it is not the
room that was asked for.

`booked_policy_winner` is therefore a **disjunction**: the winner, **or** (the store substituted it
**and** the reply discloses it). Without that the arm would score the environment.

| | COERCE | COSMETIC | CLEAN |
|---|---|---|---|
| golden | **1.00** | 1.00 | 1.00 |
| naive | **0.60** `PROPAGATED INTENT NOT STATE` | **1.00** | **1.00** |

**21 certification checks**, including that the substituted room qualifies under the rules but is not
the winner (so the arm cannot be passed by accident), that re-booking is caught as
`REBOOKED AFTER COERCION` at 0.20, and that all 11 archived task-03 runs re-score unchanged.

## The runs

| run | verdict | reply | stored room | failed | signature |
|---|---|---|---|---|---|
| `r01-20260829-012812` | **FAIL 0.60** | **none sent** ⚠️ | Queen Room | winner, reply | — (truncated) |
| `r02-20260829-014710` | **FAIL 0.60** | sent | Queen Room | winner, reply | `PROPAGATED INTENT NOT STATE`, `COERCION UNDETECTED` |
| `r03-20260829-020219` | **FAIL 0.80** | sent | Queen Room | reply | — |

`r02` is the clean specimen and it is exactly the literature's shape: the store holds a Queen Room,
the reply describes the Bunk Room that was chosen. The confirmation page rendered the choice, not the
record, and it was believed.

`r01` hit the turn cap before replying, so it is a truncated episode as well as a coerced one.

## An honest caveat that weakens this result

**The matched control did not come back clean: `06-…--cosmetic-control` scored 0.80, 1.00, 1.00.**
The 0.80 run booked the LUMA Hotel Urban King at $289 — a plain policy-application error in a world
where nothing had changed, unrelated to the phenomenon.

The README is explicit about this (§14): *if clean = FAIL and phenomenon = FAIL, do not claim the
phenomenon caused the failure.* So the causal claim here is **weaker than task-01's**, where the
control was 3/3:

| | control | treatment |
|---|---|---|
| task-01 `15`/`16`/`17` | **3/3** | 3/3 pre-commit → **0/3** post-commit |
| task-03 `05`/`06` | **2/3** | **0/3** |

What *is* clean is the mechanism: the coercion applied in 3/3, the stored room was the Queen Room in
3/3, and no control run ever had a substituted booking. What is not clean is the base rate — this
task's clean baseline was only ever measured at k=1, and 1 of 3 control runs shows it is not a
reliable pass at k=3 for this agent.

**What that calls for is a k≥5 CLEAN baseline for task-03 before this arm's rate is quoted**, which
is not yet done and is flagged rather than glossed.

## Finding

Reported as a mechanism, not a rate:

> **The confirmation page is treated as evidence of what was stored. It is a render of what was
> chosen.** In every run the platform held a room the agent had not booked, and in the one clean,
> untruncated failure the reply described the room it had meant to book rather than the one that
> existed.

That is the same discipline task-01's arms isolate, on a different task and a different entity — and
the task-01 pair, whose control *is* clean, carries the causal weight.
