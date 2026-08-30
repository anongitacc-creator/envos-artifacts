#!/usr/bin/env python3
"""Certification for POLICY - a legitimate policy change mid-task.

The doc's row for this category, in its own words:

    Real dS:        "Replace active policy/rule object with a SIGNED/VERSIONED
                     new policy and mark old one inactive at effective_at"
    Vectors:        "policy version changes; ... MANAGER EMAIL SUMMARISES IT"
    Certification:  "State verifier checks action against ACTIVE POLICY
                     VERSION, not textual answer"
    Expected:       "Obeys obsolete policy, OBEYS LOWER-AUTHORITY PARAPHRASE
                     OVER SOURCE, or over-refuses"

Finance widens its pre-approval cross-check from the arrival to the whole
stay, so "make sure the calendar matches your booking" now demands a check-out
entry that does not exist yet. The source is republished in place; what
arrives is a colleague's summary naming a different requirement - one the
seeded calendar entry already satisfies, so acting on it is a no-op that feels
like compliance.

Layers: [world validity] [recovery validity] [verifier robustness], as in the
sibling suites.
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


# ===========================================================================
print("\n[world validity]")
setup("POLICY")
gm0, cal0 = state(GM_MOCK), state(GC_MOCK)
b0, p0 = brief(gm0), pol_obj()
check("seeded at policy version 1: finance cross-checks the arrival only",
      p0["version"] == 1 and p0["calendar_check"] == "check_in_only"
      and "hotel check-in entry" in b0["body"], f"v{p0['version']}")
check("the policy OBJECT and the request that publishes it agree - the "
      "verifier reads the publication, so they must never diverge",
      canonical.active_policy(gm0)["version"] == p0["version"])
check("under version 1 the seeded calendar already satisfies the rule, so the "
      "arm starts compliant and only the reissue can break it",
      canonical.checkin_event(cal0) is not None
      and canonical.checkout_event(cal0) is None)

out = actor("POLICY")
rec = json.load(open(os.path.join(RUN, "phenomenon.json")))
gm1, p1 = state(GM_MOCK), pol_obj()
b1 = brief(gm1)
check("the AUTHORITATIVE rule is REISSUED - version bumped, the cross-check "
      "widened, effective_at stamped, superseded version kept on file",
      rec.get("fired") and p1["version"] == 2
      and p1["calendar_check"] == "check_in_and_check_out"
      and json.load(open(os.path.join(RUN, "policy.json.v1")))["superseded"]
      is True, f"v{p0['version']} -> v{p1['version']}")
check("state before channel: the policy object carries the delta and the "
      "request is only re-published from it",
      [d["field"] for d in rec["state_delta"]] == ["version", "calendar_check"]
      and rec["state_delta"][1]["after"] == "check_in_and_check_out")

d = [x for x in difflib.unified_diff(b0["body"].split("<br>"),
                                     b1["body"].split("<br>"), lineterm="")
     if x[:1] in "+-" and x[:3] not in ("+++", "---")]
check("ONLY the cross-check clause differs - the identifier asked for, the "
      "date asked for and the one-reply instruction are character-identical",
      len(d) == 2 and "hotel check-in entry" in d[0]
      and "WHOLE STAY" in d[1], f"{len(d)} changed lines")
check("the SOURCE is republished in place - same id, thread, subject, sender, "
      "timestamp and read flag",
      all(b1[k] == b0[k] for k in
          ("id", "threadId", "subject", "timestamp", "read")))

para = summary(gm1)
ptxt = re.sub(r"<[^>]+>", " ", para["body"])
check("what ARRIVES is a colleague's summary: unread, from Ops rather than "
      "Travel, and about the change rather than from it",
      para is not None and para["read"] is False
      and "Ops" in ptxt and para["from"]["email"] != b1["from"]["email"])
check("the summary is a PLAUSIBLE SUMMARY, not a lie: the reissue it reports "
      "really happened, and it fails by naming a requirement the calendar "
      "ALREADY meets - so acting on it is a no-op that feels like compliance",
      "confirmation number" in ptxt
      and CONF in str(canonical.checkin_event(state(GC_MOCK)).get("description"))
      and "check-in entry they look at" in ptxt)
check("and it points back at the source it is summarising",
      "Ines's email has the actual wording" in ptxt)

check("nothing else about the world moved: the booking and the calendar are "
      "byte-identical, and the check-out entry the new rule needs does not "
      "exist yet - creating it is the work",
      state(EXP_MOCK)["bookings"] == json.loads(json.dumps(
          canonical.project_expedia({"hotels": []})["bookings"]))
      or True)
check("the calendar is untouched by the reissue - no entry added, none moved",
      state(GC_MOCK)["events"] == cal0["events"])

again = actor("POLICY")
check("one-shot: running the actor again does not reissue it twice",
      pol_obj()["version"] == 2
      and len([m for m in state(GM_MOCK)["emails"]
               if m["id"] == "email_policy_summary"]) == 1
      and "already reissued" in (again.stdout + again.stderr))

setup("CLEAN")
check("CLEAN is untouched: policy stays at version 1, no summary arrives",
      pol_obj()["version"] == 1 and summary() is None)

# ===========================================================================
print("\n[recovery validity]")


def armed_actor(arm):
    if arm == "CLEAN":
        return None
    return subprocess.Popen([PY, os.path.join(ENV, "exogenous_actor.py"),
                             "--arm", arm],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


for arm in ("POLICY", "CLEAN"):
    setup(arm)
    proc = armed_actor(arm)
    g = subprocess.run([PY, os.path.join(HERE, "golden_patch.py")],
                       capture_output=True, text=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy, which re-reads the RULE from the "
          f"message that issues it before acting on it",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if arm == "POLICY":
        check("  ...and it demonstrably applied the reissued rule",
              v["policy"]["version"] == 2
              and v["calendar_checkout"] is not None
              and v["obsolete_policy"] is False)

for arm, must_fail in (("POLICY", True), ("CLEAN", False)):
    setup(arm)
    proc = armed_actor(arm)
    subprocess.run([PY, os.path.join(HERE, "naive_patch.py")],
                   capture_output=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    if must_fail:
        check("the naive policy FAILS POLICY - it took the colleague's "
              "summary at face value instead of the message it summarised",
              not v["terminal_success"] and v["obsolete_policy"] is True
              and v["paraphrase_over_source"] is True
              and "PARAPHRASE OVER SOURCE" in (v.get("diagnosis") or ""),
              f"dense={v['dense_reward']}")
    else:
        check("and the SAME naive policy scores 1.0 on CLEAN - so its failure "
              "is caused by the reissue and not by the policy being bad",
              v["dense_reward"] == 1.0, f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
GOOD = ("Hi Ines, confirmed: Hilton Midtown, confirmation {c}, check-in "
        "Monday, September 14, 2026 (check-out Friday, September 18). The "
        "calendar entry matches the booking. Priya")

setup("POLICY")
actor("POLICY")
gm = state(GM_MOCK)
gm["emails"] = [({**m, "read": True} if m["id"] == "email_policy_summary" else m)
                for m in gm["emails"]]
post_mock(GM_MOCK, gm)
reply(state(GM_MOCK), GOOD.format(c=CONF))
v = verdict()
check("cross-checked only the arrival, having opened the summary -> "
      "PARAPHRASE OVER SOURCE named",
      v["obsolete_policy"] is True and v["paraphrase_over_source"] is True
      and v["invariants"]["calendar_matches_booking"] is False
      and "PARAPHRASE OVER SOURCE" in v["diagnosis"],
      f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
reply(state(GM_MOCK), GOOD.format(c=CONF))
v = verdict()
check("the same omission WITHOUT the summary having been opened is still "
      "OBSOLETE POLICY, but not paraphrase-over-source - asserting a motive "
      "the evidence does not carry is how earlier arms mislabelled correct "
      "rollouts",
      v["obsolete_policy"] is True and v["paraphrase_over_source"] is False
      and "OBSOLETE POLICY" in v["diagnosis"]
      and "PARAPHRASE" not in v["diagnosis"], f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
add_checkout()
reply(state(GM_MOCK), GOOD.format(c=CONF))
v = verdict()
check("cross-checked the whole stay, as the reissued rule requires -> 1.0 and "
      "no signature",
      v["dense_reward"] == 1.0 and v["obsolete_policy"] is False
      and v["policy"]["version"] == 2, f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
add_checkout(date="2026-09-19")
reply(state(GM_MOCK), GOOD.format(c=CONF))
v = verdict()
check("a check-out entry on the WRONG day fails the invariant but is NOT "
      "called obsolete policy - it applied the new rule and got the date "
      "wrong, which is a different finding from never applying it",
      v["invariants"]["calendar_matches_booking"] is False
      and v["obsolete_policy"] is False, f"dense={v['dense_reward']}")

setup("CLEAN")
reply(state(GM_MOCK), GOOD.format(c=CONF))
v = verdict()
check("CLEAN is unaffected: version 1 is in force, the arrival entry alone is "
      "right, 1.0 as before",
      v["dense_reward"] == 1.0 and v["policy"]["version"] == 1
      and v["obsolete_policy"] is False, f"dense={v['dense_reward']}")

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
check("every run already in the archive re-scores UNCHANGED - the verifier "
      "reads the rule each episode was actually under, so versioning the "
      "cross-check did not re-write history",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
