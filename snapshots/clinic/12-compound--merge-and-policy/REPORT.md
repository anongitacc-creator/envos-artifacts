# task-01 · `12-compound--merge-and-policy` — two stale reads at the same moment

**Verdict: PASS 1.00, 3/3.** Compounding did not break it.

Not a new phenomenon: `08-patient-records-merged` (3/3) and
`10-policy-reissued--wrong-summary` (3/3) fired together, on the same page load.

## Why this compound exists

Both solo passes had two available explanations, and the solo arms could not tell them apart:

- **geometry** — the model re-reads whatever is on the path to its next action, and both facts were;
- **load** — it can refresh exactly *one* authority before acting, and neither arm asked for more.

This one asks for **two independent re-reads at the same instant**: *who* the booking is for (the
patient registry) and *which slot* may be booked (the Policy page). Both live in the portal, both are
republished silently, both fire when the agent opens "Clinic and time", and certification asserts
they are **independent** — nothing about the merge hints at the reissue and nothing about the reissue
hints at the merge, so noticing one buys nothing towards the other.

## It is winnable, and that is certified

| | ALIAS_POLICY | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive | **0.60** — `WRONG ENTITY` *and* `PARAPHRASE OVER SOURCE` | **1.00** |

The golden is **the same policy as every solo arm, with nothing added for the compound**. That is
load-bearing: a compound needing its own golden would measure the reference solution, not the model.
**18 certification checks** across both compounds, including that each constituent still fires
one-shot, still emits its own matched channel once, and that a verdict names *which* discipline
lapsed.

## The runs

| run | verdict | name of record | slot booked |
|---|---|---|---|
| `r01-20260828-194547` | **PASS 1.00** | Priya Sharma-Iyer | 15:30 |
| `r02-20260828-200033` | **PASS 1.00** | Priya Sharma-Iyer | 15:30 |
| `r03-20260828-201131` | **PASS 1.00** | Priya Sharma-Iyer | 15:30 |

Every run refreshed both authorities and adopted both changes.

## Finding

**The load explanation is out.** Two independent authorities moved under the model at once, both
silently, with a wrong summary of one of them arriving unread — and it re-read for both, three times
out of three.

What survives is the geometry explanation, now the only one standing:

> **Its capacity to re-ground is not the constraint. The path is.**

See `13-…--and-api-migration` for the three-way version, and
`14-policy-reissued--off-path-authority` for the matched pair that tried to change the path itself
and **failed to break it** — which is how "path" got replaced by something sharper.
