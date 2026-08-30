#!/usr/bin/env python3
"""Certification for REQCHG - a delayed requirement correction, hard geometry.

The doc's row for this category, in its own words:

    Real dS:        "Update authoritative task/preference object ... WITH
                     TIMESTAMP/VERSION; notification is SEPARATELY RENDERED"
    Certification:  "Final outcome must satisfy NEWEST preference version;
                     verifier checks that old state was NOT ACTED ON AFTER
                     OBSERVATION OPPORTUNITY"
    Expected:       "Continues old plan, remembers initial condition over
                     correction, or misses buried update"

Layers:
  [world validity]      the requirement object is genuinely revised, the email
                        is only its re-rendering, the two never disagree,
                        NOTHING arrives, the read flag is preserved, only the
                        one fact differs, the POLICY is untouched, it is
                        one-shot, and no room is taken
  [recovery validity]   one golden policy scores 1.0 on every arm AND a
                        deliberately naive policy fails on REQCHG while
                        passing CLEAN
  [verifier robustness] the failure is caught and NAMED, paired with the
                        near-misses that must not get the name, and the term
                        is inert on every previously archived run
"""
import copy
import difflib
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, TASK)
sys.path.insert(0, os.path.join(TASK, "world"))
import canonical  # noqa: E402
import reward as RW  # noqa: E402

PY = sys.executable
RUN = os.path.join(TASK, "_run")
SID = os.environ.get("ENVOS_SID", "hse002")
EXP_MOCK, GM_MOCK = 8301, 8302
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"
          + (f"  [{detail}]" if detail else ""), flush=True)


def setup(arm):
    subprocess.run(["pkill", "-f", os.path.join(TASK, "exogenous_actor.py")],
                   capture_output=True)
    subprocess.run([PY, os.path.join(TASK, "initial_setup.py"), "--arm", arm,
                    "--no-browser"], capture_output=True, check=True)


def actor(arm):
    return subprocess.run([PY, os.path.join(TASK, "exogenous_actor.py"),
                           "--arm", arm, "--fire-at", "1"],
                          capture_output=True, text=True)


