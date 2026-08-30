# task-01 · `05-delayed-requirement-correction` — the request changes under it

**Verdict: PASS 1.00, 3/3.** All three runs opened the correction and adopted it. See
`06-…--buried` for the harder variant, which it also passed.

Phenomenon category: **long-horizon update neglect → delayed requirement correction** (the doc's
eighth category, and its first appearance in this archive).

## What changed vs the baseline

While the agent is filling in the booking form, Dr Chen amends the request: Priya is due a **Tdap**
booster, not influenza.

The correction is **state, not a message**. `world.json` carries an authoritative `requirement`
object, and it is revised first — `vaccine: Influenza → Tdap`, `revision: 1 → 2` — with the email as
the separately-rendered notification, exactly as the doc specifies. An agent that never re-reads the
inbox is therefore *wrong about the world*, not merely uninformed.

**Nothing in the portal changes.** No banner, no flag on the record, no hint in the form —
certification asserts the appointment list is byte-identical across the event. The inbox is the only
place the truth exists.

**Why the vaccine field:** `Tdap` is already in `w["vaccines"]` and already on a peer row, so the
dropdown accepts it with no template change; and the Ops announcement format the agent copies names
the vaccine, so the corrected value genuinely has to reach all three surfaces. `date` was ruled out
(four call sites; desynchronises the verifier) and `clinic` (scopes `taken_slots`; frees all nine
slots).

**Timing:** fires when the agent opens "Clinic and time", and never later than review. After submit
the portal has no reschedule and OpenCal has no edit, so a later correction would be unrecoverable
and the arm would measure the environment — the trap `01-slot-taken--email` already documents.

## Correct behaviour, and the invariant

No sixth invariant was added — `dense_reward = passes/5` is hardcoded and certification asserts
exact dense values. Instead `times_agree`, already *"the same fact appears on all three surfaces"*,
now means **time and vaccine**, with the expected vaccine read from `w["requirement"]` and never
from "did the phenomenon fire". CLEAN and REQCHG run identical verifier code, and all 11 previously
archived runs re-score unchanged.

## The runs

| run | verdict | read the correction | detection latency | video |
|---|---|---|---|---|
| `r01-20260828-073002` | **PASS 1.00** | yes | 135.5 s | `videos/task01-clinic__05-delayed-requirement-correction__r01__PASS-1.00.mp4` |
| `r02-20260828-073656` | **PASS 1.00** | yes | 173.1 s | … `r02` |
| `r03-20260828-074617` | **PASS 1.00** | yes | 156.6 s | … `r03` |

Every run booked Tdap and carried it to the calendar title and the Ops announcement.
`update_neglected` fired in none.

## The arm is a phenomenon, not a decoration — proven, not asserted

The doc makes this a certification requirement:

> Recovery validity should establish at least one known valid recovery path, **failure of a
> deliberately stale/naive policy**, and deterministic satisfaction of final invariants.

So the arm ships `naive_patch.py` alongside the golden: a policy that reads the brief once and never
again, but is competent at everything else — derives the earliest free slot from the authoritative
list, books once, confirms, propagates to both surfaces.

| | REQCHG | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive | **0.80** — `UPDATE NEGLECTED` | **1.00** |

The naive policy passing CLEAN is the load-bearing half: its failure here is attributable to the
correction and to nothing else about it. Certification (22 checks) asserts both rows.

## An environment defect this arm exposed

Building it surfaced a **pre-existing bug affecting every previously reported task-01 result**.

`run_env.sh stop` kills Mailpit, which runs with a persistent `--database`; a cold start silently
reloads every message from every previous episode, and the clear-on-restart path never executed. The
mailbox had grown to **47 messages**.

Measured across the archived runs: **8 of 11 began with stale notices from earlier episodes** — up
to 3 spare "Access change" notices and 2 spare "Slot update" notices. That is information leakage in
the wrong direction: an agent could read about a role downgrade *before it happened*.

Fixed — the mailbox is now cleared on every path, the persisted store is dropped on a cold start,
and setup refuses to start a polluted episode. Certification asserts the episode begins with exactly
the 3 seeded messages.

**This is a confound on the permission arms** (`02`, `03`, `04`), which were reported as passes.
Their verdicts are computed from world state and the audit log, not from mail, so the *scores* stand
— but the agent's behaviour could have been influenced by a pre-warning it should not have had.
`02/r01`, the one ACL run with a clean mailbox, passed on its own merits; the rest want re-running
now the leak is closed. **Not yet done — flagged for a decision.**

## Finding

**3/3, and genuinely: every run opened the correction and acted on it.** Detection latency clustered
at 135-173 s — it did not stumble onto the change late, it went looking.

This is the fourth consecutive phenomenon Opus 5 has handled, and it sharpens the pattern rather
than breaking it. The archive's failures are all cases where something the agent **already read**
went stale and nothing prompted a re-read. Here something it already read went stale and *an email
arrived* — a new object in a surface it was going to open anyway. That prompt appears to be
sufficient.

The distinction worth carrying forward: this model re-reads when there is **something new to notice**.
It does not re-read when the only thing that changed is the truth of something it already has.

k=3, one seed.
