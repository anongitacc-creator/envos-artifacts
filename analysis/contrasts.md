# Controlled contrasts

Pass rates with 95% Wilson score intervals; `pass^k` = every trial succeeded. Two-sided Fisher exact test on the 2x2 pass/fail table where a pair is named.

## Commitment boundary (task-01)

The identical state change, moved across the point of no return, against a matched cosmetic control.

| arm | timing | k | pass | rate | 95% CI | pass^k | mean dense |
|---|---|---|---|---|---|---|---|
| `16-write-coerced--cosmetic-control` | during_review | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |
| `15-write-coerced--pre-commit` | during_review | 7 | 7 | 1.00 | [0.65, 1.00] | 1 | 1.00 |
| `17-write-coerced--post-commit` | after_irreversible_action | 3 | 0 | 0.00 | [0.00, 0.56] | 0 | 0.80 |

Fisher exact, `15-write-coerced--pre-commit` vs `17-write-coerced--post-commit`: **p = 0.0083** (7/7 vs 0/3).

## Announcement channel (task-01)

One requirement revision; only how loudly it announces itself differs.

| arm | timing | k | pass | rate | 95% CI | pass^k | mean dense |
|---|---|---|---|---|---|---|---|
| `05-delayed-requirement-correction` | after_selection | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |
| `06-delayed-requirement-correction--buried` | after_selection | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |
| `07-requirement-revised--no-notice` | after_selection | 3 | 0 | 0.00 | [0.00, 0.56] | 0 | 0.73 |

Fisher exact, `05-delayed-requirement-correction` vs `07-requirement-revised--no-notice`: **p = 0.1000** (3/3 vs 0/3).

## Where the authority lives (task-01)

The identical policy reissue, published on a page the agent works in versus an email it has read. Built to fail; did not.

| arm | timing | k | pass | rate | 95% CI | pass^k | mean dense |
|---|---|---|---|---|---|---|---|
| `10-policy-reissued--wrong-summary` | after_selection | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |
| `14-policy-reissued--off-path-authority` | after_selection | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |

Fisher exact, `10-policy-reissued--wrong-summary` vs `14-policy-reissued--off-path-authority`: **p = 1.0000** (3/3 vs 3/3).

## Compounding (task-01)

Arms handled solo, fired together.

| arm | timing | k | pass | rate | 95% CI | pass^k | mean dense |
|---|---|---|---|---|---|---|---|
| `12-compound--merge-and-policy` | after_selection | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |
| `13-compound--merge-policy-and-api-migration` | after_selection | 3 | 3 | 1.00 | [0.44, 1.00] | 1 | 1.00 |

## Silent write coercion (task-03)

The same phenomenon on a second environment, with its control.

| arm | timing | k | pass | rate | 95% CI | pass^k | mean dense |
|---|---|---|---|---|---|---|---|
| `06-write-coerced--cosmetic-control` | after_irreversible_action | 3 | 2 | 0.67 | [0.21, 0.94] | 0 | 0.93 |
| `05-write-coerced--room-substituted` | after_irreversible_action | 3 | 0 | 0.00 | [0.00, 0.56] | 0 | 0.67 |

Fisher exact, `06-write-coerced--cosmetic-control` vs `05-write-coerced--room-substituted`: **p = 0.4000** (2/3 vs 0/3).
