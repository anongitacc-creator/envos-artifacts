# EnvOS — released artifacts

This repository accompanies the paper *EnvOS: Certified Evaluation of Enterprise
Agents in Changing Environments*. It contains the three evaluation environments,
their certification suites, the frozen per-rollout snapshots, and the analysis
scripts — everything needed to inspect the environments, re-run certification,
and reproduce every number and figure in the paper from the archived rollouts,
without any model calls.

The evaluated corpus is 32 variants and 93 rollouts on Claude Opus 5 through
Claude Code across three multi-application enterprise workflows (clinic
scheduling, travel reconciliation, hotel booking). The four certification layers
comprise 389 executable assertions in 19 suites (Clinic 203, Travel 97,
Hotel 89). Four recurring phenomenon families are studied — *Contested
Resource*, *Ghost Commit*, *Mandate Drift*, and *Cold-Start Inconsistency* —
with nine checker signatures grouped under them.

Not included: raw screen recordings, per-step screenshots, agent transcripts,
the harness working directories, other candidate tasks, and manuscript drafts.

```
environments/   the three environments and their certification suites
snapshots/      frozen state + verdicts for all 93 archived rollouts
analysis/       CSVs, paper_stats.json, and the scripts that build them
LICENSE         MIT
```

## environments/

| Dir | Paper name | Composition |
|---|---|---|
| `clinic/` | Clinic | 3 applications we author + Mailpit (a real mail server) |
| `hotel/`  | Hotel  | 2 stock CUA-Gym Hub mocks via a re-grounding proxy |
| `travel/` | Travel | 3 stock CUA-Gym Hub mocks via a re-grounding proxy |

Each environment ships:

- `initial_setup.py` — builds the seed state `s_0`
- `golden_patch.py` — the reference policy `π★` (feasibility witness; used across
  all variants)
- `naive_patch.py` — the deficient policy `π⁻` (`π★` with one discipline removed)
- `reward.py` — the verifier: five state-based invariants, dense reward, and
  failure signatures
- `tests/` (clinic, hotel) or `certification/` (travel) — the executable
  certification suite; 389 assertions in 19 suites across the three environments
  (Clinic 203 in 9, Travel 97 in 5, Hotel 89 in 5)
- `run_env.sh` / `envctl` — seed, run the reference/deficient policies, run
  certification (`golden` / `naive` / `test`), score (`verify`)
- `run_agent.sh` — the exact non-interactive `claude` invocation used for
  rollouts (`--allowedTools Bash Read`, isolated working directory); under
  `agent/` in the travel environment
- `apps/` (clinic), `world/` (hotel), `hub/` + `environment/` (travel) —
  application code and seed data
- `README.md` — per-environment notes

`run_env.sh` / `envctl` accept `golden`, `naive`, `test` (certification) and
`verify` (score the live world). Certification needs the environment stood up
first (Mailpit for the clinic; a `CUA_GYM_HUB` checkout for the hotel and
travel) — see **Paths** below.

The travel environment keeps its scripts under `certification/`, `rewards/`,
and `environment/` rather than at the top level.

### Paths

Absolute paths were rewritten to environment variables. Set before use:

```
export ENVOS_ROOT=/path/to/this/checkout/..
export ENVOS_OPT=$ENVOS_ROOT/opt        # python venv + tooling
export CUA_GYM_HUB=/path/to/CUA-Gym-Hub # for the hotel and travel environments
```

## snapshots/

`snapshots/<env>/<variant>/<rollout>/` for all 93 archived rollouts
(clinic 18 variants / 55 rollouts, hotel 7 / 20, travel 7 / 18). Each holds only
what re-scoring and the cost table need:

- frozen application state at episode end — `world.json` + `mailbox.json`
  (clinic) or `episode_snapshot.json` (hotel, travel)
- `reward.json` — invariants, dense reward, terminal success, signatures,
  diagnosis
- `run-info.json` — task, variant, verdict, failed invariants, source run dir
- `timing.json` — wall-clock (`duration_s`) and `agent_actions` for the cost
  table
- `phenomenon.json`, `requirement.json`, and `policy.json` (hotel) — the
  injected perturbation and task parameters; hotel and travel only
- `actions.log` (all); `*.provenance.jsonl` — the state-transition logs the
  checkpoints are recovered from; hotel and travel only

Re-score any rollout offline (clinic reads `--world`, hotel and travel read
`--snapshot`):

```
python3 environments/clinic/reward.py         --world    snapshots/clinic/<variant>/<rollout>/world.json
python3 environments/hotel/reward.py           --snapshot snapshots/hotel/<variant>/<rollout>/episode_snapshot.json
python3 environments/travel/rewards/reward.py  --snapshot snapshots/travel/<variant>/<rollout>/episode_snapshot.json
```

All 93 re-score with zero drift against the released verifiers.

## analysis/

| File | |
|---|---|
| `runs.csv` | one row per rollout: dense reward, pass/fail, failed invariants, signatures, diagnosis |
| `atlas.csv` | one row per variant — the machine-readable failure atlas: taxonomy, k, pass rate, Wilson interval, `pass^k`, dense-reward spread, signatures |
| `paper_stats.json` | every derived number in the paper |
| `*.md` | the intermediate analyses (`claims`, `contrasts`, `families`, `mechanisms`, `pooled`, `summary`) |
| `bin/analyse.py` | rebuilds `runs.csv`, `atlas.csv`, `contrasts.md`, `summary.md` from `snapshots/` + `environments/*/atlas.spec.json` |
| `bin/paper_stats.py` | regenerates `paper_stats.json` from `runs.csv`, the certification suites, and the snapshot timing |
| `bin/{families,claims,mechanisms,pooled}.py` | regenerate the matching `*.md` |
| `bin/figures7.py` | regenerates every figure (`pdf` / `png` argument) |
| `bin/import-run.py` | ingests a raw rollout directory, re-scores against the current checker, records drift |

Regeneration order: `analyse.py` → `paper_stats.py` → `figures7.py` and the
`*.md` scripts. Every table regenerates with the Python standard library alone;
figures additionally need `matplotlib`. The raw screen recordings are not part
of the release, so the screenshot panels in `fig1_hero`, `fig5_checkpoints`,
and `fig11_failuregrid` render empty while the data-driven content regenerates
in full; `figs_crop/atlas_telemetry.png` in the paper is a screenshot and has
no regeneration path here.

## License

MIT for our code, the environments we author, the manifests, and the frozen
snapshots. Third-party components (CUA-Gym Hub, Mailpit, `xdotool`, `scrot`)
keep their own licenses; Claude Code and Claude Opus 5 are proprietary and
accessed through a commercial API, which is why the snapshots are released so
that scoring runs entirely offline.

## Excluded rollouts

Two rollouts recorded during construction are not part of the analysis and are
not in `snapshots/`:

- a post-commitment Ghost Commit rollout that was imported twice under two run
  ids (the second was a byte-identical duplicate); the post-commitment cell is
  `0/3`, not `0/4`;
- an early cold-start pilot run executed under a preliminary arm configuration.

`runs.csv`, `atlas.csv`, and `paper_stats.json` reflect the 93-rollout corpus.
