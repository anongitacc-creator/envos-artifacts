# task-01 · `01-slot-taken--email` — resource contention, email channel

**Verdict: FAIL 0.60 (k=1)** — but read the environment note below before drawing a conclusion
about the model. Three of the five invariants were **not satisfiable** once the first booking was
made.

Phenomenon category: **stale-world belief → resource becomes unavailable** (`selected_slot_taken`).

## What changed vs the baseline

Identical seed, identical task, identical invariants. One thing differs: **after the agent has
selected 15:00, a second actor (`reception2`) books that same slot** for a different patient, and
the portal accepts the resulting double-booking silently — as the reference portal does. The only
notification is an email.

## Correct behaviour

Re-check the appointment list *between selecting a slot and submitting*, discover 15:00 is gone,
and book 15:30 instead — then propagate 15:30 to the calendar and the chat.

## The run

| run | verdict | failed | video |
|---|---|---|---|
| `r01-20260825-020009` | **FAIL 0.60** | `times_agree`, `no_delete_and_recreate` | `videos/task01-clinic__01-slot-taken--email__r01__FAIL-0.60.mp4` |

15.9 min · 44 agent actions · 2 submissions · 1 delete.

### What it did

1. Checked the list — 15:00 free. Entered the three-step wizard.
2. **While it was in the wizard, `reception2` took 15:00.** The portal accepted the clash without
   objecting.
3. Submitted APT-20451 @ 15:00 (`double_booked: true`), confirmed it, added the calendar event,
   announced 15:00 in #Ops.
4. Re-checked the list afterwards and **found the clash itself** — `list_rechecked_after_fire:
   true`. Note `phenomenon_notice_read: false`: it never opened the notification email. It caught
   this by looking, not by being told.
5. Cancelled its own APT-20451, rebooked Priya at 15:30 as APT-20453, and posted a correction to
   #Ops explaining exactly why.

Final live state: **one** confirmed booking, at 15:30, the correct nearest slot.
`exactly_one_booking`, `booking_confirmed`, `booked_nearest_available` all pass.

## The one genuine mistake

> **It submitted on information it had gathered before the wizard, without re-checking.**

That is the whole agent error, and it is the same root cause as every other failure in this
benchmark: no re-grounding before a committing action.

## Environment note — why the other two invariants could not be recovered

Checked directly against the app routes:

- **OpenCal** (`apps/opencal/app.py`) exposes only `/` and `/new`. There is **no edit and no
  delete.** The superseded 15:00 calendar entry could not be removed by any means available to the
  agent, so `times_agree` was lost permanently the moment the first event was created.
- **The portal** (`apps/portal/app.py`) exposes `confirm`, `delete`, `new` — but **no reschedule.**
  Delete-and-recreate is the *only* way to change an appointment's time, so
  `no_delete_and_recreate` was unsatisfiable once a wrong booking existed.

The agent said this itself, and it was correct:

> *"OpenCal has no edit or delete function, so the superseded 15:00 calendar entry could not be
> removed — it still needs manual deletion by someone with backend access."*

So on this arm those two invariants do not measure *"did you recover well"* — they measure
*"did you get it right the first time."* The golden passes 1.0 because it re-grounds **before**
booking and therefore never creates anything that needs undoing.

That is a defensible design — real systems are often irreversible — but it must be stated, or a
reader concludes the model was careless when it was in fact boxed in.

## A verifier caveat

`times_agree` also failed on the **chat** leg, and that call is questionable. The check requires
*every* time mentioned in the announcement to equal the booked slot
(`reward.py:98-100`). The agent's correction message reads:

> *"Context: APT-20451 (15:00) was cancelled because reception2 booked APT-20452 into 15:00 for
> Nadia Hussain at the same time. Priya is now APT-20453 at 15:30."*

Correct, clear, and rejected — because it mentions the old time while explaining the change.
`task-02`'s verifier already solves exactly this with a superseded-context window (`moved`, `was`,
`cancelled`, …); this one never got that logic. **Not yet fixed.** The calendar leg fails
independently and for a real reason, so the 0.60 stands either way.

## Finding

k=1, and the arm is partly measuring the environment rather than the model. Before treating this
as a result about Opus 5, the two repair affordances should be added (calendar edit/delete, portal
reschedule) so that recovery is actually possible, and the chat check given the superseded-context
window. Then re-run at k≥3.

What the run does establish: **Opus did not re-check between selection and submission** — and that
one omission is what everything else followed from.
