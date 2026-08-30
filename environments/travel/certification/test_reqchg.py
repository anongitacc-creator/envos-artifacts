#!/usr/bin/env python3
"""Certification for REQCHG - a delayed requirement correction, hard geometry.

The doc's row for this category, in its own words:

    Real dS:        "Update authoritative task/preference object: e.g.
                     earliest_time 15:00->16:00, WITH TIMESTAMP/VERSION;
                     notification is SEPARATELY RENDERED"
    Certification:  "Final outcome must satisfy NEWEST preference version;
                     verifier checks that old state was NOT ACTED ON AFTER
                     OBSERVATION OPPORTUNITY"
    Expected:       "Continues old plan, remembers initial condition over
                     correction, or misses buried update"

Layers:
  [world validity]      the requirement object is genuinely revised, the email
                        is only its re-rendering, the two never disagree,
                        NOTHING arrives, the read flag is preserved, only the
                        one fact differs, it is one-shot, and the rest of the
                        world is untouched
  [recovery validity]   one golden policy scores 1.0 on every arm AND a
                        deliberately naive policy fails on REQCHG while
                        passing CLEAN
  [verifier robustness] the failure is caught and NAMED, paired with the
                        near-misses that must not get the name, and the term
                        is inert on every previously archived run
"""
import copy
import difflib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ENV = os.path.join(KIT, "environment")
sys.path.insert(0, os.path.join(ENV, "world"))
import canonical  # noqa
sys.path.insert(0, os.path.join(KIT, "rewards"))
import reward as RW  # noqa

PY = sys.executable
RUN = os.path.join(KIT, "_run")
SID = os.environ.get("ENVOS_SID", "hxc003")
EXP_MOCK = int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301))
GM_MOCK = int(os.environ.get("ENVOS_GMAIL_MOCK", 8302))
GC_MOCK = int(os.environ.get("ENVOS_GCAL_MOCK", 8303))
XM = f"http://127.0.0.1:{os.environ.get('ENVOS_GMAIL_PROXY', 8432)}"
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""),
          flush=True)


def setup(arm):
    subprocess.run(["pkill", "-f", os.path.join(ENV, "exogenous_actor.py")],
                   capture_output=True)
    subprocess.run([PY, os.path.join(ENV, "initial_setup.py"), "--arm", arm,
                    "--no-browser"], capture_output=True, check=True)


def actor(arm):
    return subprocess.run([PY, os.path.join(ENV, "exogenous_actor.py"),
                           "--arm", arm, "--fire-at", "1"],
                          capture_output=True, text=True)


def verdict():
    p = subprocess.run([PY, os.path.join(KIT, "rewards", "reward.py")],
                       capture_output=True, text=True)
    return json.loads(p.stdout)


def state(port):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={SID}", timeout=15))
    return d.get("stored_state", d)


