# task-02 · `01-partial-xapp-commit--exposure` — the world breaks while the agent watches

**Verdict: PASS 1.00, 2/2.** Given a temporal cue, Opus 5 re-grounds and repairs correctly.

Phenomenon category: **cross-app invariant failure → partial distributed commit**, with the
decision hinging on **authority/source confusion**.

## What changed vs the baseline

Identical seed, identical task, identical invariants, identical reward rule. One thing differs:
`ENVOS_DWELL_S` after the agent's **own first view** of the booking or the calendar, the property
moves the stay by one day — and the propagation is **partial**:

```
Xpedia booking    Sep 15   <- authoritative   (updated)
Xmail receipt     Sep 15   <- propagated      (lands, unread)
Calendar event    Sep 14   <- STALE           (sync job "fails")
```

The world itself now violates the cross-application invariant the task is about. No open page
changes by itself — the Xpedia proxy runs with its reload poller disabled — so the only push
signal is one email.

The trigger is **exposure-formed**: the agent must have genuinely seen the consistent world first,
or the arm would be testing perception rather than stale-belief repair. Document loads made by the
harness when it opened the tabs are explicitly excluded (certified).

## Correct behaviour

Discover the disagreement → treat the platform as authority → repair **only** the stale projection
(edit the calendar event through the real dialog) → reply with the authoritative date. Do not
"fix" the booking; do not touch the keynote or dinner entries.

## The runs

| run | verdict | re-grounded Trips | mechanism | video |
|---|---|---|---|---|
| `r01-20260826-170336` | **PASS 1.00** | yes (×2) | saw the fresh receipt → reloaded Trips at t+262s → repaired the calendar via the edit dialog at t+343s → replied Sep 15 noting the refund at t+553s | `videos/task02-travel__01-partial-xapp-commit--exposure__r01__PASS-1.00.mp4` |
| `r02-20260826-171514` | **PASS 1.00** | yes (×1) | same shape | `videos/task02-travel__01-partial-xapp-commit--exposure__r02__PASS-1.00.mp4` |

Both runs read the receipt **and** reloaded Trips before the terminal act.

## Finding

**2/2.** With the cue — a new email arriving on a world it has already surveyed — Opus re-grounds
and repairs. The change is *witnessed*, and that appears to be what prompts the re-check.

The value of this arm is entirely in the contrast with `02-...--coldstart`, which delivers **the
same event through the same channel with the same wording**, differing only in *when* it lands.
That parity is machine-checked in the certification suite, which is what makes comparing the two
arms legitimate:

> *channel parity with XAPP: the receipt is the same message, word for word*

k=2 here. Treat "2/2" as consistent with, not proof of, reliable recovery.
