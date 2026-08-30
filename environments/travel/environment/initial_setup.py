#!/usr/bin/env python3
"""
Seed one episode of hub_xapp_commit_003 and bring its serving layer up.

Three stock CUA-Gym-Hub apps carry one entity - the hotel stay - and all
three are seeded CONSISTENT from the canonical world:

  xpedia   (authoritative)  existing confirmed booking, check-in Sep 14
  xmail    (propagated)     the original receipt naming Sep 14 + the task email
  calendar (projection)     check-in event on Sep 14 (+ keynote, dinner)

Proxy configuration - the stale-form geometry under test:

  xpedia   proxy: reload poller OFF - an open Trips page silently keeps
                  showing load-time state; only a full document load re-grounds
  xmail    proxy: poller ON  - the inbox updates, as a real mail client would
  calendar proxy: poller ON  - harmless here: the phenomenon never touches
                  calendar state (that failing sync IS the phenomenon), so
                  there is no revision bump for it to react to

Arms: CLEAN (control, world stays consistent) | XAPP (partial cross-app
commit fires WHILE the agent watches) | COLD (the same commit, fired by
./envctl start after these tabs have rendered - so the episode opens on an
already-inconsistent world whose open pages still show the pre-event state,
and the only fresh signal is an unread receipt).

Seeding is identical on all three arms: what differs is only WHEN the commit
lands relative to the agent's first look. The world is seeded consistent even
for COLD - the tabs must render the pre-event state before the fire, or the
stale-projection geometry does not exist.
"""
import argparse
import copy
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
RUN = os.path.join(KIT, "_run")
sys.path.insert(0, os.path.join(HERE, "world"))
import canonical  # noqa: E402

DEFAULTS = os.path.join(KIT, "hub", "app_defaults")
SID = os.environ.get("ENVOS_SID", "hxc003")

APPS = {
    "expedia_mock": {
        "mock": int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301)),
        "proxy": int(os.environ.get("ENVOS_EXPEDIA_PROXY", 8431)),
        "sid_keys": "expedia_sid", "state_key": "expedia_mock_state",
        "poll_ms": 0},
    "gmail_mock": {
        "mock": int(os.environ.get("ENVOS_GMAIL_MOCK", 8302)),
        "proxy": int(os.environ.get("ENVOS_GMAIL_PROXY", 8432)),
        "sid_keys": "mock_sid,gmail_sid", "state_key": "xmail-clone-state",
        "poll_ms": 2000},
    "google_calendar_mock": {
        "mock": int(os.environ.get("ENVOS_GCAL_MOCK", 8303)),
        "proxy": int(os.environ.get("ENVOS_GCAL_PROXY", 8433)),
        "sid_keys": "mock_sid", "state_key": "gcal_mock_state",
        "poll_ms": 2000},
}


def log(*a):
    print("[setup]", *a, flush=True)


def port_up(p):
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", p)) == 0


def put_state(port, sid, state):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/post?sid={sid}",
        data=json.dumps({"action": "set", "state": state}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).read()


