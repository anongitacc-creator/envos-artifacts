#!/usr/bin/env python3
"""
Start the two stock CUA-Gym-Hub mock servers this task uses, idempotently.

Each mock is the app's own `npm run preview` (vite serving the built dist/) on
a loopback port. The agent is never pointed at these ports - it only ever sees
the re-grounding proxies (environment/reground_proxy.py) that sit in front.

State on a mock server is partitioned by ?sid=..., so several kit instances
(or several seeds) can share one pair of mock processes: each uses its own sid.

Nothing in the CUA-Gym-Hub checkout is modified. Ever. All behaviour this kit
needs beyond the stock apps lives in the proxy layer.
"""
import os
import socket
import subprocess
import sys
import time

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(KIT, "_run")
HUB = os.environ.get("CUA_GYM_HUB", os.path.expanduser("~/CUA-Gym-Hub"))

MOCKS = {
    "expedia_mock": int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301)),
    "gmail_mock":   int(os.environ.get("ENVOS_GMAIL_MOCK", 8302)),
    "google_calendar_mock": int(os.environ.get("ENVOS_GCAL_MOCK", 8303)),
}


def port_up(port):
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_mock(name, port):
    if port_up(port):
        print(f"  [up] {name:13s} mock :{port}", flush=True)
        return
    d = os.path.join(HUB, "websites", name)
    if not os.path.isdir(os.path.join(d, "dist")):
        sys.exit(f"[mocks] {name} is not built - run "
                 f"{HUB}/install-all.sh --only {name} --build")
    os.makedirs(RUN, exist_ok=True)
    logf = open(os.path.join(RUN, f"{name}.mock.log"), "w")
    subprocess.Popen(
        ["npm", "run", "preview", "--", "--host", "127.0.0.1",
         "--port", str(port), "--strictPort"],
        cwd=d, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(360):
        if port_up(port):
            break
        time.sleep(0.25)
    if not port_up(port):
        sys.exit(f"[mocks] {name} failed to start - see {RUN}/{name}.mock.log")
    print(f"  [start] {name:13s} mock :{port}", flush=True)


if __name__ == "__main__":
    for n, p in MOCKS.items():
        start_mock(n, p)
