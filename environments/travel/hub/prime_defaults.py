#!/usr/bin/env python3
"""
Regenerate hub/app_defaults/*.json - each app's OWN pristine default state.

Why this exists: the Hub mocks build their default state in the BROWSER, not
on the server. The server knows nothing until an app loads once and pushes its
state up. So the only authentic source for a starting catalog is to load each
app headlessly with a throwaway sid and save what it pushed. Seeding
(environment/initial_setup.py) then EDITS that real state instead of inventing
one - which is what keeps the catalog "the app's own data" rather than ours.

The kit ships with the two JSONs already captured, so you normally never run
this. Run it only if your CUA-Gym-Hub build differs from the one the kit was
certified against (the seeding assertion in initial_setup.py will tell you).

Usage: .kit/venv/bin/python hub/prime_defaults.py     (mocks must be up)
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(KIT, "hub")
PRIME_SID = "kitprime"

MOCKS = {
    "expedia_mock": int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301)),
    "gmail_mock":   int(os.environ.get("ENVOS_GMAIL_MOCK", 8302)),
}
CHROME = os.environ.get("CHROME_BIN") or shutil.which("google-chrome") \
    or shutil.which("chromium")


def post(port, payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/post?sid={PRIME_SID}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def get_state(port):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={PRIME_SID}", timeout=15))
    return d["stored_state"] if isinstance(d, dict) and "stored_state" in d else d


if __name__ == "__main__":
    if not CHROME:
        sys.exit("[prime] no chrome/chromium on PATH (set CHROME_BIN)")
    os.makedirs(os.path.join(HERE, "app_defaults"), exist_ok=True)
    for name, port in MOCKS.items():
        post(port, {"action": "reset"})     # drop any stale prime state first
        subprocess.run(
            [CHROME, f"--user-data-dir=/tmp/envos-prime-profile",
             "--headless=new", "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=8000", "--dump-dom",
             f"http://127.0.0.1:{port}/?sid={PRIME_SID}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        st = get_state(port)
        if not st or not isinstance(st, dict):
            sys.exit(f"[prime] {name} pushed no state - is the mock healthy?")
        out = os.path.join(HERE, "app_defaults", f"{name}.json")
        json.dump(st, open(out, "w"))
        print(f"[prime] {name}: cached -> {out}")
