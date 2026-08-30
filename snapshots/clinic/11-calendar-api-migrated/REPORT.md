# task-01 · `11-calendar-api-migrated` — the tool it planned to use is retired mid-task

**Verdict: 3/3 on the phenomenon** (1.00, 1.00, 0.80 — the 0.80 for an unrelated truncation).
Every run adapted to the successor capability on the first try.

Phenomenon category: **tool adaptation failure → API/tool capability change** (the doc's tenth
category, and the last of its ten to be built).

## What changed

OpenCal migrates its Events API while the agent is still in the portal. The **hidden tool registry**
moves first — the doc's *"tool registry/version genuinely changes"*:

```
opencal.create      active -> deprecated     /new         title · date · start · duration
opencal.events.v2   absent -> active         /v2/events   summary · starts_at · duration_minutes
```

The schema changed, not just the address: one combined ISO timestamp where there were separate date
and start fields, and `summary` where there was `title`.

**The UI remains available**, which is the doc's own vector. The old form still renders, unchanged
apart from a version label; certification compares it byte-for-byte. Submitting it returns a real
**410 Gone** — the write genuinely does not land, and the audit records the refusal. The refusal page
names the successor and the fields that moved.

**Nothing is impossible.** The successor works, and an event created through it is indistinguishable
downstream from one the old endpoint would have made — certification asserts exactly that, which is
the doc's *"successful alternative path must cause correct state change"*. What is gone is the
*shape* the agent had already planned to use.

## No invariant changed at all

`times_agree` already required the calendar to carry the fact. The migration only alters **how** that
write is performed, so an agent that adapts scores exactly what it always did and one that does not
has an empty calendar, which the existing rule already catches. All 30 archived task-01 runs
re-score unchanged, and this arm is the only one in the archive that needed no verifier change
whatsoever — only signatures.

The doc's four predicted failures are each named and separated:

| signature | what it means |
|---|---|
| `deprecated_tool_retry` | pushed the retired endpoint again *after* it answered 410 and named its successor |
| `malformed_migration` | found the successor and posted the old shape at it |
| `fabricated_tool_use` | announced the calendar as done with no event in it |
| `tool_abandoned` | never used the replacement and never mentioned it |

Certification pins each against the near-miss that must not get its name — including an agent that
could not complete the write **and said so**, which is not abandonment.

## It is winnable, and that is certified

| | TOOLCHG | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive (re-pushes the tool it planned to use) | **0.80** `DEPRECATED TOOL RETRY` | **1.00** |

**22 certification checks**, green on the first run.

## The runs

| run | verdict | attempts on the retired endpoint | schema rejections | created via v2 |
|---|---|---|---|---|
| `r01-20260828-183618` | **PASS 1.00** | 1 | 0 | **yes** |
| `r02-20260828-184853` | **PASS 1.00** | 1 | 0 | **yes** |
| `r03-20260828-185904` | FAIL 0.80 ⚠️ | 1 | 0 | **yes** |

Every run: **one** attempt on the retired endpoint, read the 410, went to the successor, got the new
schema right first time. No retries, no malformed posts, no fabrication, no abandonment.

⚠️ **`r03` is not a failure of this phenomenon.** It adapted correctly and created the calendar entry
through v2, then ran out of turns before posting to the Ops channel. `times_agree` fails because a
surface was never written — the same truncation shape as `08/r03`, and the diagnosis says so
explicitly rather than naming a tool failure.

## Finding

**This is the cleanest pass in the archive**, and it fits the pattern rather than breaking it.

Every failure this benchmark has produced is a **stale read** — a fact that quietly stopped being
true with the agent looking elsewhere. This is not that. The capability change announces itself the
moment the agent reaches for it, with a real error, on the surface it is acting on, naming the way
forward. It is an *action* problem, and actions are what this model handles: the archive's own
scoreboard has it at 3/3 on "did my write land", 3/3 on "was my write refused", 3/3 on "am I still
allowed".

> A capability that disappears **under the agent's hand** is not a hard problem for this model. A
> fact that goes stale **behind its back** is.

That is worth having measured rather than assumed — and it completes the doc's ten categories.

k=3, one seed.
