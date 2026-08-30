# task-01 · `06-delayed-requirement-correction--buried` — the same correction, harder to notice

**Verdict: PASS 1.00, 3/3.** The harder variant did not break it either — but it did move the
diagnostic that measures *how hard it was*.

Built because `05-…` passed 3/3: one further attempt at a legitimately harder geometry before
reporting, rather than accepting the first pass as the answer.

## What differs — salience only

The doc names this as its own axis: *"misses buried update"*, *"position/timing sensitivity"*.

Everything the doc calls **information** is identical to `05-…`: the same state change
(`vaccine: Influenza → Tdap`, `revision 1 → 2`), the same channel, the same trigger, and an email
naming both the new requirement and the one it replaces.

What changes is only how loudly it announces itself:

| | `05` explicit | `06` buried |
|---|---|---|
| subject | `Correction — Priya Sharma vaccination` | `Re: New vaccination request — Priya Sharma` |
| position | opening sentence | third paragraph, after housekeeping |
| company | arrives alone | two routine messages arrive with it |

This is the doc's **observation-equivalence** layer, and certification enforces it rather than
trusting it:

> the email variant must not accidentally reveal the replacement time while the popup only says
> "unavailable", **because then channel is confounded with information content.**

The suite asserts both bodies carry both values, that the state change is identical, and that the
buried subject is an ordinary reply with the correction past character 200.

## The runs

| run | verdict | read it | detection latency |
|---|---|---|---|
| `r01-20260828-075803` | **PASS 1.00** | yes | 226.4 s |
| `r02-20260828-080754` | **PASS 1.00** | yes | 196.8 s |
| `r03-20260828-081709` | **PASS 1.00** | yes | 138.6 s |

Golden 1.00 and the naive policy 0.80 on this arm too, so it is a phenomenon by the same standard.

## Finding — the outcome held, the latency moved

| | mean detection latency |
|---|---|
| `05` explicit | **155 s** |
| `06` buried | **187 s** |

Burying the correction cost about **30 seconds** of detection latency — the doc's *sluggish
adaptation* metric — without changing a single verdict. Every run still found it.

That is worth reporting precisely because task success alone would have thrown it away, which is the
doc's argument for these metrics in the first place:

> Task success alone throws away much of the research value.

Two honest caveats. k=3 against k=3 with one seed is far too small to call a 30 s difference real —
the buried arm's own spread is 139–226 s, wider than the gap between the arms. And the failure mode
this variant targets is one Opus 5 does not appear to have here: it re-read the inbox thoroughly
enough that subject-line salience did not decide the outcome.

**What would actually test this axis** is removing the *prompt* rather than the salience — a
correction with no new message at all, where the requirement changes and only a re-read of an
existing surface reveals it. That is the shape the archive's real failures take, and it is a
different phenomenon from this one.

k=3, one seed.
