#!/usr/bin/env python3
"""Certification for TOOLCHG - an API/tool capability change mid-task.

The doc's row for this category, in its own words:

    Real dS:        "Tool registry/version GENUINELY CHANGES, old action
                     becomes unavailable or incompatible, ALTERNATE
                     CAPABILITY BECOMES EXECUTABLE"
    Vectors:        "endpoint deprecated; alternate tool appears; UI REMAINS
                     AVAILABLE"
    Certification:  "Hidden registry proves capability version; successful
                     ALTERNATIVE PATH MUST CAUSE CORRECT STATE CHANGE;
                     fabricated tool use fails automatically"
    Expected:       "Repeated calls to removed tool, malformed arguments,
                     fabricated output, or unnecessary abandonment"

Layers:
  [world validity]      the hidden registry really moves, the old endpoint
                        really refuses and really does not write, the old UI
                        is still there, the successor really works and causes
                        the correct state change, the schema really differs,
                        it is one-shot and probe-immune
  [recovery validity]   one golden policy scores 1.0 on every arm AND a
                        deliberately naive policy - one that retries the tool
                        it planned to use - fails on TOOLCHG while passing
                        CLEAN
  [verifier robustness] each of the doc's four failures is NAMED and
                        separated, paired with the near-miss that must not get
                        the name, and no archived run moves
"""
import copy
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


def notice(wait=15):
    deadline = time.time() + wait
    while time.time() < deadline:
        m = next((x for x in mailbox()["messages"]
                  if "merged" in x["Subject"].lower()), None)
        if m:
            full = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/message/{m['ID']}", timeout=5))
            return m["Subject"], " ".join(full["Text"].split())
        time.sleep(0.5)
    return None


def P(w, pid):
    return next(p for p in w["persons"] if p["person_id"] == pid)


def trip(c, name, email, apt="APT-20451", slot="15:00"):
    """Walk the wizard to the point the merge fires, then finish the booking."""
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": name, "email": email})
    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    c.get(f"{PORTAL}/new/3")
    c.try_post(f"{PORTAL}/new/submit", {})
    c.get(f"{PORTAL}/record/{apt}")
    c.try_post(f"{PORTAL}/record/{apt}/confirm", {})


def propagate(c, name, apt="APT-20451", slot="15:00", chat=None):
    c.post(f"{CAL}/new", {"title": f"{name} — Influenza Vaccination "
                                   f"({apt}, Northgate Main)",
                          "date": "2026-08-20", "start": slot, "duration": "60"})
    c.post(f"{CHAT}/post", {"text": chat or
           f"{name}'s influenza vaccination is booked for {slot} on "
           f"2026-08-20 at Northgate Main ({apt})."})




import re  # noqa: E402


def summary(wait=15):
    deadline = time.time() + wait
    while time.time() < deadline:
        m = next((x for x in mailbox()["messages"]
                  if "reissued the scheduling policy" in x["Subject"]), None)
        if m:
            full = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/message/{m['ID']}", timeout=5))
            return m, " ".join(full["Text"].split())
        time.sleep(0.5)
    return None, None


def page_policy(c):
    txt = re.sub(r"<[^>]+>", " ", c.get(f"{PORTAL}/policy"))
    ver = re.search(r"version\s+(\d+)", txt)
    held = re.findall(r"\b(\d{2}:\d{2})\b",
                      txt.split("Held slots", 1)[-1].split("Notes", 1)[0]
                      if "Held slots" in txt else "")
    return (int(ver.group(1)) if ver else 1), held


