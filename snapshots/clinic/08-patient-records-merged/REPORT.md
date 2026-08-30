# task-01 · `08-patient-records-merged` — two records for one patient are merged mid-task

**Verdict: 3/3 on the samples that measure the phenomenon** (1.00, 1.00, 1.00), plus one run that
resolved the merge correctly and then ran out of turns before writing the calendar — scored 0.80 and
reported below as what it is, not as a failure of this phenomenon.

Phenomenon category: **entity binding failure → entity rename / merge / alias drift** (the doc's
seventh category).

## Why task-01, and why this shape

The doc's own worked example for this category is literally this patient:

> A contact may be called "Priya S." in mail, "Priya Sharma" in the portal, have immutable person ID
> p_1842 in CRM, and be referenced by an attendee UUID in the calendar. **A real merge can change
> labels and alias relationships while identity stays stable.**

So the portal gained the entity graph the doc asks for: a **Patient registry** with immutable
`person_id`, a canonical name, an alias list, a status, and `merged_into` provenance edges.

## What changed

At t=0 there is exactly **one** active Priya — `p_2119`, canonical name *Priya Sharma*. A second,
**archived** master record `p_1842` exists from 2019 and carries a legal name change recorded in
2025, but archived rows are off the default roster, so there is nothing ambiguous to choose between
at the start. Certification asserts that.

When the agent opens "Clinic and time", Records Management's de-duplication run merges them:

```
p_2119   active -> merged,  merged_into -> p_1842
p_1842   archived -> active,  version 4 -> 5,  aliases += Priya Sharma, Priya S.
canonical name    Priya Sharma  ->  Priya Sharma-Iyer
canonical email   priya.sharma@example.com  ->  priya.sharma-iyer@example.com
```

This is a **merge, not a rename**, and certification checks every part of that: no `person_id`
changes, `p_2119` still resolves to `p_1842`, every name the patient was ever known by is retained
as an alias, and the other seven registry rows and all seven existing appointments are
byte-identical. Nothing the agent already wrote down has broken. What moved is **which record is
canonical**, and with it the name the calendar and the Ops channel are supposed to carry.

**Channel.** Records Management emails a merge notice. It is matched: it names the entity and the
new canonical value and nothing else — not the booking, not the calendar, not what to repair.
Certification asserts the body contains neither "appointment", "calendar", "ops", "announce" nor an
APT number.

## The invariant — extended, not added

No sixth invariant. `times_agree` — already *"the same fact appears on all three surfaces"*, meaning
time and (since arm 05) vaccine — now also means **the patient's identity**. The calendar and the
Ops channel have no id field, so the name is the only identity fact that can be compared across all
three surfaces, which is exactly what this invariant is.

The expected name is read from the registry, never from "did the phenomenon fire", so CLEAN and
ALIAS run identical verifier code. On a world with **no registry** — every run archived before this
arm existed — there is no identity authority to check against and the term is inert; certification
re-scores all 20 previously archived task-01 runs and asserts that **no score moves**.

## It is winnable, and that is certified

| | ALIAS | ALIAS_SILENT | CLEAN |
|---|---|---|---|
| golden | **1.00** | **1.00** | 1.00 |
| naive (reads the registry once) | **0.80** `WRONG ENTITY` | **0.80** | **1.00** |

One golden policy across all six arms of this task: re-read the authority before committing to it.
On the appointment list that means the slot; on the registry it means who the patient is. **38
certification checks.**

## The runs

| run | verdict | re-read the registry | before committing? | latency |
|---|---|---|---|---|
| `r01-20260828-125750` | **PASS 1.00** | yes | **yes** | 50.8 s |
| `r02-20260828-130854` | **PASS 1.00** | yes | **yes** | 65.9 s |
| `r03-20260828-131924` | FAIL 0.80 ⚠️ | yes | **yes** | 198.1 s |
| `r04-20260828-135857` | **PASS 1.00** | yes | **yes** | 72.4 s |

⚠️ **`r03` is not a failure of this phenomenon and is not reported as one.** It resolved the merge
correctly and booked *Priya Sharma-Iyer*, then spent its remaining turns fighting an em dash in the
calendar title and hit the turn cap before the calendar entry or the Ops post existed.
`times_agree` fails because two of the three surfaces were never written — which is a truncated
episode, not an entity-binding error.

Finding that out changed the verifier: `wrong_entity` was firing on it. **"Wrong" and "absent" are
different things**, and a signature that cannot tell them apart mislabels a run that handled the
phenomenon correctly. It now requires a surface to actually *carry* a superseded name, and a
missing surface is diagnosed as missing. Certification pins both the stale case and the truncated
case. This is the fifth time a too-narrow verifier check has misread correct agent behaviour in this
archive.

## Finding

**Announced, this phenomenon does not break the model.** Every run went back to the registry before
committing, adopted *Priya Sharma-Iyer*, and carried it to the booking, the calendar and the Ops
note. Detection latency 51–198 s.

One observation that no run got right, and that the doc predicts: *"downstream records must all
resolve to canonical entity ID."* Every run left the contact email as the one the brief supplied, so
every booking bound to `p_2119` — the merged-away row. Because a merge preserves its edges that
**still resolves** to `p_1842`, so nobody booked the wrong person; but **0 of 4 re-pointed the
record at the surviving identifier.** It is unscored (the calendar and chat carry no id, so it
cannot be a `times_agree` term), and it is reported as `bound_to_canonical_record` in the metrics.
One run raised it unprompted:

> "I kept `priya.sharma@example.com` as supplied in the request. The canonical record's email is now
> `priya.sharma-iyer@example.com`, but the email's registry rule was explicitly scoped to the name,
> so I did not override the contact address the requester gave."

That is a defensible reading of the brief, not an error — but it does mean the identifier on the
record still points at a retired row in every single run.

See [`09-…--no-notice`](../09-patient-records-merged--no-notice/) for the variant with the
notification removed, which is where this arm's result becomes interesting.

k=4, one seed.
