# hub/ — the substrate

The environment is built on **stock CUA-Gym-Hub mock applications** — realistic
single-page-app clones (Xpedia ≈ Expedia, Xmail ≈ Gmail) from
<https://github.com/xlang-ai/CUA-Gym-Hub>. **No upstream file is ever
modified**; every behaviour the kit needs beyond the stock apps lives in the
proxy layer (`environment/reground_proxy.py`).

| file | job |
|---|---|
| `start_mocks.py` | start `npm run preview` for both apps on loopback ports, idempotently |
| `prime_defaults.py` | (rarely needed) re-capture each app's own pristine default state |
| `app_defaults/*.json` | the captured defaults the kit ships with |

## Why cached defaults exist

The Hub mocks build their default state **in the browser**, not on the server:
the server knows nothing until an app has loaded once and pushed its state up.
Priming with a headless browser on every setup proved flaky, so the kit
captures each app's own catalog **once** into `app_defaults/` and seeding then
*edits that real state* rather than inventing one. That is what keeps the
hotel catalog "the app's own data" — only two values in it are seeded, and
each carries a written justification (`environment/world/canonical.py`,
`SEEDED_EDITS`).

If your Hub build's catalog differs from the certified one, the seeding
assertion in `environment/initial_setup.py` will fail loudly; re-run
`prime_defaults.py` and re-check `SEEDED_EDITS` against the new catalog.

## The sid

State on a mock server is partitioned by `?sid=...`. Several kit instances
(several seeds, several experimenters) can share one pair of mock processes —
each uses its own `ENVOS_SID`. That's also why `envctl stop` leaves the mocks
running.
