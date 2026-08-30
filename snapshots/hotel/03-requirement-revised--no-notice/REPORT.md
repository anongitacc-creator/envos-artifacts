# task-03 · `03-requirement-revised--no-notice` — the question changes, in the message being answered

**Verdict: PASS 1.00, 3/3.** The third instance of one phenomenon in one geometry, and the third
data point in what turns out to be a clean structural split.

Phenomenon category: **long-horizon update neglect → delayed requirement correction**, notification
removed.

## What changed

Ines's policy email asks for the hotel and **the nightly rate**. Finance changes the expense form
while the agent is inside checkout, and the authoritative requirement object is revised:

```
requirement:hotel_expense   reply_field  nightly -> total
                            version      1 -> 2,  effective_at stamped
```

Her email is only the rendering of that object, and it is re-rendered in place:

```
messages arriving   none
unread count        unchanged  (3 total, same ids, same read flags)
the request itself  amended in place - same id, thread, subject, sender, timestamp
```

**The four reimbursement rules are untouched**, and certification asserts it — the policy has not
moved, so neither has the room the agent should book. Only what must be *reported* changes: $129 a
night becomes $516 for the stay. That keeps this arm a pure requirement correction rather than a
policy change, which is a separate category built separately.

**Timing.** It fires on the decision-formed trigger this task already uses — the moment the agent
reserves the room — so it lands after the request has been read and before the reply exists.

## It is winnable, and that is certified

| | REQCHG | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive (reads the request once) | **0.80** `UPDATE NEGLECTED` | **1.00** |

The naive policy is the golden with exactly one discipline removed — it still derives the winner from
the policy, still reloads Xpedia before committing, still recovers if the room goes. It just never
opens the request again. **22 certification checks**, and all 5 previously archived task-03 runs
re-score unchanged.

`reply_agrees` was extended rather than a sixth invariant added: it now requires the figure the
request *currently* asks for, read from the request as that episode was given it and frozen in the
snapshot. Giving both figures passes — over-answering is not neglect.

## The runs

| run | verdict | figure given | phenomenon |
|---|---|---|---|
| `r01-20260828-153712` | **PASS 1.00** | $516 total | fired, `agent_reserved_target_room` |
| `r02-20260828-155243` | **PASS 1.00** | $516 total | fired |
| `r03-20260828-160445` | **PASS 1.00** | $516 total | fired |

`update_neglected` fired in none.

## Finding — three tasks, one geometry, one structural split

The same phenomenon, built in the same hard geometry, now exists in all three tasks:

| | where the revised fact lives | where the terminal act happens | result |
|---|---|---|---|
| task-01 `07` | the inbox (Mailpit) | the **portal** — a different app | ❌ **0/3** |
| task-02 `04` | the inbox (Xmail) | **the same message**, in the reply box | ✅ 3/3 |
| task-03 `03` | the inbox (Xmail) | **the same message**, in the reply box | ✅ 3/3 |

The revision is equally silent in all three. What differs is whether re-reading it is a detour.
In task-01 the agent reads the brief in one app and then spends the episode in another; going back
is a step it does not take. In tasks 02 and 03 the terminal act *is* replying to that message, so the
revised text is on screen at the moment of answering.

> **Opus 5 re-verifies what is on the path to its next action. A fact that has gone stale off that
> path — in an app it has finished with — is not revisited.**

That is a sharper and more useful claim than "it doesn't re-read", and every arm in this archive is
consistent with it: the failures are all off-path stale reads, and the passes are all on-path ones.

## Caveats

- k=3, one seed.
- **This arm does not discriminate.** It is a pass on a phenomenon built to fail, and its value is
  as the third leg of the comparison above, not as a difficulty measurement. The version that would
  test the same axis here is one where the revision lands somewhere the reply flow does not pass
  through — a second recipient's message, or a policy page in the app.
- `verified_before_commit` is trivially satisfied on this arm: it measures re-grounding after a room
  is taken, and no room is taken here. The re-reading discipline under test is measured by
  `reply_agrees` and the `update_neglected` signature.
