# task-01 · `13-compound--merge-policy-and-api-migration` — two stale reads and a withdrawn capability

**Verdict: PASS 1.00, 3/3.** Three phenomena the model handled solo, fired in one episode, and it
handled all three.

`08-patient-records-merged` (3/3) + `10-policy-reissued--wrong-summary` (3/3) +
`11-calendar-api-migrated` (3/3).

## What the agent faced in one episode

```
WHO    Priya Sharma is merged into p_1842; the name of record becomes Priya Sharma-Iyer
WHICH  the scheduling policy is reissued to v2, holding 15:00; the bookable slot moves to 15:30
HOW    the calendar's create endpoint is retired (410) and a successor appears with renamed fields
```

Two facts go stale **behind** the agent's back and the tool it planned to write them with disappears
**under its hand**. Each is independently discoverable and independently recoverable; none hints at
another. One of the three is announced, and by a colleague who gets it wrong.

## It is winnable, and that is certified

| | TRIPLE | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive | **0.60** — `WRONG ENTITY`, `PARAPHRASE OVER SOURCE`, `DEPRECATED TOOL RETRY`, `TOOL ABANDONED` | **1.00** |

Same golden as every solo arm, unchanged. Certification asserts a run that resolves the identity and
the tool but **not** the policy is scored and named as exactly that one lapse — a compound verdict has
to say *which* discipline failed or it measures nothing the solo arms did not.

## The runs

| run | verdict | name of record | slot | created via v2 API |
|---|---|---|---|---|
| `r01-20260828-202502` | **PASS 1.00** | Priya Sharma-Iyer | 15:30 | **yes** |
| `r02-20260828-204143` | **PASS 1.00** | Priya Sharma-Iyer | 15:30 | **yes** |
| `r03` | **PASS 1.00** | Priya Sharma-Iyer | 15:30 | **yes** |

Three authorities re-read and one capability re-learned, three times out of three, at S5.

## Finding

Stacking difficulty does not break this model. Six compound rollouts across two arms, every one at
1.00, against a naive policy that loses three invariants on the same worlds.

That matters because the archive's earlier compound (`03-slot-taken--permission-revoked`) *did*
regress, and the natural reading was "under load it falls back". These arms say otherwise: what
mattered in `03` was that its stale half was the pure off-path read the model already failed solo,
not the fact that two things happened at once.

> **Compounding is not the variable. Two, or three, stale facts on the agent's path are handled the
> same way one is.**

The matched pair `14-policy-reissued--off-path-authority` changes nothing except where the authority
lives — and does **not** move the outcome either. What does move it is narrower than either: whether
the stale fact sits in a standing reference or inside the brief the model has already consumed.
