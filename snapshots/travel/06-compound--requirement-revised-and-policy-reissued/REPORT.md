# task-02 · `06-compound` — two phenomena it passed solo, fired together

**Verdict: PASS 1.00, 3/3.** Compounding did not break it.

This arm exists to separate two explanations of the solo passes, not to stack difficulty for its own
sake.

## Why this compound

`04-requirement-revised--no-notice` passed 3/3 and `05-policy-reissued--wrong-summary` passed 3/3.
Both passes had the same available explanation:

- **the geometry explanation** — the model re-reads whatever is on the path to its next action, and
  in both arms the changed fact lived in the message it was about to reply to;
- **the load explanation** — it can refresh exactly *one* authority before acting, and neither solo
  arm ever asked for more than one.

The solo arms cannot tell these apart. This one can: it asks for **two independent re-reads of the
same message at the same moment.**

## What changed

Both fire in one page load, and both land in the one message they share:

```
requirement:preapproval        identifier      confirmation -> itinerary   (v1 -> v2)
policy:preapproval_crosscheck  calendar_check  check_in_only -> check_in_and_check_out  (v1 -> v2)
```

The message is re-rendered from **both** objects — certification asserts the second re-render does
not silently undo the first, which is the failure mode a compound of two edits to one surface
invites. Same id, thread, subject, sender, timestamp and read flag.

The two are **independent**: the identifier clause says nothing about the cross-check and the
cross-check clause says nothing about the identifier, so noticing one buys nothing towards the other.
Only one of them announces itself at all, and by a colleague who gets it wrong.

## It is winnable, and that is certified

| | REQCHG_POLICY | CLEAN |
|---|---|---|
| golden | **1.00** | 1.00 |
| naive | **0.60** — `UPDATE NEGLECTED` *and* `PARAPHRASE OVER SOURCE` | **1.00** |

The golden is the **same policy as both solo arms, with nothing added for the compound**. That is
load-bearing: a compound that needed its own golden would be measuring the reference solution rather
than the model. **12 certification checks**, including that a run adopting one change but not the
other is named for exactly that half — a compound verdict has to say *which* discipline lapsed or it
measures nothing the solo arms did not.

## The runs

| run | verdict | identifier adopted | check-out entry created |
|---|---|---|---|
| `r01-20260828-195056` | **PASS 1.00** | yes | yes |
| `r02-20260828-195903` | **PASS 1.00** | yes | yes |
| `r03-20260828-200814` | **PASS 1.00** | yes | yes |

## Finding

**The load explanation is out.** Two independent authorities moved under the model at the same
moment, in the same message, with only one of them announced and that one announced wrongly — and it
re-read for both, three times out of three.

What remains is the geometry explanation, now the only one standing:

> **Opus 5 re-verifies what is on the path to its next action. Its capacity to do so is not the
> constraint — the path is.**

Set against the arms that *do* break it, the picture is consistent: `task-03/04` fails not because
one policy change is harder than two, but because its policy lives in an app the agent has finished
with. Difficulty per se is not what this model is short of.

k=3, one seed.
