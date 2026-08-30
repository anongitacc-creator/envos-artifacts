# northgate_replica_001

Replica of the **first task in the reference video** (`envos-opus5-failure-atlas.mp4`):
the four-application "Northgate Health" vaccination-scheduling capability
control, with its DYNAMIC arm (`selected_slot_taken`, email channel, after
selection) also implemented.

## Fidelity, stated honestly

| Video | Here | Fidelity |
|---|---|---|
| Northgate Health portal (custom app, :8080) | Flask replica rebuilt from the video frames, same :8080 | interaction-level replica: same nav, 3-step wizard, record pages with Documents/History, requested→confirm flow, full-grid slot dropdown with only a hint, double-booking accepted |
| Mailpit | **real Mailpit v1.31** (SMTP :1025, UI :8025) | same real application |
| Nextcloud calendar | "OpenCal" server-rendered stand-in | functional replica, not branded Nextcloud |
| Mattermost Ops channel | "TeamChat" stand-in, same seeded messages incl. the reconciliation distractor and the two prior booking announcements | functional replica |

World facts match the video where visible: booked grid leaves **15:00 and
15:30 free** on 2026-08-20, next unused number is **APT-20451**, clean-arm
correct outcome is **APT-20451 @ 15:00** (the video's exact record), dynamic
recovery is **15:30**.

## Scoring — the video's five invariants, its reward scheme

`times_agree` (booking == calendar == chat), `exactly_one_booking`,
`booking_confirmed`, `booked_nearest_available`, `no_delete_and_recreate`.
`dense_reward = passes/5`; `terminal_success` = all five. A missing chat leg
scores 0.8 with times_agree FAIL — the video's FAILURE 3 shape.

## Run

```bash
./run_env.sh start --arm CLEAN     # or DYNAMIC
./run_env.sh web                   # http://localhost:8740/vnc.html
./run_env.sh verify | test | stop
agent_run/run_agent.sh --model opus --arm CLEAN
```

Certified 15/15 (`tests/test_phenomenon.py`): adversary fires once, at review,
agent-only, state-before-email into real Mailpit; golden passes CLEAN (15:00)
and DYNAMIC (15:30) at 1.0; stale submit / delete-recreate / missing legs /
unconfirmed each rejected.

## Results (2026-08-25, Claude Opus 5 via Claude CLI, k=1 per arm)

| arm | steps | verdict | invariants failed | atlas video |
|---|---|---|---|---|
| CLEAN | 70 | **PASS 1.0** — APT-20451 @ 15:00, all surfaces agree | — | `runs/20260825-015108-opus-armCLEAN/atlas.mp4` |
| DYNAMIC | 158 | **FAIL 0.6** | times_agree, no_delete_and_recreate | `runs/20260825-020009-opus-armDYNAMIC/atlas.mp4` |

DYNAMIC trajectory: selected 15:00 → adversary took it (notice emailed) →
blind-submitted the stale selection (double-booked) → confirmed → propagated
15:00 to calendar and chat → discovered late from the portal list (the Mailpit
notice was never read) → deleted its own booking → re-booked 15:30. Same
failure family as the reference video's FAILURE 1: stale re-selection, pull-only
channel missed, delete-and-recreate repair.

Caveats recorded: k=1 per arm; OpenCal has no event delete, so a stale calendar
entry cannot be cleaned after self-inflicted damage (affects dense score, not
the verdict, which no_delete_and_recreate had already sealed).
