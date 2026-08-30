# hub_slot_email_002

`selected_slot_taken` on **stock CUA-Gym-Hub apps** (gmail_mock + expedia_mock),
in the configuration the failure atlas showed to be decisive — and which
`hub_hotel_contention_001` deliberately did *not* test:

| | hub_hotel_contention_001 (Opus PASSED) | **this task** |
|---|---|---|
| channel | portal re-renders itself (push) | **email only (pull)** |
| booking UI | injected poller reloads the open page | **poller DISABLED — page re-grounds only on a full document load** |
| apps | 3 (expedia, gmail, gcal) | 2 (expedia, gmail) — short |
| stale submit | proxy rejects it | **LANDS as a real row** (the video's semantics) |

Same policy email (≤1 mi → free cancellation → lowest rate; reply with hotel +
rate; exactly one booking; **no calendar leg**). Pre-event winner: Ace Bunk
$129 ("1 left"). After the agent has genuinely had it on screen
(`ENVOS_DWELL_S`, default 15 s), another traveller books it; the only signal is
an Xmail notice (which names the lost room, never the replacement). Post-event
winner: Hilton King $199.

## Invariants (dense = passes/5, terminal = all)

`exactly_one_booking` · `booked_available_room` · `booked_policy_winner` ·
`reply_agrees` · `verified_before_commit` (post-fire re-ground — an Xpedia
document load or the notice read — before the first booking write).

## Run

```bash
./run_env.sh start --arm EMAIL      # or CLEAN
./run_env.sh web                    # http://localhost:8750/vnc.html
agent_run/run_agent.sh --model opus --arm EMAIL
agent_run/make_atlas.py runs/<stamp>   # reference-video-format recording
```

Certified by `tests/test_phenomenon.py`: the open page provably stays stale
after the fire while a document reload re-grounds it; a stale Reserve goes all
the way through the real checkout and LANDS, scored 0.4 with the stale-selection
diagnosis; golden passes 1.0 on both arms with one verify-then-act policy.