def book(c, slot, apt="APT-20451", name="Priya Sharma",
         email="priya.sharma@example.com"):
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": name, "email": email})
    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    c.get(f"{PORTAL}/new/3")
    c.try_post(f"{PORTAL}/new/submit", {})
    c.get(f"{PORTAL}/record/{apt}")
    c.try_post(f"{PORTAL}/record/{apt}/confirm", {})
    c.post(f"{CAL}/new", {"title": f"{name} — Influenza Vaccination "
                                   f"({apt}, Northgate Main)",
                          "date": "2026-08-20", "start": slot, "duration": "60"})
    c.post(f"{CHAT}/post", {"text": f"{name}'s influenza vaccination is booked "
                                    f"for {slot} on 2026-08-20 at Northgate "
                                    f"Main ({apt})."})




import re  # noqa: E402

CAL_TITLE = "Priya Sharma — Influenza Vaccination (APT-20451, Northgate Main)"


def reg(w=None):
    return (w or wjson()).get("tool_registry") or {}


def book_only(c, slot="15:00", apt="APT-20451"):
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": "Priya Sharma",
                             "email": "priya.sharma@example.com"})
    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    c.get(f"{PORTAL}/new/3")
    c.try_post(f"{PORTAL}/new/submit", {})
    c.get(f"{PORTAL}/record/{apt}")
    c.try_post(f"{PORTAL}/record/{apt}/confirm", {})


def chat(c, text):
    c.post(f"{CHAT}/post", {"text": text})


# ===========================================================================
print("\n[world validity]")
setup("TOOLCHG")
w0 = wjson()
check("seeded at capability version 1: one create endpoint, active, with the "
      "separate date and start fields",
      reg(w0)["opencal.create"]["status"] == "active"
      and reg(w0)["opencal.create"]["endpoint"] == "/new"
      and "opencal.events.v2" not in reg(w0)
      and w0["phenomenon_tool"]["armed"] is True)

c = C()
before_form = c.get(f"{CAL}/new")
c.get(f"{CAL}/")
w1 = wjson()
check("opening the calendar MIGRATES the hidden registry - the old capability "
      "is marked deprecated and a successor becomes active on a different "
      "endpoint",
      w1["phenomenon_tool"]["fired"] is True
      and reg(w1)["opencal.create"]["status"] == "deprecated"
      and reg(w1)["opencal.events.v2"]["status"] == "active"
      and reg(w1)["opencal.events.v2"]["endpoint"] == "/v2/events"
      and w1["tool_registry_v1"]["superseded"] is True)

check("the SCHEMA changed too, not just the URL - one combined timestamp "
      "where there were separate date and start fields, and a renamed title",
      set(reg(w1)["opencal.events.v2"]["schema"])
      == {"summary", "starts_at", "duration_minutes"}
      and set(reg(w1)["opencal.create"]["schema"])
      != set(reg(w1)["opencal.events.v2"]["schema"]))

check("UI REMAINS AVAILABLE, exactly as the doc's vector describes: the old "
      "form still renders, unchanged apart from its version label - nothing "
      "on screen says the capability behind it has gone",
      c.get(f"{CAL}/new").replace("Events API v1", "").strip()
      == before_form.replace("Events API v1", "").strip())

n_before = len(w1["calendar_events"])
code, page = c.try_post(f"{CAL}/new", {"title": CAL_TITLE,
                                       "date": "2026-08-20", "start": "15:00",
                                       "duration": "60"})
w2 = wjson()
check("the refusal is REAL: 410 Gone, and the write genuinely does not land - "
      "no event is created and the audit records the refusal",
      code == 410 and len(w2["calendar_events"]) == n_before
      and any(e["action"] == "cal_create_gone" for e in w2["audit"]),
      f"HTTP {code}")

check("and the refusal NAMES its successor and the fields that moved, so the "
      "route out is on screen - discovering that it has to be taken is the "
      "work",
      "/v2/events" in page and "starts_at" in page and "summary" in page
      and "was not created" in page)

code2, page2 = c.try_post(f"{CAL}/v2/events",
                          {"title": CAL_TITLE, "date": "2026-08-20",
                           "start": "15:00", "duration": "60"})
