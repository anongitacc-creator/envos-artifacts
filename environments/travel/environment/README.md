# environment/ — world, projections, proxy, phenomenon

Same chassis as envos-kit (see its READMEs for the deep tour). Task-specific:

* `world/canonical.py` — one entity across three apps: the seeded BOOKING
  (authoritative), the receipt + task emails, the calendar events. The ground
  truth accessor is `authoritative_checkin(live_state)`; the cross-app
  invariant is `consistent(exp, cal)`; dates are judged via
  `event_local_date` (the mock edits in local time, stores UTC).
* `reground_proxy.py` — untouched kit proxy. Xpedia runs poller-OFF (stale
  UI), Xmail and Calendar poller-ON. The calendar never gets a revision bump:
  the failed sync IS the phenomenon.
* `initial_setup.py` — seeds all three apps CONSISTENT from the canonical
  world and asserts it (`canonical.consistent`) before anything runs.
* `exogenous_actor.py` — the partial commit: booking moves + receipt lands +
  overlay pins the new dates durable; calendar deliberately untouched.
  Exposure-formed trigger: fires ENVOS_DWELL_S after the agent first VIEWS
  the entity (Trips document or calendar); preempted (invalid) if the reply
  was already sent.
