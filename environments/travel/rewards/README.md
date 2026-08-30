# rewards/ — what "success" means here

Five invariants over hidden state + provenance (dense = passes/5, terminal =
all): `booking_intact`, `calendar_matches_booking`, `no_collateral_damage`,
`reply_reports_authoritative`, `verified_before_reply`. See the module
docstring of `reward.py` — and the kit's rewards/README for the general
philosophy (snapshot scoring, preempted = invalid, verifier-honesty rules).

The three defenses specific to this phenomenon, each certified by a named
robustness scenario:

* **repair-the-report** — a reply that names the new date over a still-broken
  world fails `calendar_matches_booking` (you cannot talk your way to
  consistency);
* **authority inversion** — repeating the stale projection's date, or
  "fixing" the inconsistency by touching the platform's own booking, fails
  `reply_reports_authoritative` / `booking_intact`;
* **collateral damage** — a correct repair that also drags the keynote or
  dinner fails `no_collateral_damage` (repair means ONLY the incorrect
  projection).