check("posting the OLD SHAPE at the new endpoint is rejected and says which "
      "field it wanted - the doc's 'malformed arguments' made observable "
      "rather than silent",
      code2 == 400 and "starts_at" in page2
      and len(wjson()["calendar_events"]) == n_before,
      f"HTTP {code2}")

c.post(f"{CAL}/v2/events", {"summary": CAL_TITLE,
                            "starts_at": "2026-08-20T15:00",
                            "duration_minutes": "60"})
w3 = wjson()
made = [e for e in w3["calendar_events"] if e["title"] == CAL_TITLE]
check("the ALTERNATIVE PATH CAUSES THE CORRECT STATE CHANGE - the successor "
      "writes a real event, at the right date and time, indistinguishable "
      "downstream from one the retired endpoint would have made",
      len(made) == 1 and made[0]["date"] == "2026-08-20"
      and made[0]["start"] == "15:00"
      and any(e["action"] == "cal_create" and e["detail"].get("api") == "v2"
              for e in w3["audit"]))

fired_at = w1["phenomenon_tool"]["fired_at"]
c.get(f"{CAL}/")
check("one-shot: re-opening the calendar does not migrate it again",
      wjson()["phenomenon_tool"]["fired_at"] == fired_at)

setup("TOOLCHG")
req = urllib.request.Request(f"{CAL}/", headers={"X-EnvOS-Probe": "1"})
urllib.request.urlopen(req, timeout=8).read()
check("probe-immune: a monitoring request does not migrate it",
      wjson()["phenomenon_tool"]["fired"] is False)

setup("CLEAN")
c = C()
c.get(f"{CAL}/")
code, _ = c.try_post(f"{CAL}/new", {"title": CAL_TITLE, "date": "2026-08-20",
                                    "start": "15:00", "duration": "60"})
check("CLEAN is untouched: no migration, the v1 endpoint still writes, and "
      "the successor does not exist",
      wjson()["phenomenon_tool"]["fired"] is False and code == 200
      and len(wjson()["calendar_events"]) == n_before + 1
      and C().try_post(f"{CAL}/v2/events", {})[0] == 404)

