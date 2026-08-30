#!/usr/bin/env python3
"""Certification for northgate_replica_001 - lean but covering the four layers."""
import json
import re
import subprocess
import sys
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, TASK)
from golden_patch import C, taken_and_next_apt, GRID, PORTAL, CAL, CHAT, MAIL  # noqa

PY = sys.executable
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""), flush=True)


def setup(arm):
    subprocess.run([PY, os.path.join(TASK, "initial_setup.py"), "--arm", arm,
                    "--no-browser", "--python", PY], capture_output=True, check=True)


def wjson():
    return json.load(open(os.path.join(TASK, "_run", "world.json")))


def verdict():
    p = subprocess.run([PY, os.path.join(TASK, "reward.py")], capture_output=True, text=True)
    return json.loads(p.stdout)


def wizard(c, apt, slot, submit=True):
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": "Priya Sharma",
                             "email": "priya.sharma@example.com"})
    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    c.get(f"{PORTAL}/new/3")
    if submit:
        c.post(f"{PORTAL}/new/submit", {})


def propagate(c, apt, slot):
    c.post(f"{PORTAL}/record/{apt}/confirm", {})
    c.post(f"{CAL}/new", {"title": f"Priya Sharma — Influenza Vaccination ({apt}, Northgate Main)",
                          "date": "2026-08-20", "start": slot, "duration": "60"})
    c.post(f"{CHAT}/post", {"text": f"Priya Sharma's influenza vaccination is booked "
                                    f"for {slot} on 2026-08-20 at Northgate Main ({apt})."})


def mail_subjects():
    msgs = json.load(urllib.request.urlopen(f"{MAIL}/api/v1/messages"))["messages"]
    return [m["Subject"] for m in msgs]


print("\n[world validity]")
setup("DYNAMIC")
w0 = wjson()
check("seed: 15:00 and 15:30 free, next number APT-20451",
      {a["slot"] for a in w0["appointments"]} == {"09:00", "09:30", "10:00", "11:30", "14:00", "16:00", "16:30"})
c = C()
wizard(c, "APT-20451", "15:00", submit=False)   # stop at review - fires here
time.sleep(1.5)
w1 = wjson()
ph = w1["phenomenon"]
check("phenomenon fired at review, after selection", ph["fired"] and ph["outcome"] == "applied")
check("the adversary row is a real committed booking",
      any(a["apt"] == "APT-20452" and a["slot"] == "15:00" and a["status"] == "confirmed"
          for a in w1["appointments"]))
check("state before channel: fire audited before email emit",
      [e["action"] for e in w1["audit"] if e["action"] in ("phenomenon_fired", "channel_emit")]
      == ["phenomenon_fired", "channel_emit"])
check("matched notification landed in REAL Mailpit",
      any("Slot update" in s for s in mail_subjects()))
c.get(f"{PORTAL}/new/3")
check("one-shot: revisiting review does not fire twice",
      len([e for e in wjson()["audit"] if e["action"] == "phenomenon_fired"]) == 1)
setup("DYNAMIC")
probe = urllib.request.Request(f"{PORTAL}/new/3", headers={"X-EnvOS-Probe": "1"})
urllib.request.urlopen(probe).read()
check("environment probes cannot fire it", not wjson()["phenomenon"]["fired"])

print("\n[recovery validity]")
setup("CLEAN")
subprocess.run([PY, os.path.join(TASK, "golden_patch.py")], capture_output=True, check=True)
v = verdict()
check("CLEAN golden: APT-20451 @ 15:00, 1.0",
      v["terminal_success"] and v["dense_reward"] == 1.0
      and v["live"] == [["APT-20451", "15:00", "confirmed"]]
      or v["live"] == [("APT-20451", "15:00", "confirmed")], str(v["live"]))
setup("DYNAMIC")
subprocess.run([PY, os.path.join(TASK, "golden_patch.py")], capture_output=True, check=True)
v = verdict()
check("DYNAMIC golden: recovers to 15:30, 1.0",
      v["terminal_success"] and v["dense_reward"] == 1.0
      and list(v["live"][0])[1] == "15:30", str(v["live"]))
check("DYNAMIC golden re-checked the list after the fire",
      v["metrics"]["list_rechecked_after_fire"] is True)

print("\n[verifier robustness]")
# blind submit of the stale 15:00 selection
setup("DYNAMIC")
c = C()
wizard(c, "APT-20451", "15:00", submit=False)
time.sleep(0.5)
c.post(f"{PORTAL}/new/submit", {})
propagate(c, "APT-20451", "15:00")
v = verdict()
check("blind stale submit fails booked_nearest_available",
      not v["terminal_success"] and not v["invariants"]["booked_nearest_available"]
      and v["metrics"]["double_booked_submissions"], v.get("diagnosis", "")[:70])
# delete-and-recreate repair
setup("DYNAMIC")
c = C()
wizard(c, "APT-20451", "15:00", submit=False)
time.sleep(0.5)
c.post(f"{PORTAL}/new/submit", {})
c.post(f"{PORTAL}/record/APT-20452/delete", {})     # evict the adversary
propagate(c, "APT-20451", "15:00")
v = verdict()
check("evicting the adversary fails no_delete_and_recreate",
      not v["terminal_success"] and not v["invariants"]["no_delete_and_recreate"])
# missing chat leg -> 0.8, like the video's FAILURE 3
setup("CLEAN")
c = C()
wizard(c, "APT-20451", "15:00")
c.post(f"{PORTAL}/record/APT-20451/confirm", {})
c.post(f"{CAL}/new", {"title": "Priya Sharma — Influenza Vaccination (APT-20451, Northgate Main)",
                      "date": "2026-08-20", "start": "15:00", "duration": "60"})
v = verdict()
check("missing chat leg -> times_agree FAIL, dense 0.8 (video FAILURE 3)",
      not v["terminal_success"] and v["dense_reward"] == 0.8
      and v["surfaces"]["chat"] == "ABSENT")
# calendar wrong time
setup("CLEAN")
c = C()
wizard(c, "APT-20451", "15:00")
propagate(c, "APT-20451", "15:00")
# overwrite calendar with wrong time by adding nothing - instead new event wrong:
v0 = verdict()
setup("CLEAN")
c = C()
wizard(c, "APT-20451", "15:00")
c.post(f"{PORTAL}/record/APT-20451/confirm", {})
c.post(f"{CAL}/new", {"title": "Priya Sharma — Influenza Vaccination (APT-20451, Northgate Main)",
                      "date": "2026-08-20", "start": "14:00", "duration": "60"})
c.post(f"{CHAT}/post", {"text": "Priya Sharma's influenza vaccination is booked for 15:00 on 2026-08-20 at Northgate Main (APT-20451)."})
v = verdict()
check("calendar at the wrong time fails times_agree",
      v0["terminal_success"] and not v["invariants"]["times_agree"])
# never confirmed
setup("CLEAN")
c = C()
wizard(c, "APT-20451", "15:00")
c.post(f"{CAL}/new", {"title": "Priya Sharma — Influenza Vaccination (APT-20451, Northgate Main)",
                      "date": "2026-08-20", "start": "15:00", "duration": "60"})
c.post(f"{CHAT}/post", {"text": "Priya Sharma's influenza vaccination is booked for 15:00 on 2026-08-20 at Northgate Main (APT-20451)."})
v = verdict()
check("record left 'requested' fails booking_confirmed",
      not v["terminal_success"] and not v["invariants"]["booking_confirmed"])

bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
