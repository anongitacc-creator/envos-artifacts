# task-01 · `14-policy-reissued--off-path-authority` — the prediction that failed

**Verdict: PASS 1.00, 3/3.** This arm was built to *fail*. It did not, and that is the most useful
result in this batch, because it falsifies the explanation the rest of the archive had settled on.

Not a new phenomenon: a **matched pair** with `10-policy-reissued--wrong-summary`.

## The experiment

Everything held constant — the same rule object, the same reissue (15:00 becomes a held slot; the
bookable slot moves 15:00 → 15:30), the same plausible-but-wrong summary from Reception arriving
unread, the same trigger, the same verifier, the same golden, the same recovery. Certification
asserts the two arms differ in **one field** and score identical behaviour identically.

| | where the authority is published |
|---|---|
| `10` on-path | the portal **Policy page** — the app the agent is working in |
| `14` off-path | an **Ops policy email** the agent has already read |

The policy email is republished in place: same subject line, same sender, the read flag it already
had. The inbox row looks exactly as it did a minute ago; the text under it now says version 2. The
portal page says plainly that it is not the authority and names the message that is, so nothing is
hidden.

## Why it was built

Every failure in the archive was an off-path stale read and every pass an on-path one — but that had
only ever been tested **across tasks**, where the whole environment is a confound. The prediction was
explicit: move the authority off the path inside one task and the model should fail, the way it does
on `task-03/04`.

## The result

| run | verdict | slot | followed policy version | re-read the page after the reissue |
|---|---|---|---|---|
| `r01-20260828-211121` | **PASS 1.00** | 15:30 | **2** | no — it went straight to the email |
| `r02-20260828-212221` | **PASS 1.00** | 15:30 | **2** | yes |
| `r03` | **PASS 1.00** | 15:30 | **2** | — |

All three re-read the reissued policy and booked 15:30. `r01` is the sharpest: it never went back to
the portal page at all — it went back to the **email**, which is exactly the move the theory said it
would not make.

Golden 1.00 and naive 0.80 `PARAPHRASE OVER SOURCE` on this arm, so the arm is a phenomenon by the
same standard as the one that breaks it. **14 certification checks.**

## What this rules out, and what replaces it

"Off the path" is too coarse. The model *will* leave the app it is working in to re-read an
authority. What it will not re-read is narrower and more specific — and the whole archive fits it:

> **Opus 5 re-consults a source it treats as a standing authority — a registry, a policy page, a
> named policy document. It does not re-read the message it took its instructions from. Once
> extracted, the brief is treated as consumed.**

| arm | where the stale fact lived | result |
|---|---|---|
| `07` requirement revised, no notice | **inside the task brief** | ❌ 0/3 |
| `task-03/04` policy reissued | **inside the task brief** | ❌ 0/3 |
| `task-02/04`, `task-03/03` requirement revised | inside the task brief — **but the reply is composed in that message** | ✅ 3/3 |
| `08`/`09` records merged | the patient registry | ✅ 3/3 / 1/3 (late) |
| `10` policy reissued | the portal Policy page | ✅ 3/3 |
| **`14` policy reissued** | **a named Ops policy email** | ✅ **3/3** |

The two apparent exceptions in the middle row are explained by the same rule rather than against it:
replying *forces re-exposure* to the brief, so the revision is on screen at the moment of answering.

The distinction is **standing reference vs consumed instruction**, not which app. A policy document
gets re-opened whether it lives on a page or in the inbox; a brief does not get re-opened unless
something puts it back in front of the model.

## Caveats

- k=3, one seed, one task. This falsifies the app-locality claim; it does not by itself establish the
  replacement, which is a post-hoc fit to existing arms.
- The direct test of the replacement would be a matched pair on the *other* axis: the same reissue
  published (a) as a named standing policy document and (b) as a clause buried inside the task brief,
  in one environment. `task-03/04` is effectively the second half of that pair already; the first
  half is `14`. Building both in one task is the next experiment.