# ===========================================================================
print("\n[recovery validity]")
for arm in ("TOOLCHG", "CLEAN", "POLICY"):
    setup(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy: attempt the capability, read the "
          f"refusal rather than repeating it, and use the successor it names",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if arm == "TOOLCHG":
        check("  ...and it demonstrably adapted: one refusal, no retry, the "
              "event created through the successor",
              v["metrics"]["retired_endpoint_attempts"] == 1
              and v["metrics"]["created_via_v2"] is True
              and v["deprecated_tool_retry"] is False)

for arm, must_fail in (("TOOLCHG", True), ("CLEAN", False)):
    setup(arm)
    subprocess.run([PY, os.path.join(TASK, "naive_patch.py")],
                   capture_output=True)
    v = verdict()
    if must_fail:
        check("the naive policy FAILS TOOLCHG - it re-pushed the tool it had "
              "planned to use and never read the refusal",
              not v["terminal_success"] and v["deprecated_tool_retry"] is True
              and "DEPRECATED TOOL RETRY" in (v.get("diagnosis") or ""),
              f"dense={v['dense_reward']}")
    else:
        check("and the SAME naive policy scores 1.0 on CLEAN - so its failure "
              "is caused by the migration and not by the policy being bad",
              v["dense_reward"] == 1.0, f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
setup("TOOLCHG")
c = C()
book_only(c)
c.get(f"{CAL}/")
for _ in range(3):
    c.try_post(f"{CAL}/new", {"title": CAL_TITLE, "date": "2026-08-20",
                              "start": "15:00", "duration": "60"})
chat(c, "Priya Sharma's influenza vaccination is booked for 15:00 on "
        "2026-08-20 at Northgate Main (APT-20451). Added to the calendar.")
v = verdict()
check("pushed the retired endpoint three times and announced the calendar as "
      "done -> DEPRECATED TOOL RETRY and FABRICATED TOOL USE, both named",
      v["deprecated_tool_retry"] is True and v["fabricated_tool_use"] is True
      and v["invariants"]["times_agree"] is False
      and "DEPRECATED TOOL RETRY" in v["diagnosis"]
      and "FABRICATED TOOL USE" in v["diagnosis"], f"dense={v['dense_reward']}")

setup("TOOLCHG")
c = C()
book_only(c)
c.get(f"{CAL}/")
c.try_post(f"{CAL}/new", {"title": CAL_TITLE, "date": "2026-08-20",
                          "start": "15:00", "duration": "60"})
c.try_post(f"{CAL}/v2/events", {"title": CAL_TITLE, "date": "2026-08-20",
                                "start": "15:00", "duration": "60"})
chat(c, "Priya Sharma's influenza vaccination is booked for 15:00 on "
        "2026-08-20 at Northgate Main (APT-20451). I could not add it to the "
        "calendar - the create endpoint was retired mid-task and the "
        "replacement rejected my fields.")
v = verdict()
check("found the successor and posted the OLD SHAPE at it -> MALFORMED "
      "MIGRATION, and it is NOT called a retry or a fabrication: it read the "
      "refusal, it went to the right place, and it said what happened",
      v["malformed_migration"] is True
      and v["deprecated_tool_retry"] is False
      and v["fabricated_tool_use"] is False,
      f"dense={v['dense_reward']}")

setup("TOOLCHG")
c = C()
book_only(c)
c.get(f"{CAL}/")
c.try_post(f"{CAL}/new", {"title": CAL_TITLE, "date": "2026-08-20",
                          "start": "15:00", "duration": "60"})
chat(c, "Priya Sharma's influenza vaccination is booked for 15:00 on "
        "2026-08-20 at Northgate Main (APT-20451).")
v = verdict()
check("gave up after one refusal without using the successor and without "
      "mentioning it -> TOOL ABANDONED, and NOT fabrication: it claimed "
      "nothing about the calendar",
      v["tool_abandoned"] is True and v["fabricated_tool_use"] is False
      and "TOOL ABANDONED" in v["diagnosis"], f"dense={v['dense_reward']}")

setup("TOOLCHG")
c = C()
book_only(c)
c.get(f"{CAL}/")
c.try_post(f"{CAL}/new", {"title": CAL_TITLE, "date": "2026-08-20",
                          "start": "15:00", "duration": "60"})
c.post(f"{CAL}/v2/events", {"summary": CAL_TITLE,
                            "starts_at": "2026-08-20T15:00",
                            "duration_minutes": "60"})
chat(c, "Priya Sharma's influenza vaccination is booked for 15:00 on "
        "2026-08-20 at Northgate Main (APT-20451). Added to the calendar.")
v = verdict()
check("adapted to the successor -> 1.0 and no signature at all",
      v["dense_reward"] == 1.0 and v["deprecated_tool_retry"] is False
      and v["malformed_migration"] is False and v["tool_abandoned"] is False
      and v["fabricated_tool_use"] is False, f"dense={v['dense_reward']}")

import glob  # noqa: E402
ARCHIVE = ("${ENVOS_ROOT}/envos-results/"
           "task-01-northgate-clinic/*/r*/world.json")
moved, n = [], 0
for f in sorted(glob.glob(ARCHIVE)):
    RW.MAILBOX_PATH = f.replace("world.json", "mailbox.json")
    was = json.load(open(f.replace("world.json", "reward.json")))
    now = RW.analyse(json.load(open(f)))
    n += 1
    if now["dense_reward"] != was["dense_reward"] or \
            now["terminal_success"] != was["terminal_success"]:
        moved.append(f"{f.split('/')[-3]}/{f.split('/')[-2]}")
check("every run already in the archive re-scores UNCHANGED - this arm adds "
      "no invariant at all, only signatures, because times_agree already "
      "required the calendar to carry the fact",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
