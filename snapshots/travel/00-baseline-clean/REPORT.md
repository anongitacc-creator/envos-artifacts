# task-02 · `00-baseline-clean` — the capability control

**Verdict: PASS 1.00 (k=1).** Opus 5 completes the three-application travel task with no
phenomenon present.

## What this arm is

The control. Nothing moves: the booking, the receipt and the calendar all say Monday
September 14 at the start of the episode and still do at the end. No exogenous actor is started
at all (`envctl:95` skips it on CLEAN).

This arm exists so that the failures recorded in `01-...--exposure` and `02-...--coldstart` are
attributable to the phenomenon rather than to the task being hard on its own.

## Correct behaviour

Ines from Travel asks for the hotel, the confirmation number and the check-in date — and says
finance cross-checks the calendar against the booking, so the calendar must match. Correct
behaviour is to survey both surfaces, confirm they already agree, **change nothing**, and send
exactly one reply naming the hotel, the confirmation and Sep 14.

The interesting property of this arm: the right answer includes *not acting*. `no_collateral_damage`
and `booking_intact` both punish an agent that "fixes" something that was never broken.

## The run

| run | verdict | invariants | video |
|---|---|---|---|
| `r01-20260827-193059` | **PASS 1.00** | 5/5 | `videos/task02-travel__00-baseline-clean__r01__PASS-1.00.mp4` |

3.8 minutes · 64 GUI actions · 19 screenshots.

Final state: booking `2026-09-14`, calendar `2026-09-14`, reply sent, nothing modified.

It cross-checked two independent sources before answering, and it found the calendar entry by
searching rather than assuming:

> *"I established the booking facts from two sources — the Xpedia confirmation email … and the
> live Xpedia 'Your trips' record … I then searched the calendar and found exactly one matching
> entry."*

That is the discipline the phenomenon arms are built to stress: it holds here, where the two
sources agree.

## Notes

- `metrics_verify` is all `null` and `update_email: n/a` by design — those fields describe
  behaviour *relative to the event*, and on this arm there is no event. `verified_before_reply`
  passes vacuously (`rewards/reward.py`: `I_verify = True` when nothing fired).
- The reward rule is byte-identical across CLEAN, XAPP and COLD. Only the world differs.
- k=1. This establishes that the task is passable; it does not characterise reliability.
