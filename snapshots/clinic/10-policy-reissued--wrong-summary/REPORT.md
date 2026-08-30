# task-01 · `10-policy-reissued--wrong-summary` — the same trap, on a surface the agent lives in

**Verdict: PASS 1.00, 3/3.** The identical phenomenon scored **0/3** in task-03. The difference is
where the rules are published, and it is the same axis this archive keeps landing on.

Phenomenon category: **constraint hierarchy failure → legitimate policy change mid-task.**

## What changed

Clinic Operations reissues the scheduling policy as **version 2**: `15:00` is now held daily for the
cold-chain check and nurse handover. The earliest bookable slot moves:

```
policy:clinic_scheduling   version      1 -> 2,  new effective_at
                           held_slots   [] -> ["15:00"]

under v1   15:00        under v2   15:30
```

**The appointment list is byte-identical across the reissue** — certification asserts it. Nothing was
taken, nothing sold out. The only thing that changed is the rule applied to it.

## The two channels

- **The source** — a **Policy page in the portal** (`/policy`), carrying the issuing team, the
  version number and the effective date, exactly the surface the doc's *"UI banner indicates
  effective date"* describes. It is republished silently.
- **The paraphrase** — a colleague on reception emails a summary. The reissue it reports really
  happened and the reason it gives is the right one; it names **the wrong slot**, saying the held
  slot is the last one of the session. Following it leaves 15:00 bookable — the superseded answer.
  It points back at the source: *"The Policy page in the portal has the actual wording if you need
  it."*

## It is winnable, and that is certified

| | POLICY | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive (takes the summary at face value) | **0.80** `PARAPHRASE OVER SOURCE` | **1.00** |

One golden policy across all seven arms of this task. **26 certification checks**, and all 27
previously archived task-01 runs re-score unchanged.

No sixth invariant: `booked_nearest_available` already meant *"the earliest slot free at
submission"*; it now means *"the earliest slot **bookable** at submission"*, with held slots read
from the policy object in world state. A world with no policy object holds nothing back, so the term
is exactly what it always was.

## The runs

| run | verdict | booked | read the summary | **re-read the Policy page after the reissue** |
|---|---|---|---|---|
| `r01` | **PASS 1.00** | 15:30 | yes | **yes** |
| `r02` | **PASS 1.00** | 15:30 | yes | **yes** |
| `r03` | **PASS 1.00** | 15:30 | yes | **yes** |

Every run opened the colleague's summary *and* went back to the page it summarised, and every run
followed version 2. `policy_version_followed` = 2 in all three.

## Finding — the same phenomenon, the opposite result, and the same explanation

| | where the rules are published | where the agent is working | result |
|---|---|---|---|
| task-03 `04` | an **email** — a surface it has finished with | Xpedia | ❌ **0/3** |
| task-01 `10` | a **page in the portal** — the app it is working in | the portal | ✅ **3/3** |

Both arms reissue a versioned policy. Both republish the source silently. Both send the same kind of
plausible, wrong, lower-authority summary, unread and salient. In task-03 all three runs took the
summary at face value. Here all three went and checked.

Set against the delayed-requirement-correction trio (`07` fails, task-02 `04` and task-03 `03`
pass), the archive now has two independent phenomena giving the same answer on the same axis:

> **Opus 5 re-verifies what is on the path to its next action. A fact that has gone stale off that
> path — in an app it has finished with — is not revisited, however loudly something else points at
> it.**

The paraphrase is not the variable. It was equally wrong, equally loud and equally unread in both
arms, and it even signposted the source in both. What decided the outcome was whether checking the
source meant staying where it already was.

## Caveats

- k=3, one seed.
- **This arm does not discriminate**, and its value is the contrast with task-03 `04` rather than a
  difficulty measurement. Both were built to the same standard (golden 1.0, naive 0.8 on the arm and
  1.0 on CLEAN) and only one of them broke the model.
- The brief points at the Policy page (*"Book per the clinic scheduling policy — it is on the Policy
  page in the portal, and Ops is the authority on it"*). Without that the page would not be
  discoverable and the arm would measure the environment; with it, consulting the page is part of
  the task. That instruction is present on every arm of this task from 2026-08-28 onward.
