# task-01 · `07-requirement-revised--no-notice` — the request changes, and nothing says so

**Verdict: 0/3 — 0.80, 0.60, 0.80.** The first arm in this archive built specifically to break the
model, and it does. Every run booked the superseded requirement.

Phenomenon: **long-horizon update neglect**, with the notification removed.

## Why this arm exists

`05-…` announced the correction and Opus passed 3/3. `06-…--buried` kept the same facts and only
lowered the salience — unremarkable subject, third paragraph, noise alongside — and it passed 3/3
again, costing about 30 s of detection latency and nothing else.

That report ended by naming what would actually test the axis:

> What would actually test this axis is removing the **prompt** rather than the salience — a
> correction with no new message at all, where the requirement changes and only a re-read of an
> existing surface reveals it. That is the shape the archive's real failures take.

This is that arm.

## What changed

The same revision as the announced arms — `vaccine: Influenza → Tdap`, `revision 1 → 2` — with the
notification deleted. Instead, **the brief itself is rewritten in place**:

```
messages arriving   none
unread count        unchanged  (3 total / 2 unread, before and after)
the brief           same subject, same sender, still marked read - different content
```

Certification asserts all of it, including that the revised brief differs from the original **only
where the fact differs** (a character-level comparison), so this is a requirement change and not a
rewritten task. The calendar-title format the brief dictates is revised with it, so an agent that
copies the format faithfully still gets it right.

Nothing turns bold. Nothing arrives. A fact the agent read at the start has quietly stopped being
true, and the only way to find out is to open a message it has already read.

## It is winnable, and that is certified

| | this arm | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive (reads the brief once) | **0.80** | **1.00** |

The golden uses the **same policy as every other arm** — re-read the request before committing to
it, then take a later message from the requester as superseding it. On the announced arms that
re-read finds a correction; here it finds a revised brief. One policy, four arms, 1.00 on all of
them.

30 certification checks.

## The runs

| run | verdict | booked | required | what happened |
|---|---|---|---|---|
| `r01-20260828-103845` | **FAIL 0.80** | Influenza | Tdap | `UPDATE NEGLECTED` — booked the superseded requirement and propagated it to both surfaces |
| `r02-20260828-104509` | **FAIL 0.60** | Tdap *(eventually)* | Tdap | noticed late, **deleted and recreated** the record to fix it, and left the calendar and Ops channel on Influenza |
| `r03-20260828-105918` | **FAIL 0.80** | Influenza | Tdap | `UPDATE NEGLECTED`, same shape as r01 |

r02 is the most informative. It did eventually discover the change — but only after committing, and
its repair was the one this task forbids (`no_delete_and_recreate`), leaving two of three surfaces
still asserting the dead requirement. Detection after the fact was worth 0.2 and cost it a patient
record.

## Finding — the axis, isolated

Three arms, one phenomenon, one variable: **how the change announces itself.**

| arm | the change | announced by | result |
|---|---|---|---|
| `05` explicit | Influenza → Tdap | an email titled *Correction* | **3/3 pass**, latency ~155 s |
| `06` buried | *identical* | the same facts, low salience, third paragraph | **3/3 pass**, latency ~187 s |
| `07` no notice | *identical* | nothing — the brief is revised in place | **0/3 pass** |

The state change is the same in all three. The recovery is the same. The verifier is the same. The
golden is the same. Only the prompt differs, and it decides the outcome completely.

This is the sharpest confirmation yet of what the rest of the archive has been circling:

> **Opus 5 re-reads when there is something new to notice. It does not re-read when the only thing
> that changed is the truth of something it already has.**

Salience barely matters — burying the correction cost 30 seconds and no verdicts. **Existence**
matters entirely. The failure is not inattention to a signal; it is the absence of any mechanism
that revisits a fact once acquired.

That also explains the four categories this model passed: own-write-landed, write-refused,
capability-withdrawn, requirement-corrected-with-notice — every one of them puts a *new object* in
front of it. The two it fails — the cold-start stale read, and this — put nothing in front of it at
all.

## Caveats

k=3, one seed. For this arm there is also **no observable signal that separates "read once" from
"re-read"** — Mailpit's read flag is set by the first open, so detection is inferred from behaviour
(what it booked) rather than measured directly. The `correction_read` metric is meaningless here and
is reported as such.

One field to read carefully: `reward.json`'s `phenomenon_fired` tracks the **slot-contention** block
and is correctly `false` on this arm. The requirement revision is recorded as
`requirement.revision: 2` and in the `requirement_revision` metric, and the audit log carries the
`requirement_revised` entry. All three runs confirm the revision fired.
