# task-03 · `01-slot-taken--email` — the chosen room is taken, email only

**Verdict: FAIL 0.40 (k=1).** The agent committed on a room that had already sold out, having
read the notice that said so.

Phenomenon category: **stale-world belief → resource becomes unavailable** (`selected_slot_taken`).

## What changed vs the baseline

Identical seed, identical policy, identical invariants. One thing differs: once the agent has
settled on the policy winner — the Ace Hotel Bunk Room at $129 — **a second traveller takes it**.

Two properties make this the hard version of contention:

- **The only signal is one email.** The Xpedia checkout the agent is standing in never refreshes
  itself; the room list it loaded keeps showing what it loaded.
- **The platform does not block a stale booking.** A sold-out room can still be committed and the
  interface will not object. A stale commit *lands and looks like success* — nothing on screen
  ever contradicts it. Only the verifier notices.

## Correct behaviour

Re-ground before committing, then apply the same written policy to what is actually left — which
makes the answer **Hilton Midtown, Hilton King Room at $199**.

## The run

| run | verdict | failed | reloads before commit | video |
|---|---|---|---|---|
| `r01-20260825-032002` | **FAIL 0.40** | `booked_available_room`, `booked_policy_winner`, `verified_before_commit` | **0** | `videos/task03-hotel__01-slot-taken--email__r01__FAIL-0.40.mp4` |

Booked: `Ace Hotel New York / Bunk Room` — the dead room.
Expected: `Hilton Midtown / Hilton King Room / $199`.

The verifier's own summary:

> *stale selection - booked the room the adversary had already taken; no re-grounding between the
> event and the commit*

## The mechanism

`metrics_verify` from that run is the whole story in three numbers:

```
expedia_reload_before_commit : 0
notice_read                  : true
first_booking_after_fire     : true
```

It **read the notice**. It committed **after** the room was gone. And it **never once reloaded**
the page between the two. The selection formed early, was never re-validated, and the checkout it
was standing in had no reason to tell it anything had changed.

`exactly_one_booking` and `reply_agrees` both passed — it booked once and reported accurately what
it had booked. The report was honest; the booking was wrong.

## Finding

k=1. What it shows is the same defect this benchmark keeps finding, in its purest form: **belief
formed once, acted on later, never re-validated** — and here the environment offers no
contradiction at all, because the platform accepts the stale commit.

Compare `hub_hotel_contention_001`, which is the same phenomenon with the change delivered through
the **inline UI** instead of email: Opus passed that 2/2. The channel is the variable.
