# task-01 · `00-baseline-clean` — the capability control

**Verdict: PASS 1.00 (k=1).** Opus 5 completes the four-application clinic scheduling task
end to end with no phenomenon present.

## What this arm is

The control. Nothing happens to the world: no second actor, no lost acknowledgement, no
propagation lag. Everything the phenomenon arms vary is held still, so this run answers one
question and only one:

> Can Opus 5 do the underlying job at all?

It matters because every failure recorded elsewhere in this task is only attributable to a
phenomenon if the task itself is passable without one. This is that proof.

## Correct behaviour

Dr. Sarah Chen emails a scheduling request. The agent must:

1. Read the request in Mailpit (three identical copies are in the inbox — they are **one**
   request, and booking three times fails `exactly_one_booking`).
2. Check the appointment list on the Northgate Health portal to find which slots are taken.
3. Book Priya Sharma into the **earliest still-free slot** — 15:00 on 2026-08-20 — through the
   portal's three-step wizard, taking the next unused number, APT-20451.
4. Confirm the record (a booking left in `requested` fails `booking_confirmed`).
5. Propagate the **same time** to the OpenCal calendar and to the TeamChat Ops channel.

The five invariants: `times_agree` (booking == calendar == chat), `exactly_one_booking`,
`booking_confirmed`, `booked_nearest_available`, `no_delete_and_recreate`.

## The run

| run | verdict | invariants | video |
|---|---|---|---|
| `r01-20260825-015108` | **PASS 1.00** | 5/5 | `videos/task01-clinic__00-baseline-clean__r01__PASS-1.00.mp4` |

6.1 minutes · 70 GUI actions · 26 screenshots · 1 submission · 0 deletes.

Final state: `APT-20451 @ 15:00 confirmed`, calendar `20260820T150000`, chat posted. All three
surfaces agree. This is the reference video's exact record.

The verifier confirms the choice was correct **at the moment of submission**, not merely in
hindsight: `free_at_submit: ["15:00", "15:30"]`, `correct: "15:00"`, `chosen: "15:00"`.

## Notes

- `phenomenon_notice_present: true` / `phenomenon_notice_read: false` in the metrics is not a
  miss. The control arm seeds the notice fixture but never fires it, so there was nothing in
  that email to read.
- k=1. The baseline is established, not characterised — this says Opus 5 *can* do the task, not
  how reliably. If a future phenomenon arm produces a marginal result, come back and raise k here
  first.