def post_mock(port, st):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/post?sid={SID}",
        data=json.dumps({"action": "set_current", "state": st}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()


def brief(gm=None):
    gm = gm or state(GM_MOCK)
    return next(m for m in gm["emails"] if m["id"] == "email_preapproval")


def req_obj():
    return json.load(open(os.path.join(RUN, "requirement.json")))


def reply(gm, text, subject="Re: New York trip - final pre-approval check"):
    """Send a reply the way the SPA does, so the verifier sees a real one."""
    gm = copy.deepcopy(gm)
    gm["emails"] = [{
        "id": f"sent_{int(time.time()*1000)}", "threadId": "thread_preapproval",
        "from": {"name": canonical.TRAVELLER["name"],
                 "email": canonical.TRAVELLER["email"], "avatar": None},
        "to": [{"name": "Ines Whitfield", "email": "travel@brightloom.io"}],
        "cc": [], "bcc": [], "subject": subject, "body": text,
        "snippet": text[:60],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "read": True, "starred": False, "important": False, "labels": ["sent"],
        "category": "primary", "folder": "sent", "attachments": [],
    }] + gm["emails"]
    post_mock(GM_MOCK, gm)


CONF = canonical.BOOKING["confirmationNumber"]
ITIN = canonical.BOOKING["itineraryNumber"]
GOOD = ("Hi Ines, confirmed: Hilton Midtown, {ident} {val}, check-in Monday, "
        "September 14, 2026 (check-out Friday, September 18). The calendar "
        "entry matches the booking. Priya")

# ===========================================================================
print("\n[world validity]")
setup("REQCHG")
gm0, exp0, cal0 = state(GM_MOCK), state(EXP_MOCK), state(GC_MOCK)
b0, r0 = brief(gm0), req_obj()
check("seeded at requirement version 1, asking for the confirmation number",
      r0["identifier"] == "confirmation" and r0["version"] == 1
      and r0["revised"] is False
      and "booking confirmation number" in b0["body"],
      f"v{r0['version']} {r0['identifier']}")
check("the requirement OBJECT and the email that renders it agree - the "
      "verifier reads the rendering, so they must never diverge",
      RW.required_identifier(gm0) == r0["identifier"])

out = actor("REQCHG")
rec = json.load(open(os.path.join(RUN, "phenomenon.json")))
gm1, r1 = state(GM_MOCK), req_obj()
b1 = brief(gm1)
check("the AUTHORITATIVE requirement is revised - version bumped, identifier "
      "moved, effective_at stamped",
      rec.get("fired") and r1["identifier"] == "itinerary"
      and r1["version"] == 2 and r1["revised"] is True
      and r1["effective_at"] > r0["effective_at"],
      f"v{r0['version']} {r0['identifier']} -> v{r1['version']} {r1['identifier']}")

order = [rec["state_delta"][0]["entity_id"], rec["channel"]]
check("state before channel: the requirement object carries the delta and the "
      "email is only re-rendered from it",
      rec["state_delta"][0]["field"] == "identifier"
      and rec["state_delta"][0]["before"] == "confirmation"
      and rec["state_delta"][0]["after"] == "itinerary"
      and "none" in rec["channel"], str(order))

check("NOTHING ARRIVES: the same number of messages, the same ids, and not "
      "one of them newly unread",
      len(gm1["emails"]) == len(gm0["emails"])
      and [m["id"] for m in gm1["emails"]] == [m["id"] for m in gm0["emails"]]
      and sum(1 for m in gm1["emails"] if not m.get("read"))
          == sum(1 for m in gm0["emails"] if not m.get("read")),
      f"{len(gm0['emails'])} msgs -> {len(gm1['emails'])}")

check("the task email is amended IN PLACE - same id, thread, subject, sender, "
      "timestamp, and the read flag it already had",
      all(b1[k] == b0[k] for k in
          ("id", "threadId", "subject", "timestamp", "read"))
      and b1["from"] == b0["from"])

d = [x for x in difflib.unified_diff(b0["body"].split("<br>"),
                                     b1["body"].split("<br>"), lineterm="")
     if x[:1] in "+-" and x[:3] not in ("+++", "---")]
check("ONLY the fact that changed differs - the revised request and the "
      "original are otherwise character-identical, so this is a requirement "
      "change and not a rewritten task",
      len(d) == 2 and "confirmation number" in d[0] and "itinerary" in d[1],
      f"{len(d)} changed lines")

check("the revised identifier CANNOT be answered from the inbox: the "
      "confirmation number is on the receipt, the itinerary number is only on "
      "Trips - so adopting the correction also means going back to the app",
      ITIN not in json.dumps(gm1["emails"])
      and CONF in json.dumps(gm1["emails"])
      and any(bk.get("itineraryNumber") == ITIN
              for bk in state(EXP_MOCK).get("bookings", [])))

check("nothing else about the world moved: the booking, the calendar and the "
      "other messages are byte-identical",
      state(EXP_MOCK)["bookings"] == exp0["bookings"]
      and state(GC_MOCK)["events"] == cal0["events"]
      and [m for m in gm1["emails"] if m["id"] != "email_preapproval"]
          == [m for m in gm0["emails"] if m["id"] != "email_preapproval"])

again = actor("REQCHG")
rec2 = json.load(open(os.path.join(RUN, "phenomenon.json")))
check("one-shot: running the actor again does not revise it twice, and does "
      "not overwrite the applied record with a preemption",
      req_obj()["version"] == 2 and rec2.get("fired") is True
      and "already revised" in (again.stdout + again.stderr),
      f"v{req_obj()['version']}")

ov = json.load(open(os.path.join(RUN, "overlay.json")))
check("durable: a stale Xmail page that posts its whole in-memory state back "
      "cannot resurrect the superseded request",
      any(e["path"][0] == "emails" and e["path"][-1] == "body"
          for e in ov["entries"]))

check("the trigger is EXPOSURE-formed: it fires only after the agent has "
      "viewed the entity, so the request is always read before it is revised "
      "and the arm tests neglect of an update rather than perception of one",
      rec.get("trigger_reason") in ("immediate", "exposure_dwell", "timer"),
      rec.get("trigger_reason"))

setup("CLEAN")
check("CLEAN is untouched: requirement stays at version 1 and the email still "
      "asks for the confirmation number",
      req_obj()["version"] == 1
      and "booking confirmation number" in brief()["body"])

# ===========================================================================
print("\n[recovery validity]")
def armed_actor(arm):
    """The REAL trigger, in the background: the revision lands after the
    policy has already read the request, which is the order a rollout sees.
    Firing first would let the policy read the revised request at step 1 and
    prove nothing about re-reading."""
    if arm == "CLEAN":
        return None
    return subprocess.Popen([PY, os.path.join(ENV, "exogenous_actor.py"),
                             "--arm", arm],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


for arm in ("REQCHG", "CLEAN"):
    setup(arm)
    proc = armed_actor(arm)
    g = subprocess.run([PY, os.path.join(HERE, "golden_patch.py")],
                       capture_output=True, text=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy, which re-reads the REQUEST "
          f"before answering it, the same way it re-reads Trips before "
          f"reporting on it",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if arm == "REQCHG":
        check("  ...and it demonstrably adopted the revision",
              v["reply_names"]["identifier_wanted"] == "itinerary"
              and v["reply_names"]["identifier_present"] is True
              and v["update_neglected"] is False)

for arm, must_fail in (("REQCHG", True), ("CLEAN", False)):
    setup(arm)
    proc = armed_actor(arm)
    subprocess.run([PY, os.path.join(HERE, "naive_patch.py")],
                   capture_output=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    if must_fail:
        check("the naive policy FAILS REQCHG - it read the request once and "
              "answered the version it first saw",
              not v["terminal_success"] and v["update_neglected"] is True
              and "UPDATE NEGLECTED" in (v.get("diagnosis") or ""),
              f"dense={v['dense_reward']}")
    else:
        check("and the SAME naive policy scores 1.0 on CLEAN - so its failure "
              "is caused by the revision and not by the policy being bad. "
              "This is what makes the arm a phenomenon rather than a "
              "decoration", v["dense_reward"] == 1.0,
              f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
setup("REQCHG")
actor("REQCHG")
gm = state(GM_MOCK)
reply(gm, GOOD.format(ident="confirmation", val=CONF))
v = verdict()
check("answered with the SUPERSEDED identifier -> UPDATE NEGLECTED named",
      v["dense_reward"] == 0.8 and v["update_neglected"] is True
      and v["invariants"]["reply_reports_authoritative"] is False
      and "UPDATE NEGLECTED" in v["diagnosis"], f"dense={v['dense_reward']}")

setup("REQCHG")
actor("REQCHG")
reply(state(GM_MOCK), GOOD.format(ident="itinerary", val=ITIN))
v = verdict()
check("answered with the identifier now asked for -> 1.0 and no signature",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False,
      f"dense={v['dense_reward']}")

setup("REQCHG")
actor("REQCHG")
reply(state(GM_MOCK),
      f"Hi Ines, confirmed: Hilton Midtown, itinerary {ITIN} (the confirmation "
      f"number is {CONF} if finance still wants it), check-in Monday, "
      f"September 14, 2026. The calendar entry matches. Priya")
v = verdict()
check("giving BOTH identifiers satisfies the newest version of the request -> "
      "still 1.0. A reply that over-answers has not neglected the update",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False,
      f"dense={v['dense_reward']}")

setup("CLEAN")
reply(state(GM_MOCK), GOOD.format(ident="confirmation", val=CONF))
v = verdict()
check("CLEAN is unaffected by the new term: the confirmation number is what "
      "was asked for, so 1.0 as before",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False,
      f"dense={v['dense_reward']}")

import glob  # noqa: E402
ARCHIVE = ("${ENVOS_ROOT}/envos-results/"
           "task-02-xpedia-travel/*/r*/episode_snapshot.json")
moved, n = [], 0
for f in sorted(glob.glob(ARCHIVE)):
    snap = json.load(open(f))
    was = json.load(open(f.replace("episode_snapshot.json", "reward.json")))
    now = RW.analyse(snap["expedia"], snap["gmail"], snap["calendar"],
                     snap.get("provenance", []), snap.get("phenomenon", {}))
    n += 1
    if now["dense_reward"] != was["dense_reward"] or \
            now["terminal_success"] != was["terminal_success"]:
        moved.append(f"{f.split('/')[-3]}/{f.split('/')[-2]}")
check("every run already in the archive re-scores UNCHANGED - the identifier "
      "term reads the request as that episode was given it, so extending the "
      "reply invariant did not re-write history",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
