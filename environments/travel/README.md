# hub_xapp_commit_003 — partial cross-app commit

The EnvOS phenomenon the research doc calls its **"strongest longer-term moat
candidate"**: one entity (a hotel stay) lives in three stock CUA-Gym-Hub apps,
and mid-episode the world commits a change **partially** —

```
Xpedia booking    Sep 15   <- authoritative      (updated)
Xmail receipt     Sep 15   <- propagated         (lands, unread)
Calendar event    Sep 14   <- STALE              (sync job "fails")
```

This is not conflicting text: the world itself temporarily violates the
cross-application invariant *all projections agree with the authoritative
version*. The benchmark asks whether the agent can **discover** the
inconsistency, decide which source is **authoritative**, and **repair only
the incorrect projection** — then report the truth.

## The task (20–35 GUI steps)

Ines (Travel) emails: *reply with the hotel, confirmation number and check-in
date — and make sure the calendar matches the booking, finance cross-checks
it.* The agent surveys a fully consistent world (everything says Sep 14);
once it has genuinely seen it (`ENVOS_DWELL_S` after its first Trips/calendar
view), the property moves the stay to Sep 15. The Xpedia page re-grounds only
on a full document load; the only push signal is the receipt email; the
calendar just sits there being wrong.

## Arms — the same commit, three collision geometries

The task, the seed, the invariants and the receipt are identical on every arm.
What varies is **when the world commits relative to the agent's first look** —
so a recovery-rate gap between arms is attributable to that and nothing else
(certified: `channel parity with XAPP`).

| arm | the commit lands | what the agent meets |
|---|---|---|
| `CLEAN` | never | a consistent world; control |
| `XAPP` | `ENVOS_DWELL_S` after the agent's own first view | it changes **while the agent watches** — a fresh email arrives on a world it has already surveyed |
| `COLD` | after the tabs render, **before step 0** | an **already-broken** world: Trips and calendar are inherited pages showing the pre-event date, the receipt sits unread, and nothing on screen ever changes by itself |

`COLD` is the harder arm and the pilot rollout discovered it by accident: with
no *it-changed-while-I-watched* cue, Opus resolved the conflict by majority
vote across surfaces — two stale screens outvoting one fresh receipt — and
reasoned its way into rejecting the authoritative signal it was quoting. The
verifier names that specimen: `authority_inversion` (unscored signature; read
the receipt, reported the dead date anyway, never reloaded Trips). It is
distinct from never having looked at all, and the suite certifies the
distinction.

## Invariants (dense = passes/5, terminal = all)

`booking_intact` (the authoritative store was not "repaired") ·
`calendar_matches_booking` (THE cross-app invariant) ·
`no_collateral_damage` (keynote & dinner untouched) ·
`reply_reports_authoritative` (new date; dead date only in superseded context) ·
`verified_before_reply` (receipt read or Trips reloaded before sending)

## Run

```bash
./envctl check                 # deps (shares the envos-kit toolchain via config.local.env)
./envctl test                  # certification: expect 28/28 (all three arms)
./envctl start --arm XAPP && ./envctl web    # watch: http://localhost:8752/vnc.html
./envctl start --arm COLD      # the cold-start geometry instead
./envctl rollout [--arm COLD]  # recorded, scored Opus episode -> runs/<stamp>/
./envctl atlas runs/<stamp>    # the annotated failure-atlas video
```

Built on the envos-kit chassis (`${ENVOS_ROOT}/envos-kit`,
see its `docs/05-extending.md` — this task is that recipe executed: same
proxy, same provenance, same certification discipline, new phenomenon).
Everything specific to this task lives in `environment/world/canonical.py`,
`environment/exogenous_actor.py`, `rewards/reward.py`,
`certification/` and `agent/make_atlas.py`.
