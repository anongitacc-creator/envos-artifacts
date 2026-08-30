# Does injection break the agent? The pooled test

Arm-by-arm contrasts at k=3 cannot reach significance - a perfect separation gives Fisher p=0.10. But the claim under test is about **injection as a method**, and that claim pools. Two arms excluded and reported separately: those whose own REPORT states that the phenomenon made an invariant unreachable, so they partly score the environment.

## 1. Task success

| condition | runs | pass | rate | 95% CI |
|---|---|---|---|---|
| **control** (clean + matched cosmetic) | 12 | 11 | 0.92 | [0.65, 0.99] |
| **injected phenomenon** | 79 | 56 | 0.71 | [0.60, 0.80] |

Two-sided Fisher exact: **p = 0.17193**  (absolute drop 21 percentage points).

## 2. Dense reward

The benchmark scores `passes/5`, so thresholding to pass/fail throws away four fifths of the signal. Mann-Whitney U on the graded score keeps it.

| condition | n | mean | median |
|---|---|---|---|
| control | 12 | 0.983 | 1.00 |
| injected | 79 | 0.896 | 1.00 |

U = 578, z = 1.58, **p = 0.11448**, rank-biserial r = 0.22.

## Excluded (arms that partly score the environment)

2 runs across 2 arms, 0 pass. Their REPORTs document invariants the phenomenon made unreachable; including them would inflate the effect.

## 3. Where the effect lives - by phenomenon family

The pooled number must never be quoted without this. Injection is not uniformly harmful; the families differ sharply, and that difference is the actual finding.

| family | arms | runs | pass rate |
|---|---|---|---|
| `commitment_durability` | 1 | 3 | 1/3 (33%) |
| `false_success` | 3 | 13 | 7/13 (54%) |
| `entity_binding` | 2 | 7 | 4/7 (57%) |
| `cross_app_invariant` | 2 | 5 | 3/5 (60%) |
| `permission_reasoning` | 3 | 9 | 6/9 (67%) |
| `tool_adaptation` | 1 | 3 | 2/3 (67%) |
| `constraint_hierarchy` | 4 | 12 | 9/12 (75%) |
| `long_horizon_update_neglect` | 5 | 15 | 12/15 (80%) |
| `uncertain_action_outcome` | 1 | 3 | 3/3 (100%) |
| `entity_binding + constraint_hierarchy` | 1 | 3 | 3/3 (100%) |
| `entity_binding + constraint_hierarchy + tool_adaptation` | 1 | 3 | 3/3 (100%) |
| `long_horizon_update_neglect + constraint_hierarchy` | 1 | 3 | 3/3 (100%) |

## 4. Yield of the taxonomy

Of the phenomena built from the proposal's categories, how many actually break the agent:

- **5 of 25 arms fail at every trial** (20%)
- 5 are unreliable (some trials fail) (20%)
- 15 are handled at every trial (60%)

So **40% of injected phenomena degrade the agent at least sometimes**, against a control condition at 11/12.

### Arms that never pass

- `01/03-slot-taken--permission-revoked` - permission_reasoning · 0/3 · mean dense 0.667
- `01/07-requirement-revised--no-notice` - long_horizon_update_neglect · 0/3 · mean dense 0.733
- `01/17-write-coerced--post-commit` - false_success · 0/3 · mean dense 0.8
- `03/04-policy-reissued--wrong-summary` - constraint_hierarchy · 0/3 · mean dense 0.333
- `03/05-write-coerced--room-substituted` - false_success · 0/3 · mean dense 0.667

### Arms that are unreliable

- `01/08-patient-records-merged` - 3/4
- `01/09-patient-records-merged--no-notice` - 1/3
- `01/11-calendar-api-migrated` - 2/3
- `02/02-partial-xapp-commit--coldstart` - 1/3
- `03/02-slot-taken--void` - 1/3

## Caveat that must ship with these numbers

The arms are **not a random sample of possible phenomena**. They were built from a fixed taxonomy, and several were iterated after an early version passed. The pooled figure is therefore a statement about *the yield of this taxonomy under deliberate search*, not about phenomena in general - which is what the proposal asks for, and is how it should be worded.
