# EnvOS — released artifacts

This repository accompanies the paper *EnvOS: A Certified Pipeline for
Evaluating Interactive Agents Under State-Changing Phenomena*. It contains the
three evaluation environments, their certification suites, the frozen
per-rollout snapshots, and the analysis scripts — everything needed to inspect
the environments, re-run certification, and reproduce every number and figure in
the paper from the archived rollouts, without any model calls.

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
  certification suite; 389 assertions across the three environments
- `run_env.sh` / `envctl` — seed, run the reference/deficient policies, run
  certification (`golden` / `naive` / `test`), score (`verify`)
- `run_agent.sh` — the exact non-interactive `claude` invocation used for
  rollouts (`--allowedTools Bash Read`, isolated working directory)
- `apps/`, `world/`, `hub/`, `environment/` — application code and seed data
- `README.md`, `PHENOMENON.md` — per-environment notes

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
what re-scoring needs:

- `episode_snapshot.json` (or `world.json` + `mailbox.json`) — frozen
  application state at episode end
- `reward.json` — invariants, dense reward, terminal success, signatures,
  diagnosis
- `run-info.json` — task, variant, verdict, failed invariants
- `phenomenon.json`, `policy.json`, `requirement.json` — the injected
  perturbation and task parameters
- `actions.log`, `*.provenance.jsonl` — the action and state-transition logs the
  checkpoints are recovered from

Re-score any rollout offline:

```
python3 environments/<env>/reward.py --snapshot snapshots/<env>/<variant>/<rollout>/episode_snapshot.json
```

## analysis/

| File | |
|---|---|
| `runs.csv` | one row per rollout: dense reward, pass/fail, failed invariants, signatures, diagnosis |
| `atlas.csv` | per-rollout timing and action counts |
| `paper_stats.json` | every derived number in the paper |
| `*.md` | the intermediate analyses (`claims`, `contrasts`, `families`, `mechanisms`, `pooled`, `summary`) |
| `bin/paper_stats.py` | regenerates `paper_stats.json` from `runs.csv` + the certification suites |
| `bin/figures7.py` | regenerates every figure (`pdf` argument) |
| `bin/import-run.py` | ingests a rollout directory, re-scores against the current checker, records drift |

Every table and figure regenerates with the Python standard library alone
(matplotlib only for the figures).

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
