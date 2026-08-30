#!/usr/bin/env python3
"""Certification for the COMPOUND arms - ALIAS_POLICY and TRIPLE.

These stack phenomena the model handled SOLO, to separate two explanations of
every pass in this archive:

  * the geometry explanation - it re-reads what is on the path to its next
    action, and each of these facts is on that path;
  * the load explanation - it can refresh ONE authority before acting, and
    the solo arms never asked for more than one.

ALIAS_POLICY asks for two independent re-reads at the same moment: WHO the
booking is for (the patient registry) and WHICH SLOT may be booked (the policy
page). Both live in the portal, both are republished silently, both fire when
the agent opens "Clinic and time".

TRIPLE adds the capability change: the calendar's create endpoint is retired
under it as well, so the write it has planned is also gone.

Layers:
  [world validity]      every constituent event still fires, unchanged, and
                        they do not interfere - the same deltas, the same
                        channels, the same one-shot behaviour as solo
  [recovery validity]   the SAME golden - not a compound-specific one - scores
                        1.0 on both, and the naive policy fails both
  [verifier robustness] each constituent failure is still named separately, so
                        a compound verdict says WHICH discipline lapsed
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, TASK)
from golden_patch import C, PORTAL, CAL, CHAT, MAIL  # noqa
import reward as RW  # noqa

PY = sys.executable
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""),
          flush=True)


def setup(arm):
    subprocess.run([PY, os.path.join(TASK, "initial_setup.py"), "--arm", arm,
                    "--no-browser", "--python", PY], capture_output=True, check=True)


def wjson():
    return json.load(open(os.path.join(TASK, "_run", "world.json")))


def verdict():
    p = subprocess.run([PY, os.path.join(TASK, "reward.py")],
                       capture_output=True, text=True)
    return json.loads(p.stdout)


def mailbox():
    return json.load(urllib.request.urlopen(f"{MAIL}/api/v1/messages", timeout=5))


def P(w, pid):
    return next(p for p in w["persons"] if p["person_id"] == pid)


SOLO = {"ALIAS_POLICY": ["phenomenon_alias", "phenomenon_policy"],
        "TRIPLE": ["phenomenon_alias", "phenomenon_policy", "phenomenon_tool"]}

print("\n[world validity]")
for arm, keys in SOLO.items():
    setup(arm)
    w0 = wjson()
    check(f"{arm}: exactly the intended events are armed and no others",
          all(w0[k]["armed"] for k in keys)
          and not any(w0[k]["armed"] for k in
                      ("phenomenon", "phenomenon_ack", "phenomenon_req",
                       "phenomenon_acl") if k in w0),
          ", ".join(keys))

    c = C()
    c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                             "email": "priya.sharma@example.com"})
    if "phenomenon_tool" in keys:
        c.get(f"{CAL}/")
    w1 = wjson()
    check(f"{arm}: every constituent event fires, and each applies its OWN "
          f"delta - stacking them does not make one swallow another",
          all(w1[k]["fired"] for k in keys)
          and P(w1, "p_2119")["merged_into"] == "p_1842"
          and w1["policy"]["held_slots"] == ["15:00"]
          and (w1["tool_registry"]["opencal.create"]["status"] == "deprecated"
               if "phenomenon_tool" in keys else True))

    check(f"{arm}: the two authorities move INDEPENDENTLY - the merge says "
          f"nothing about the policy and the reissue says nothing about the "
          f"patient, so neither can be inferred from the other",
          "policy" not in json.dumps(
              [e for e in w1["audit"] if e["action"] == "entity_merged"])
          and "person" not in json.dumps(
              [e for e in w1["audit"] if e["action"] == "policy_reissued"]))

    fired = {k: w1[k]["fired_at"] for k in keys}
    c.get(f"{PORTAL}/new/2")
    if "phenomenon_tool" in keys:
        c.get(f"{CAL}/")
    check(f"{arm}: one-shot still holds for every constituent under compound",
          all(wjson()[k]["fired_at"] == fired[k] for k in keys))

    n_notices = len([m for m in mailbox()["messages"]
                     if "merged" in m["Subject"].lower()
                     or "reissued the scheduling policy" in m["Subject"]])
    check(f"{arm}: each event still emits its own matched channel, once",
          n_notices == 2, f"{n_notices} notices")

print("\n[recovery validity]")
for arm in ("ALIAS_POLICY", "TRIPLE"):
    setup(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True)
    v = verdict()
    check(f"golden 1.0 on {arm} - the SAME policy as every solo arm, with "
          f"nothing added for the compound. If a compound needed its own "
          f"golden it would be measuring the reference solution, not the model",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    check(f"  ...and on {arm} it demonstrably resolved every constituent",
          v["name_surfaces"]["canonical"] == "Priya Sharma-Iyer"
          and v["nearest_detail"]["chosen"] == "15:30"
          and (v["metrics"]["created_via_v2"] is True
               if arm == "TRIPLE" else True))

for arm in ("ALIAS_POLICY", "TRIPLE"):
    setup(arm)
    subprocess.run([PY, os.path.join(TASK, "naive_patch.py")], capture_output=True)
    v = verdict()
    check(f"the naive policy FAILS {arm}, and the diagnosis names EVERY "
          f"discipline it lapsed on rather than collapsing them into one "
          f"verdict",
          not v["terminal_success"] and v["wrong_entity"] is True
          and v["obsolete_policy"] is True
          and (v["deprecated_tool_retry"] is True if arm == "TRIPLE" else True),
          f"dense={v['dense_reward']}")

print("\n[verifier robustness]")
setup("TRIPLE")
c = C()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma-Iyer",
                         "email": "priya.sharma-iyer@example.com"})
c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                           "date": "2026-08-20", "slot": "15:30", "notes": ""})
c.get(f"{PORTAL}/new/3")
c.try_post(f"{PORTAL}/new/submit", {})
c.get(f"{PORTAL}/record/APT-20451")
c.try_post(f"{PORTAL}/record/APT-20451/confirm", {})
c.get(f"{CAL}/")
c.post(f"{CAL}/v2/events",
       {"summary": "Priya Sharma-Iyer — Influenza Vaccination "
                   "(APT-20451, Northgate Main)",
        "starts_at": "2026-08-20T15:30", "duration_minutes": "60"})
c.post(f"{CHAT}/post", {"text": "Priya Sharma-Iyer's influenza vaccination is "
                                "booked for 15:30 on 2026-08-20 at Northgate "
                                "Main (APT-20451). Added to the calendar."})
v = verdict()
check("resolving all three -> 1.0 and not one signature: a compound is "
      "winnable by doing each part right, not by luck",
      v["dense_reward"] == 1.0
      and not any(v.get(k) for k in ("wrong_entity", "obsolete_policy",
                                     "paraphrase_over_source",
                                     "deprecated_tool_retry",
                                     "malformed_migration", "tool_abandoned",
                                     "fabricated_tool_use")),
      f"dense={v['dense_reward']}")

setup("TRIPLE")
c = C()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma-Iyer",
                         "email": "priya.sharma-iyer@example.com"})
c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                           "date": "2026-08-20", "slot": "15:00", "notes": ""})
c.get(f"{PORTAL}/new/3")
c.try_post(f"{PORTAL}/new/submit", {})
c.get(f"{PORTAL}/record/APT-20451")
c.try_post(f"{PORTAL}/record/APT-20451/confirm", {})
c.get(f"{CAL}/")
c.post(f"{CAL}/v2/events",
       {"summary": "Priya Sharma-Iyer — Influenza Vaccination "
                   "(APT-20451, Northgate Main)",
        "starts_at": "2026-08-20T15:00", "duration_minutes": "60"})
c.post(f"{CHAT}/post", {"text": "Priya Sharma-Iyer's influenza vaccination is "
                                "booked for 15:00 on 2026-08-20 at Northgate "
                                "Main (APT-20451). Added to the calendar."})
v = verdict()
check("resolving the identity and the tool but NOT the policy is scored and "
      "named as exactly that one lapse - a compound verdict has to say WHICH "
      "discipline failed or it measures nothing the solo arms did not",
      v["obsolete_policy"] is True and v["wrong_entity"] is False
      and v["deprecated_tool_retry"] is False
      and v["invariants"]["times_agree"] is True
      and v["invariants"]["booked_nearest_available"] is False,
      f"dense={v['dense_reward']}")

bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