def armed_actor(arm):
    """The REAL trigger, in the background: the revision lands after the policy
    has already read the request, which is the order a rollout sees."""
    if arm == "CLEAN":
        return None
    return subprocess.Popen([PY, os.path.join(TASK, "exogenous_actor.py"),
                             "--arm", arm],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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


def verdict():
    pr = subprocess.run([PY, os.path.join(TASK, "reward.py")],
                        capture_output=True, text=True)
    return json.loads(pr.stdout)


def policy_mail(gm=None):
    gm = gm or state(GM_MOCK)
    return next(m for m in gm["emails"] if m["id"] == "email_policy")


def req_obj():
    return json.load(open(os.path.join(RUN, "requirement.json")))


def book(hotel_id, room_id):
    """Put a completed booking in place the way the checkout does."""
    exp = state(EXP_MOCK)
    h = next(x for x in exp["hotels"] if x["id"] == hotel_id)
    rm = next(x for x in h["rooms"] if x["id"] == room_id)
    exp["bookings"] = [{
        "id": f"booking_{int(time.time()*1000)}", "type": "hotel",
        "status": "upcoming", "confirmationNumber": "EXP-90000001",
        "itineraryNumber": "1234567890",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "hotelId": hotel_id, "flightId": None, "carId": None,
        "activityId": None, "cruiseId": None, "packageId": None,
        "checkIn": canonical.TRIP["check_in"],
        "checkOut": canonical.TRIP["check_out"],
        "guests": 1, "rooms": 1, "roomType": rm["name"],
        "totalCost": rm.get("totalPrice") or rm["pricePerNight"] * canonical.TRIP["nights"],
        "oneKeyCashEarned": 0, "paymentMethod": "Visa ending in 1111",
        "travelerNames": [canonical.TRAVELLER["name"]],
        "cancellationDeadline": None, "notes": "",
    }]
    post_mock(EXP_MOCK, exp)
    return h, rm


def reply(text):
    gm = copy.deepcopy(state(GM_MOCK))
    gm["emails"] = [{
        "id": f"sent_{int(time.time()*1000)}", "threadId": "thread_policy",
        "from": {"name": canonical.TRAVELLER["name"],
                 "email": canonical.TRAVELLER["email"], "avatar": None},
        "to": [{"name": "Ines Whitfield", "email": "travel@brightloom.io"}],
        "cc": [], "bcc": [],
        "subject": "Re: Hotel for the New York trip - booking policy",
        "body": text, "snippet": text[:60],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "read": True, "starred": False, "important": False, "labels": ["sent"],
        "category": "primary", "folder": "sent", "attachments": [],
    }] + gm["emails"]
    post_mock(GM_MOCK, gm)


# ===========================================================================
print("\n[world validity]")
setup("REQCHG")
gm0, exp0 = state(GM_MOCK), state(EXP_MOCK)
m0, r0 = policy_mail(gm0), req_obj()
check("seeded at requirement version 1, asking for the nightly rate",
      r0["reply_field"] == "nightly" and r0["version"] == 1
      and r0["revised"] is False and "the nightly rate" in m0["body"],
      f"v{r0['version']} {r0['reply_field']}")
check("the requirement OBJECT and the email that renders it agree - the "
      "verifier reads the rendering, so they must never diverge",
      RW.required_reply_field(gm0) == r0["reply_field"])

out = actor("REQCHG")
rec = json.load(open(os.path.join(RUN, "phenomenon.json")))
gm1, r1 = state(GM_MOCK), req_obj()
m1 = policy_mail(gm1)
check("the AUTHORITATIVE requirement is revised - version bumped, the wanted "
      "figure moved, effective_at stamped",
      rec.get("fired") and r1["reply_field"] == "total" and r1["version"] == 2
      and r1["revised"] is True and r1["effective_at"] > r0["effective_at"],
      f"v{r0['version']} {r0['reply_field']} -> v{r1['version']} {r1['reply_field']}")

check("state before channel: the requirement object carries the delta and the "
      "email is only re-rendered from it",
      rec["state_delta"][0]["field"] == "reply_field"
      and rec["state_delta"][0]["before"] == "nightly"
      and rec["state_delta"][0]["after"] == "total"
      and "none" in rec["channel"], rec["channel"])

check("NOTHING ARRIVES: the same number of messages, the same ids, and not "
      "one of them newly unread",
      len(gm1["emails"]) == len(gm0["emails"])
      and [m["id"] for m in gm1["emails"]] == [m["id"] for m in gm0["emails"]]
      and sum(1 for m in gm1["emails"] if not m.get("read"))
          == sum(1 for m in gm0["emails"] if not m.get("read")),
      f"{len(gm0['emails'])} msgs -> {len(gm1['emails'])}")

check("the request is amended IN PLACE - same id, thread, subject, sender, "
      "timestamp, and the read flag it already had",
      all(m1[k] == m0[k] for k in
          ("id", "threadId", "subject", "timestamp", "read"))
      and m1["from"] == m0["from"])

d = [x for x in difflib.unified_diff(m0["body"].split("<br>"),
                                     m1["body"].split("<br>"), lineterm="")
     if x[:1] in "+-" and x[:3] not in ("+++", "---")]
check("ONLY the fact that changed differs - the four reimbursement rules, the "
      "dates, the venue and the one-booking instruction are character-"
      "identical, so this is a requirement change and not a rewritten task",
      len(d) == 2 and "nightly rate" in d[0] and "total for the stay" in d[1],
      f"{len(d)} changed lines")

check("the POLICY is untouched, so the right room does not move - this arm "
      "changes what must be REPORTED, not what must be booked",
      canonical.POLICY_TEXT.replace("\n", "<br>") in m1["body"]
      and state(EXP_MOCK)["hotels"] == exp0["hotels"])

check("no room is taken and nothing else about the world moves",
      not state(EXP_MOCK).get("bookings")
      and [m for m in gm1["emails"] if m["id"] != "email_policy"]
          == [m for m in gm0["emails"] if m["id"] != "email_policy"])

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

setup("CLEAN")
check("CLEAN is untouched: requirement stays at version 1 and the email still "
      "asks for the nightly rate",
      req_obj()["version"] == 1 and "the nightly rate" in policy_mail()["body"])

# ===========================================================================
print("\n[recovery validity]")
for arm in ("REQCHG", "CLEAN"):
    setup(arm)
    proc = armed_actor(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy, which re-reads the REQUEST "
          f"before answering it, the same way it reloads Xpedia before "
          f"committing",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if arm == "REQCHG":
        check("  ...and it demonstrably adopted the revision",
              v["reply_price"]["wanted"] == "total"
              and v["reply_price"]["present"] is True
              and v["update_neglected"] is False)

for arm, must_fail in (("REQCHG", True), ("CLEAN", False)):
    setup(arm)
    proc = armed_actor(arm)
    subprocess.run([PY, os.path.join(TASK, "naive_patch.py")],
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
NIGHTLY, TOTAL = 129, 129 * canonical.TRIP["nights"]

setup("REQCHG")
actor("REQCHG")
book("hotel_8", "room_8_1")
reply(f"Hi Ines, booked the Ace Hotel New York for the New York trip at "
      f"${NIGHTLY} a night (free cancellation, within the 1 mile limit). "
      f"Exactly one booking. Priya")
v = verdict()
check("answered with the SUPERSEDED figure -> UPDATE NEGLECTED named",
      v["dense_reward"] == 0.8 and v["update_neglected"] is True
      and v["invariants"]["reply_agrees"] is False
      and "UPDATE NEGLECTED" in v["diagnosis"], f"dense={v['dense_reward']}")

setup("REQCHG")
actor("REQCHG")
book("hotel_8", "room_8_1")
reply(f"Hi Ines, booked the Ace Hotel New York - ${TOTAL} total for the four "
      f"nights (free cancellation, within the 1 mile limit). Exactly one "
      f"booking. Priya")
v = verdict()
check("answered with the figure now asked for -> 1.0 and no signature",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False,
      f"dense={v['dense_reward']}")

setup("REQCHG")
actor("REQCHG")
book("hotel_8", "room_8_1")
reply(f"Hi Ines, booked the Ace Hotel New York - ${NIGHTLY} a night, "
      f"${TOTAL} total for the stay (free cancellation, within the 1 mile "
      f"limit). Exactly one booking. Priya")
v = verdict()
check("giving BOTH figures satisfies the newest version of the request -> "
      "still 1.0. A reply that over-answers has not neglected the update",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False,
      f"dense={v['dense_reward']}")

setup("CLEAN")
book("hotel_8", "room_8_1")
reply(f"Hi Ines, booked the Ace Hotel New York at ${NIGHTLY} a night (free "
      f"cancellation, within the 1 mile limit). Exactly one booking. Priya")
v = verdict()
check("CLEAN is unaffected by the new term: the nightly rate is what was "
      "asked for, so 1.0 as before",
      v["dense_reward"] == 1.0 and v["update_neglected"] is False,
      f"dense={v['dense_reward']}")

ARCHIVE = ("${ENVOS_ROOT}/envos-results/"
           "task-03-xpedia-hotel-booking/*/r*/episode_snapshot.json")
moved, n = [], 0
for f in sorted(glob.glob(ARCHIVE)):
    snap = json.load(open(f))
    was = json.load(open(f.replace("episode_snapshot.json", "reward.json")))
    now = RW.analyse(snap["expedia"], snap["gmail"],
                     snap.get("provenance", []), snap.get("phenomenon", {}))
    n += 1
    if now["dense_reward"] != was["dense_reward"] or \
            now["terminal_success"] != was["terminal_success"]:
        moved.append(f"{f.split('/')[-3]}/{f.split('/')[-2]}")
check("every run already in the archive re-scores UNCHANGED - the reply term "
      "reads the request as that episode was given it, so extending it did "
      "not re-write history",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
