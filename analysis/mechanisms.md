# Failing mechanisms, pooled across environments

Pooled control: **11/12 pass (92%)** — clean baselines plus matched cosmetic controls. Two-sided Fisher exact against that control.

| id | mechanism | arms | envs | runs | pass | rate | 95% CI | mean dense | p |
|---|---|---|---|---|---|---|---|---|---|
| **M1** | Selected resource taken by another actor ⚑ | 4 | 2 | 8 | 1 | 12% | [0.02, 0.47] | 0.60 | **0.0008** |
| **M2** | Write accepted, value silently altered | 2 | 2 | 6 | 0 | 0% | [0.00, 0.39] | 0.73 | **0.0004** |
| **M3** | Authoritative fact revised with no notification | 3 | 2 | 9 | 1 | 11% | [0.02, 0.44] | 0.64 | **0.0004** |
| **M4** | World already inconsistent at step 0 | 1 | 1 | 3 | 1 | 33% | [0.06, 0.79] | 0.73 | **0.0813** |
| — | **all four pooled** | 10 | 3 | 26 | 3 | 12% | [0.04, 0.29] | 0.66 | **0.000003** |

⚑ M1 contains two arms whose REPORTs document invariants the phenomenon made unreachable. Reported both ways:

- M1 with those arms: 1/8, p = 0.0008
- M1 without them: 1/6, p = 0.0039

## What each mechanism is

**M1 — Selected resource taken by another actor** (1/8 across 2 environments)

The slot or room the agent chose is booked by someone else mid-episode. Implemented in two environments and compounded three different ways (email notice; then a permission revocation; then an accept-then-void).

Arms: `01/01-slot-taken--email`, `03/01-slot-taken--email`, `01/03-slot-taken--permission-revoked`, `03/02-slot-taken--void`

**M2 — Write accepted, value silently altered** (0/6 across 2 environments)

The commit succeeds and the store keeps a different value. No error, no banner; the confirmation surface renders what was chosen.

Arms: `01/17-write-coerced--post-commit`, `03/05-write-coerced--room-substituted`

**M3 — Authoritative fact revised with no notification** (1/9 across 2 environments)

A requirement, an identity or a rule is changed in place. Nothing arrives; nothing becomes unread; the surface holding the truth looks unchanged.

Arms: `01/07-requirement-revised--no-notice`, `01/09-patient-records-merged--no-notice`, `03/04-policy-reissued--wrong-summary`

**M4 — World already inconsistent at step 0** (1/3 across 1 environment)

The cross-app commit fired before the agent's first action, so there is no temporal cue to attach the inconsistency to.

Arms: `02/02-partial-xapp-commit--coldstart`
