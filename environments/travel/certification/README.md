# certification/ — the license to blame the agent

`./envctl test` runs `test_phenomenon.py` (expect 15/15):

1. **world validity** — the partial propagation is real: authoritative
   booking + receipt move, the calendar provably does not, the open Trips
   page provably keeps rendering pre-event state (localStorage-level check)
   while a document reload re-grounds it, and the change is durable against
   SPA write-backs.
2. **recovery validity** — `golden_patch.py` passes 1.0 through the real UI
   on both arms with one verify-then-act policy (survey → re-ground before
   the terminal act → platform is authority → repair only the calendar →
   reply).
3. **verifier robustness** — every named shortcut fails and is named:
   repair-the-report, trust-the-stale-projection, collateral damage,
   cancelling the authoritative booking as a "fix", false success.

Green suite first, agent verdicts second — always.
