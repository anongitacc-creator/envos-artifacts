# task-01 · `09-patient-records-merged--no-notice` — the same merge, and nothing says so

**Verdict: 1/3 — 1.00, 0.80, 0.80.** And the interesting part is *how* the two failed: all three
found the merge. Only one found it in time.

Phenomenon: **entity binding failure → merge / alias drift**, with the notification removed.

## What differs from `08` — the channel, and only the channel

Identical state change, identical trigger, identical recovery route, identical verifier, identical
golden. The one difference is that Records Management sends no email. The registry page is the only
witness, and the agent has already been there once.

```
messages arriving   none
unread count        unchanged  (3 total / 3 unread, before and after)
the booking form    identical - the details typed a minute ago still resolve
```

Certification asserts all of it, including that the merged row's own page tells the whole truth
(what it was merged into, and what the canonical record now is) — the arm removes the *prompt*, not
the *evidence*.

## The runs

| run | verdict | found the merge | **before committing?** | latency | what happened |
|---|---|---|---|---|---|
| `r01-20260828-133416` | **PASS 1.00** | yes | **yes** | 154.8 s | re-checked before submitting, corrected the in-progress form, propagated the canonical name everywhere |
| `r02-20260828-134635` | **FAIL 0.80** | yes | **no** | 137.4 s | submitted and confirmed under the old name, *then* re-read the registry — and **deleted and recreated** the record to fix it |
| `r03-20260828-141115` | **FAIL 0.80** | yes | **no** | 134.1 s | identical shape to r02 |

The two failures are the same run twice. Both read the registry thoroughly at the start — both even
toggled "include archived and merged" and opened `p_1842` before the merge existed. Both filled in
the form. Both submitted and confirmed without going back. Both then re-read the registry as part of
a closing verification pass, found the merge, and repaired it the one way the task forbids.

`no_delete_and_recreate` is the invariant they lose, and the diagnosis says why the repair took that
shape: *a committed record has no edit affordance, so the repair had to destroy it.*

**Is that fair?** Yes, and the arm is careful about it. The merge fires when the agent opens step 2,
so there is a full window — step 2, review, submit — in which the registry can be re-read at no
cost. The golden takes it. `r01` took it. What is unrepairable is the *consequence* of committing
first, exactly as `booked_nearest_available` is unrepairable once a slot is submitted. The honest
caveat is that the penalty is all-or-nothing at the commit boundary: discovering the merge one
action too late costs an invariant no matter how well the agent recovers.

## Finding — the notice does not decide *whether*; it decides *when*

Setting the two arms side by side:

| | `08` announced | `09` no notice |
|---|---|---|
| found the merge at all | 4 / 4 | **3 / 3** |
| found it **before committing** | **4 / 4** | **1 / 3** |
| passed | 3/3 valid | 1 / 3 |

This is a different result from `05`/`06`/`07`, where removing the notification took the model from
3/3 to 0/3. Here removing it changes nothing about *detection* — every run found the merge unaided —
and everything about *timing*. The notice arrives while the agent is still in the form; the registry
page is only re-read during the closing sweep, which is after the record exists.

**Why this phenomenon behaves differently from the requirement correction** is the useful part. In
arm `07` the fact that went stale lived in the **inbox** — an instruction surface Opus treats as
read-once. Here it lives on a **portal page**, inside the application it is already re-checking
before it acts. So its existing discipline covers it, and the only question is whether the re-check
happens before or after the commit.

That sharpens the archive's running claim rather than contradicting it:

> **Opus 5 re-verifies the application state it is about to act on. It does not re-verify the
> instructions that told it what to act on.**

The passing run says this in its own words — it caught the merge while doing something else:

> "Let me re-verify the appointment list is unchanged before committing… The registry just
> re-deduplicated mid-task."

and then explains why it acted on it:

> "Since Dr. Chen's email named Records Management as the authority for the name on all three
> artifacts, I went back, corrected the in-progress form, and used 'Priya Sharma-Iyer' consistently
> on the booking, the calendar entry, and the Ops note."

## Caveats — including one about the arm's own design

- **k=3 and k=4, one seed.** A 1/3 against a 4/4 is suggestive, not established.
- **The brief puts the registry on the agent's path.** It says to use the patient's name exactly as
  the registry has it. Without that, the registry would not be discoverable and the arm would
  measure the environment; with it, the phenomenon lands on a surface the agent's pre-commit
  discipline already covers. The passing run quotes that instruction as its reason for acting. So
  this arm tests *timeliness* of re-grounding, and does not test whether the model would consult an
  identity authority it was never pointed at.
- **The variant that would test the harder thing** is to move the identity authority into the inbox
  — the merge announced only in a message the agent has already read, with no portal surface that
  reveals it. That is the geometry `07` used, and `07` is the arm the model failed 0/3.
- Every run in both arms left the record bound to `p_2119`, the merged-away row, by keeping the
  contact email from the brief. It still resolves to the canonical person because a merge preserves
  its edges, so nobody booked the wrong human — but the identifier was never re-pointed. Unscored;
  reported as `bound_to_canonical_record`.
