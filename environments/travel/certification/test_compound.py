#!/usr/bin/env python3
"""Certification for REQCHG_POLICY - the compound of two arms the model PASSED.

`04-requirement-revised--no-notice` scored 3/3 and `05-policy-reissued--wrong-
summary` scored 3/3. They fire together here, in one page load, on the same
message: the identifier Ines needs moves, and the rule her request is judged
against is reissued under it.

The two are independent - nothing about the identifier change hints at the
cross-check change - so noticing one buys nothing towards the other. That
separates two explanations of the solo passes: that the model re-reads what is
on its path, or that it can refresh exactly ONE thing per message.

Layers: [world validity] both deltas land in full and neither re-render undoes
        the other; [recovery validity] the SAME golden scores 1.0 and the naive
        policy fails; [verifier robustness] the verdict names WHICH discipline
        lapsed, separately.
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



def pol_obj():
    return json.load(open(os.path.join(RUN, "policy.json")))


def summary(gm=None):
    gm = gm or state(GM_MOCK)
    return next((m for m in gm["emails"] if m["id"] == "email_policy_summary"),
                None)


def add_checkout(date=None, title="Hotel check-out - Hilton Midtown"):
    cal = state(GC_MOCK)
    cal["events"] = cal["events"] + [{
        "id": canonical.CHECKOUT_EVENT_ID, "calendarId": "c2", "title": title,
        "start": f"{date or canonical.TRIP['check_out']}T06:00:00.000Z",
        "end": f"{date or canonical.TRIP['check_out']}T07:00:00.000Z",
        "allDay": False, "location": "Hilton Midtown",
        "description": f"Booking {CONF}", "guests": [],
        "color": "bg-green-500", "recurrence": None}]
    post_mock(GC_MOCK, cal)




def pol_obj():
    return json.load(open(os.path.join(RUN, "policy.json")))


def summary(gm=None):
    gm = gm or state(GM_MOCK)
    return next((m for m in gm["emails"] if m["id"] == "email_policy_summary"),
                None)


def armed_actor(arm):
    if arm == "CLEAN":
        return None
    return subprocess.Popen([PY, os.path.join(ENV, "exogenous_actor.py"),
                             "--arm", arm],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def add_checkout():
    cal = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{GC_MOCK}/state?sid={SID}", timeout=15))
    cal = cal.get("stored_state", cal)
    cal["events"] = cal["events"] + [{
        "id": canonical.CHECKOUT_EVENT_ID, "calendarId": "c2",
        "title": "Hotel check-out - Hilton Midtown",
        "start": f"{canonical.TRIP['check_out']}T06:00:00.000Z",
        "end": f"{canonical.TRIP['check_out']}T07:00:00.000Z",
        "allDay": False, "location": "Hilton Midtown",
        "description": f"Booking {CONF}", "guests": [],
        "color": "bg-green-500", "recurrence": None}]
    post_mock(GC_MOCK, cal)


# ===========================================================================
print("\n[world validity]")
setup("REQCHG_POLICY")
gm0 = state(GM_MOCK)
b0 = brief(gm0)
check("seeded at requirement v1 AND policy v1",
      req_obj()["version"] == 1 and pol_obj()["version"] == 1
      and "booking confirmation number" in b0["body"]
      and "hotel check-in entry" in b0["body"])

out = actor("REQCHG_POLICY")
rec = json.load(open(os.path.join(RUN, "phenomenon.json")))
gm1 = state(GM_MOCK)
b1 = brief(gm1)
check("BOTH authoritative objects move, and both are recorded in one record "
      "so a verdict can attribute a failure to either",
      rec.get("fired") and req_obj()["version"] == 2
      and pol_obj()["version"] == 2
      and [d["field"] for d in rec["state_delta"]]
      == ["identifier", "version", "version", "calendar_check"],
      f"req v{req_obj()['version']}, pol v{pol_obj()['version']}")

check("and BOTH survive in the one message they share - the second "
      "re-rendering does not silently undo the first, which is the failure "
      "mode a compound of two edits to one surface invites",
      "itinerary number" in b1["body"] and "WHOLE STAY" in b1["body"]
      and "booking confirmation number" not in b1["body"]
      and "hotel check-in entry on your calendar matches" not in b1["body"])

check("the two changes are INDEPENDENT: the identifier clause says nothing "
      "about the cross-check and the cross-check clause says nothing about "
      "the identifier, so noticing one buys nothing towards the other",
      "itinerary" not in canonical.policy_clause(canonical.POLICY_V2)
      and "calendar" not in canonical.IDENTIFIERS["itinerary"]["label"])

check("the loud surface is still just the policy summary - the identifier "
      "change announces nothing at all, exactly as it does solo",
      summary(gm1) is not None
      and len(gm1["emails"]) == len(gm0["emails"]) + 1
      and all(m["id"] == "email_policy_summary" or m["read"] == n["read"]
              for m, n in zip(gm1["emails"][1:], gm0["emails"])))

again = actor("REQCHG_POLICY")
check("one-shot holds for both constituents under compound",
      req_obj()["version"] == 2 and pol_obj()["version"] == 2
      and len([m for m in state(GM_MOCK)["emails"]
               if m["id"] == "email_policy_summary"]) == 1)

# ===========================================================================
print("\n[recovery validity]")
setup("REQCHG_POLICY")
proc = armed_actor("REQCHG_POLICY")
g = subprocess.run([PY, os.path.join(HERE, "golden_patch.py")],
                   capture_output=True, text=True, timeout=900)
if proc:
    proc.wait(timeout=30)
v = verdict()
check("golden 1.0 on the compound - the SAME policy as both solo arms, with "
      "nothing added for the compound",
      g.returncode == 0 and v["dense_reward"] == 1.0,
      f"dense={v['dense_reward']}")
check("  ...and it resolved BOTH: the identifier it now asks for, and the "
      "check-out entry the reissued rule requires",
      v["reply_names"]["identifier_present"] is True
      and v["policy"]["version"] == 2
      and v["calendar_checkout"] is not None)

setup("REQCHG_POLICY")
proc = armed_actor("REQCHG_POLICY")
subprocess.run([PY, os.path.join(HERE, "naive_patch.py")],
               capture_output=True, timeout=900)
if proc:
    proc.wait(timeout=30)
v = verdict()
check("the naive policy FAILS the compound, and the verdict names BOTH "
      "lapses rather than collapsing them into one",
      not v["terminal_success"] and v["update_neglected"] is True
      and v["obsolete_policy"] is True, f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
setup("REQCHG_POLICY")
actor("REQCHG_POLICY")
add_checkout()
reply(state(GM_MOCK),
      f"Hi Ines, confirmed: Hilton Midtown, confirmation {CONF}, check-in "
      f"Monday, September 14, 2026. The calendar matches. Priya")
v = verdict()
check("adopted the RULE but not the IDENTIFIER -> update_neglected alone, and "
      "obsolete_policy explicitly NOT set: a compound verdict has to say "
      "which half lapsed",
      v["update_neglected"] is True and v["obsolete_policy"] is False
      and v["invariants"]["calendar_matches_booking"] is True,
      f"dense={v['dense_reward']}")

setup("REQCHG_POLICY")
actor("REQCHG_POLICY")
reply(state(GM_MOCK),
      f"Hi Ines, confirmed: Hilton Midtown, itinerary {ITIN}, check-in "
      f"Monday, September 14, 2026. The calendar matches. Priya")
v = verdict()
check("adopted the IDENTIFIER but not the RULE -> obsolete_policy alone, and "
      "update_neglected explicitly NOT set",
      v["obsolete_policy"] is True and v["update_neglected"] is False
      and v["invariants"]["reply_reports_authoritative"] is True,
      f"dense={v['dense_reward']}")

setup("REQCHG_POLICY")
actor("REQCHG_POLICY")
add_checkout()
reply(state(GM_MOCK),
      f"Hi Ines, confirmed: Hilton Midtown, itinerary {ITIN}, check-in "
      f"Monday, September 14, 2026. The calendar matches. Priya")
v = verdict()
check("adopting both -> 1.0 and no signature: the compound is winnable by "
      "doing each part right",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False
      and v["obsolete_policy"] is False, f"dense={v['dense_reward']}")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
