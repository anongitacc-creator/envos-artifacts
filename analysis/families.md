# Phenomenon families vs the pooled control

Pooled control condition: **11/12 pass** (clean baselines + matched cosmetic controls). Each family is the pooled outcome of every arm implementing that mechanism, across however many independent environments it was built in. Two-sided Fisher exact against the control.

| family | arms | envs | runs | pass | rate | 95% CI | mean dense | p vs control |
|---|---|---|---|---|---|---|---|---|
| `resource_contention` ⚑ | 1 | 2 (01,03) | 2 | 0 | 0% | [0.00, 0.66] | 0.50 | **0.0330** |
| `commitment_durability` | 1 | 1 (03) | 3 | 1 | 33% | [0.06, 0.79] | 0.60 | 0.0813 |
| `false_success` | 3 | 2 (01,03) | 13 | 7 | 54% | [0.29, 0.77] | 0.88 | 0.0730 |
| `entity_binding` | 2 | 1 (01) | 7 | 4 | 57% | [0.25, 0.84] | 0.91 | 0.1174 |
| `cross_app_invariant` | 2 | 1 (02) | 5 | 3 | 60% | [0.23, 0.88] | 0.84 | 0.1912 |
| `permission_reasoning` | 3 | 2 (01,02) | 9 | 6 | 67% | [0.35, 0.88] | 0.89 | 0.2722 |
| `tool_adaptation` | 1 | 1 (01) | 3 | 2 | 67% | [0.21, 0.94] | 0.93 | 0.3714 |
| `constraint_hierarchy` | 4 | 3 (01,02,03) | 12 | 9 | 75% | [0.47, 0.91] | 0.83 | 0.5901 |
| `long_horizon_update_neglect` | 5 | 3 (01,02,03) | 15 | 12 | 80% | [0.55, 0.93] | 0.95 | 0.6051 |
| `compound (multiple families)` | 3 | 2 (01,02) | 9 | 9 | 100% | [0.70, 1.00] | 1.00 | 1.0000 |
| `uncertain_action_outcome` | 1 | 1 (01) | 3 | 3 | 100% | [0.44, 1.00] | 1.00 | 1.0000 |

⚑ = contains an arm whose REPORT documents invariants the phenomenon made unreachable; the family is still informative but the confound must be stated wherever the number is used.

## Families that significantly degrade the agent

- **`resource_contention`** — 0/2 across 1 arms in 2 environment(s), p = 0.0330