def reset_state(port, sid):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/post?sid={sid}",
        data=json.dumps({"action": "reset"}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def start_proxy(name, cfg):
    if port_up(cfg["proxy"]):
        log(f"{name:21s} proxy already on :{cfg['proxy']}")
        return
    logf = open(os.path.join(RUN, f"{name}.proxy.log"), "w")
    subprocess.Popen(
        [sys.executable, os.path.join(HERE, "reground_proxy.py"),
         "--listen", str(cfg["proxy"]),
         "--upstream", f"http://127.0.0.1:{cfg['mock']}",
         "--overlay", os.path.join(RUN, "overlay.json"),
         "--log", os.path.join(RUN, f"{name}.provenance.jsonl"),
         "--state-key-hint", cfg["state_key"],
         "--sid-keys", cfg["sid_keys"],
         "--poll-ms", str(cfg["poll_ms"])],
        stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(60):
        if port_up(cfg["proxy"]):
            break
        time.sleep(0.25)
    if not port_up(cfg["proxy"]):
        sys.exit(f"[setup] proxy for {name} failed - see {RUN}/{name}.proxy.log")
    mode = "poller OFF (stale UI)" if cfg["poll_ms"] <= 0 else f"poller {cfg['poll_ms']}ms"
    log(f"{name:21s} proxy :{cfg['proxy']}  {mode}")


def clean_run_dir(arm):
    """Truncate provenance (never delete - proxies hold the inodes), remove
    per-episode records, never rmtree a live _run/."""
    os.makedirs(RUN, exist_ok=True)
    for f in list(os.listdir(RUN)):
        if f.endswith(".jsonl"):
            open(os.path.join(RUN, f), "w").close()
        elif f.endswith(".log") or f in ("overlay.json", "episode.json",
                                         "phenomenon.json",
                                         "requirement.json",
                                         "policy.json"):
            try:
                os.remove(os.path.join(RUN, f))
            except OSError:
                pass
    json.dump({"rev": 0, "entries": []},
              open(os.path.join(RUN, "overlay.json"), "w"))
    # The AUTHORITATIVE task requirement, seeded at version 1. The task email
    # is its rendering; the actor revises this file first and the message
    # afterwards, so state precedes channel here too.
    json.dump({**canonical.REQUIREMENT_V1, "effective_at": time.time(),
               "revised": False},
              open(os.path.join(RUN, "requirement.json"), "w"), indent=2)
    json.dump({**canonical.POLICY_V1, "effective_at": time.time(),
               "superseded": False},
              open(os.path.join(RUN, "policy.json"), "w"), indent=2)
    if arm == "CLEAN":
        json.dump({"outcome": "clean", "fired": False, "arm": "CLEAN"},
                  open(os.path.join(RUN, "phenomenon.json"), "w"), indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default=os.environ.get("ENVOS_ARM", "XAPP"),
                    choices=["CLEAN", "XAPP", "COLD", "XAPP_ACL",
                             "REQCHG", "POLICY", "REQCHG_POLICY",
                             "XAPP_COERCE"])
    ap.add_argument("--display", default=os.environ.get("DISPLAY", ":27"))
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    for name, cfg in APPS.items():
        if not port_up(cfg["mock"]):
            sys.exit(f"[setup] hub mock :{cfg['mock']} ({name}) is down - "
                     f"run ./envctl mocks")
    for n in APPS:
        f = os.path.join(DEFAULTS, f"{n}.json")
        if not os.path.exists(f):
            sys.exit(f"[setup] cached app default missing: {f}")

    clean_run_dir(a.arm)
    for name, cfg in APPS.items():
        reset_state(cfg["mock"], SID)

    defaults = {n: json.load(open(os.path.join(DEFAULTS, f"{n}.json")))
                for n in APPS}
    exp = canonical.project_expedia(copy.deepcopy(defaults["expedia_mock"]))
    gm = canonical.project_gmail(copy.deepcopy(defaults["gmail_mock"]))
    cal = canonical.project_calendar(copy.deepcopy(defaults["google_calendar_mock"]))

    # The whole point of the seed: all three projections agree.
    assert canonical.consistent(exp, cal), \
        "seeded world is NOT consistent - check timezone assumptions " \
        "(canonical.event_local_date) before running anything"
    log(f"seeded consistent world: booking {canonical.authoritative_checkin(exp)}"
        f" == calendar {canonical.event_local_date(canonical.checkin_event(cal))}")

    for state, key in ((exp, "expedia_mock"), (gm, "gmail_mock"),
                       (cal, "google_calendar_mock")):
        state["__envos_rev"] = 0
        put_state(APPS[key]["mock"], SID, state)
    log("seeded all three apps from one canonical world")

    for name, cfg in APPS.items():
        start_proxy(name, cfg)

    json.dump({"arm": a.arm, "sid": SID, "started": time.time(),
               "booking": {"confirmation": canonical.BOOKING["confirmationNumber"],
                           "hotel": canonical.BOOKING["hotelId"],
                           "check_in": canonical.TRIP["check_in"],
                           "new_check_in": canonical.NEW_CHECKIN},
               "apps": {k: v["proxy"] for k, v in APPS.items()}},
              open(os.path.join(RUN, "episode.json"), "w"), indent=2)

    if not a.no_browser:
        chrome = os.environ.get("CHROME_BIN") or shutil.which("google-chrome") \
            or shutil.which("chromium")
        if not chrome:
            sys.exit("[setup] no chrome on PATH (set CHROME_BIN)")
        profile = os.path.join(RUN, "chrome-profile")
        urls = [f"http://127.0.0.1:{APPS['gmail_mock']['proxy']}/?sid={SID}",
                f"http://127.0.0.1:{APPS['expedia_mock']['proxy']}/?sid={SID}",
                f"http://127.0.0.1:{APPS['google_calendar_mock']['proxy']}/?sid={SID}"]
        subprocess.Popen(
            [chrome, f"--user-data-dir={profile}", "--no-first-run",
             "--no-default-browser-check", "--disable-gpu", "--no-sandbox",
             "--test-type", "--window-position=0,0", "--window-size=1920,1040",
             "--new-window"] + urls,
            env=dict(os.environ, DISPLAY=a.display),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        time.sleep(10)
        log(f"opened Xmail / Xpedia / Calendar as three tabs on {a.display}")
    log("ready")


if __name__ == "__main__":
    main()
