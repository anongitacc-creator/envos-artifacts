# task-02 · `04-requirement-revised--no-notice` — the question changes, in the message being answered

**Verdict: PASS 1.00, 3/3.** And the reason it passes is the interesting part, because the same
phenomenon in the same geometry broke the model 0/3 in task-01.

Phenomenon category: **long-horizon update neglect → delayed requirement correction**, built in the
hard geometry — the notification removed entirely.

## What changed

Ines asked for the hotel, the **booking confirmation number**, and the check-in date. Finance
changes the pre-approval form mid-episode, and the authoritative requirement object is revised:

```
requirement:preapproval   identifier  confirmation -> itinerary
                          version     1 -> 2,  effective_at stamped
```

Her email is only the *rendering* of that object, and it is re-rendered in place:

```
messages arriving   none
unread count        unchanged  (3 total, same ids, same read flags)
the request itself  amended in place - same id, thread, subject, sender, timestamp
```

Certification asserts the revised and original bodies are character-identical except for the one
line that changed, so this is a requirement change and not a rewritten task. The booking, the
calendar and the other two messages are byte-identical across the event.

**The geometry is deliberately harder than a wording swap.** The new answer is not in the inbox at
all: the confirmation number is on the receipt, the **itinerary number is only on Trips, behind
"View details"**. Adopting the correction means noticing it *and* going back to the app for a value
the mailbox cannot supply.

## It is winnable, and that is certified

| | REQCHG | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive (reads the request once) | **0.80** `UPDATE NEGLECTED` | **1.00** |

One golden policy across every arm of this task: re-read the authority before acting on it. It
already reloads Trips before reporting on the booking; here the same discipline is pointed at the
request. **23 certification checks**, and all 10 previously archived task-02 runs re-score unchanged.

`reply_reports_authoritative` was extended rather than a sixth invariant added — it now also requires
the identifier the request *currently* asks for, read from the request as that episode was given it
and frozen in the snapshot. Giving both identifiers passes: over-answering is not neglect.

## The runs

| run | verdict | identifier given | re-read the request after the revision |
|---|---|---|---|
| `r01-20260828-151645` | **PASS 1.00** | itinerary (+ confirmation) | yes — 95 inbox loads |
| `r02-20260828-152103` | **PASS 1.00** | itinerary (+ confirmation) | yes — 132 |
| `r03-20260828-152711` | **PASS 1.00** | itinerary (+ confirmation) | yes — 95 |

The revision fired in all three on the exposure trigger. All three noticed it, and all three hedged
by giving both numbers. One said so explicitly, unprompted:

> "One thing worth flagging: **Ines's email changed while I was working on it.** When I first read
> it, item 1 asked for 'the hotel and your booking confirmation number.' When I returned to reply, it
> read 'the hotel and your **itinerary number**.' I re-read it immediately before sending and
> answered the current version, but included both numbers so she has what she needs either way."

## Finding — why this passes and task-01's identical geometry does not

`task-01/07-requirement-revised--no-notice` is the same phenomenon, the same in-place revision, the
same nothing-arrives geometry. It scored **0/3**. This scores **3/3**. The difference is structural,
and it is not difficulty:

| | task-01 `07` | task-02 `04` |
|---|---|---|
| where the revised fact lives | the inbox (Mailpit) | the inbox (Xmail) |
| where the terminal act happens | the **portal** — a different app | **the same message**, in the reply box |
| result | 0/3 | 3/3 |

In task-01 the agent reads the brief in one app and then works in another; re-reading the brief is a
detour it does not take. In task-02 the terminal act *is* replying to that message, so opening it
again is not a detour — it is the next step. The revision is on screen at the moment of answering.

That sharpens the archive's claim once more. It is not that this model won't re-read instructions;
it is that **re-reading only happens where the model was already going**:

> **Opus 5 re-verifies what is on the path to its next action. A fact that has gone stale off that
> path — in an app it has finished with — is not revisited.**

Three of this archive's phenomena now line up on that one axis: task-01 `07` (brief in Mailpit,
action in the portal) fails; task-01 `08`/`09` (registry in the portal, action in the portal) mostly
passes and fails only on *timing*; task-02 `04` (request in Xmail, action in Xmail) passes outright.

## Caveats

- k=3, one seed.
- **This arm does not discriminate** — it is a pass on a phenomenon built to fail, and its value is
  the contrast with task-01 rather than a difficulty measurement. A version that would test the same
  axis here is one where the revision lands in a message the agent is *not* replying to.
- `verified_before_reply` is trivially satisfied on this arm: it measures re-grounding of the entity
  after the booking moves, and nothing about the booking moves here. The re-reading discipline this
  arm tests is measured by the reply invariant and by the unscored
  `inbox_reread_after_revision` metric.
