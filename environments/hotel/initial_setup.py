#!/usr/bin/env python3
"""
Seed hub_slot_email_002: the same phenomenon as hub_hotel_contention_001, in
the configuration the failure atlas showed to be decisive.

Two stock CUA-Gym-Hub apps behind re-grounding proxies:

  xmail  (gmail_mock,   proxy :8412)  poller ON  - the inbox updates, as a
                                       real mail client would
  xpedia (expedia_mock, proxy :8411)  poller OFF - the booking UI re-grounds
                                       ONLY on a full document load; client-side
                                       navigation keeps showing load-time state

So when the world moves, nothing the agent is looking at changes by itself:
the signal is pull-only (an email), and the form it is standing in stays stale.

Arms: CLEAN (control) and EMAIL (the phenomenon).
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
RUN = os.path.join(HERE, "_run")
sys.path.insert(0, os.path.join(HERE, "world"))
import canonical  # noqa: E402

HUB = os.environ.get("CUA_GYM_HUB", "${CUA_GYM_HUB}")
APPS = {
    "expedia_mock": {"mock": 8301, "proxy": 8411, "sid_keys": "expedia_sid",
                     "state_key": "expedia_mock_state", "poll_ms": 0},
    "gmail_mock":   {"mock": 8302, "proxy": 8412, "sid_keys": "mock_sid,gmail_sid",
                     "state_key": "xmail-clone-state", "poll_ms": 2000},
}
SID = os.environ.get("ENVOS_SID", "hse002")
DEFAULTS = os.path.join(os.path.dirname(HERE), "hub_hotel_contention_001",
                        "states", "app_defaults")


def log(*a):
    print("[setup]", *a, flush=True)


def port_up(p):
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", p)) == 0


def get_state(port, sid):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={sid}", timeout=15))
    return d["stored_state"] if isinstance(d, dict) and "stored_state" in d else d


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
        log(f"{name:13s} proxy already on :{cfg['proxy']}")
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
        sys.exit(f"[setup] proxy for {name} failed")
    mode = "poller OFF (stale UI)" if cfg["poll_ms"] <= 0 else f"poller {cfg['poll_ms']}ms"
    log(f"{name:13s} proxy :{cfg['proxy']}  {mode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default=os.environ.get("ENVOS_ARM", "EMAIL"),
                    choices=["CLEAN", "EMAIL", "VOID", "REQCHG",
                             "POLICY", "COERCE", "COSMETIC"])
    ap.add_argument("--display", default=os.environ.get("DISPLAY", ":25"))
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    for p in (8301, 8302):
        if not port_up(p):
            sys.exit(f"[setup] hub mock :{p} is down - start it "
                     f"(hub_hotel_contention_001/run_env.sh start does)")
    for f in (os.path.join(DEFAULTS, "expedia_mock.json"),
              os.path.join(DEFAULTS, "gmail_mock.json")):
        if not os.path.exists(f):
            sys.exit(f"[setup] cached app defaults missing: {f}")

    os.makedirs(RUN, exist_ok=True)
    for f in list(os.listdir(RUN)):
        if f.endswith(".jsonl"):
            # TRUNCATE, never delete: long-lived proxies hold open handles to
            # these logs, and deleting swaps the inode out from under them -
            # every later reader then sees an empty file while the proxy keeps
            # writing to the orphan (the 13/14 suite artifact).
            open(os.path.join(RUN, f), "w").close()
        elif f.endswith(".log") or f in ("overlay.json", "episode.json",
                                         "phenomenon.json",
                                         "requirement.json", "policy.json"):
            try:
                os.remove(os.path.join(RUN, f))
            except OSError:
                pass
    json.dump({"rev": 0, "entries": []},
              open(os.path.join(RUN, "overlay.json"), "w"))
    # The AUTHORITATIVE task requirement, seeded at version 1. Ines's email is
    # its rendering; the actor revises this file first and the message
    # afterwards, so state precedes channel here too.
    json.dump({**canonical.REQUIREMENT_V1, "effective_at": time.time(),
               "revised": False},
              open(os.path.join(RUN, "requirement.json"), "w"), indent=2)
    # The AUTHORITATIVE reimbursement policy, seeded at version 1. Ines's
    # email is its publication; the actor reissues this object first and
    # re-renders the email from it afterwards.
    json.dump({**canonical.POLICY_V1, "effective_at": time.time(),
               "superseded": False},
              open(os.path.join(RUN, "policy.json"), "w"), indent=2)
    if a.arm == "CLEAN":
        # a stale phenomenon record from a prior arm would poison the verifier
        json.dump({"outcome": "clean", "fired": False, "arm": "CLEAN"},
                  open(os.path.join(RUN, "phenomenon.json"), "w"), indent=2)

    for name, cfg in APPS.items():
        reset_state(cfg["mock"], SID)

    defaults = {n: json.load(open(os.path.join(DEFAULTS, f"{n}.json"))) for n in APPS}
    exp = canonical.project_expedia(copy.deepcopy(defaults["expedia_mock"]))
    ov = json.load(open(os.path.join(RUN, "overlay.json")))
    if a.arm in ("COERCE", "COSMETIC"):
        # The booking engine substitutes the last Bunk Room for a Queen Room
        # on the way into the store. COSMETIC is the matched control: the same
        # interception, the same provenance record, the SAME room - isolating
        # "the write was touched" from "the write was changed".
        hot = next(h for h in exp["hotels"] if h["id"] == canonical.TARGET_HOTEL)
        frm = next(r for r in hot["rooms"] if r["id"] == canonical.TARGET_ROOM)
        to = frm if a.arm == "COSMETIC" else next(
            r for r in hot["rooms"] if r["id"] == "room_8_2")
        ov["coerce_room"] = {
            "hotel_id": canonical.TARGET_HOTEL,
            "from_room": frm["name"], "to_room": to["name"],
            "to_total": to.get("totalPrice") or to["pricePerNight"] * canonical.TRIP["nights"],
            "note": ("" if a.arm == "COSMETIC" else
                     "Room type substituted at booking"),
        }
        json.dump({"phenomenon_id": "silent_write_coercion",
                   "family": "false_success",
                   "canonical_semantics":
                       f"write_accepted_value_coerced(entity=booking.roomType, "
                       f"requested={frm['name']}, stored={to['name']}, "
                       f"channel=none, reports=success)",
                   "channel": "none", "timing": "after_irreversible_action",
                   "arm": a.arm, "fired": False, "fired_at": None,
                   "outcome": "armed", "style": ("cosmetic" if a.arm == "COSMETIC"
                                                 else "coerce"),
                   "requested_room": frm["name"], "stored_room": to["name"],
                   "requested_price": frm["pricePerNight"],
                   "stored_price": to["pricePerNight"]},
                  open(os.path.join(RUN, "phenomenon.json"), "w"), indent=2)
    json.dump(ov, open(os.path.join(RUN, "overlay.json"), "w"))
    hotel, room = canonical.best(exp)
    log(f"pre-event winner: {hotel['name']} / {room['name']} "
        f"${room['pricePerNight']}/night")
    assert hotel["id"] == canonical.TARGET_HOTEL and room["id"] == canonical.TARGET_ROOM

    gm = canonical.project_gmail(copy.deepcopy(defaults["gmail_mock"]))
    for state, key in ((exp, "expedia_mock"), (gm, "gmail_mock")):
        state["__envos_rev"] = 0
        put_state(APPS[key]["mock"], SID, state)
    log("seeded both apps from one canonical world (no calendar leg)")

    for name, cfg in APPS.items():
        start_proxy(name, cfg)

    json.dump({"arm": a.arm, "sid": SID, "started": time.time(),
               "target": {"hotel": hotel["id"], "hotel_name": hotel["name"],
                          "room": room["id"], "room_name": room["name"],
                          "price": room["pricePerNight"]},
               "apps": {k: v["proxy"] for k, v in APPS.items()}},
              open(os.path.join(RUN, "episode.json"), "w"), indent=2)

    if not a.no_browser:
        chrome = shutil.which("google-chrome")
        profile = os.path.join(RUN, "chrome-profile")
        urls = [f"http://127.0.0.1:{APPS['gmail_mock']['proxy']}/?sid={SID}",
                f"http://127.0.0.1:{APPS['expedia_mock']['proxy']}/?sid={SID}"]
        subprocess.Popen(
            [chrome, f"--user-data-dir={profile}", "--no-first-run",
             "--no-default-browser-check", "--disable-gpu", "--no-sandbox",
             "--test-type", "--window-position=0,0", "--window-size=1920,1040",
             "--new-window"] + urls,
            env=dict(os.environ, DISPLAY=a.display),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        time.sleep(10)
        log(f"opened Xmail / Xpedia as two tabs on {a.display}")
    log("ready")


if __name__ == "__main__":
    main()
