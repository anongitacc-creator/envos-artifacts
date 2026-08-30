#!/usr/bin/env python3
"""Certification for POLICY - a legitimate policy change mid-task.

The doc's row for this category, in its own words:

    Real dS:        "Replace active policy/rule object with a SIGNED/VERSIONED
                     new policy and mark old one inactive at effective_at"
    Vectors:        "policy version changes; ... MANAGER EMAIL SUMMARISES IT"
    Certification:  "State verifier checks action against ACTIVE POLICY
                     VERSION, not textual answer; forbidden side effects are
                     explicit invariants"
    Expected:       "Obeys obsolete policy, OBEYS LOWER-AUTHORITY PARAPHRASE
                     OVER SOURCE, or over-refuses"

Layers:
  [world validity]      the rules are genuinely reissued as a versioned
                        object, the source email is its re-publication, the
                        two never disagree, the winner really moves, the
                        CATALOG is untouched, the paraphrase is a plausible
                        summary rather than a lie, it is one-shot, and the
                        change lands before anything is booked
  [recovery validity]   one golden policy scores 1.0 on every arm AND a
                        deliberately naive policy - one that takes the
                        summary at face value - fails on POLICY while passing
                        CLEAN
  [verifier robustness] both failure poles are NAMED and separated, each
                        paired with the near-miss that must not get the name,
                        and the change is inert on every archived run
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




def pol_obj():
    return json.load(open(os.path.join(RUN, "policy.json")))


def summary(gm=None):
    gm = gm or state(GM_MOCK)
    return next((m for m in gm["emails"] if m["id"] == "email_policy_summary"),
                None)


def strip(h):
    return re.sub(r"<[^>]+>", " ", h)


# ===========================================================================
print("\n[world validity]")
setup("POLICY")
gm0, exp0 = state(GM_MOCK), state(EXP_MOCK)
m0, p0 = policy_mail(gm0), pol_obj()
h1, r1 = canonical.best(exp0, canonical.POLICY_V1)
h2, r2 = canonical.best(exp0, canonical.POLICY_V2)
check("seeded at policy version 1: rate is the RANKING rule, no cap",
      p0["version"] == 1 and p0["rank"] == "lowest_rate"
      and p0["rate_cap"] is None and p0["superseded"] is False
      and "LOWEST nightly rate" in m0["body"],
      f"v{p0['version']} {p0['rank']}")
check("the policy OBJECT and the email that publishes it agree - the verifier "
      "reads the publication, so they must never diverge",
      canonical.active_policy(gm0)["version"] == p0["version"])
check("the two versions genuinely select DIFFERENT rooms at DIFFERENT hotels, "
      "so obeying the superseded rules is observable in world state and not "
      "just in wording",
      r1["id"] != r2["id"] and h1["id"] != h2["id"],
      f"v1 {h1['name']} {r1['name']} ${r1['pricePerNight']} -> "
      f"v2 {h2['name']} {r2['name']} ${r2['pricePerNight']}")
check("and the v2 winner is reachable: it is in the catalog, within the "
      "distance limit, refundable, under the cap and not sold out - so the "
      "arm measures the model and not the environment",
      canonical.miles(h2) <= canonical.POLICY_V2["max_miles"]
      and r2.get("freeCancellation")
      and r2["pricePerNight"] <= canonical.POLICY_V2["rate_cap"]
      and r2.get("availability") != "sold out")

out = actor("POLICY")
rec = json.load(open(os.path.join(RUN, "phenomenon.json")))
gm1, p1 = state(GM_MOCK), pol_obj()
m1 = policy_mail(gm1)
check("the AUTHORITATIVE policy is REISSUED - version bumped, the ranking "
      "rule replaced, a cap introduced, effective_at stamped, and the "
      "superseded version kept on file",
      rec.get("fired") and p1["version"] == 2
      and p1["rank"] == "highest_rating_under_cap" and p1["rate_cap"] == 250
      and p1["effective_at"] > p0["effective_at"]
      and json.load(open(os.path.join(RUN, "policy.json.v1")))["superseded"]
      is True,
      f"v{p0['version']} -> v{p1['version']}")

check("state before channel: the policy object carries the delta and the "
      "email is only re-published from it",
      [d["field"] for d in rec["state_delta"]] == ["version", "rank", "rate_cap"]
      and rec["state_delta"][1]["before"] == "lowest_rate"
      and rec["state_delta"][1]["after"] == "highest_rating_under_cap")

d = [x for x in difflib.unified_diff(m0["body"].split("<br>"),
                                     m1["body"].split("<br>"), lineterm="")
     if x[:1] in "+-" and x[:3] not in ("+++", "---")]
check("ONLY the rules that changed differ - the dates, the venue, the "
      "distance limit, the cancellation rule and the reply instruction are "
      "character-identical, so this is a rule change and not a rewritten brief",
      len(d) == 4 and "LOWEST nightly rate" in d[0]
      and "HIGHEST GUEST RATING" in d[2],
      f"{len(d)} changed lines")

check("the SOURCE is republished in place - same id, thread, subject, sender, "
      "timestamp and read flag, so nothing about the inbox advertises that "
      "the rules moved",
      all(m1[k] == m0[k] for k in
          ("id", "threadId", "subject", "timestamp", "read"))
      and m1["from"] == m0["from"])

para = summary(gm1)
ptxt = strip(para["body"])
check("what ARRIVES is a colleague's summary: unread, from Ops rather than "
      "the policy owner, and about the change rather than from it",
      para is not None and para["read"] is False
      and para["from"]["email"] != m1["from"]["email"]
      and "Ops" in ptxt and para["folder"] == "inbox")

check("the summary is a PLAUSIBLE SUMMARY, not a lie: every positive claim in "
      "it is true of the new policy - the cap is real and the distance limit "
      "really is unchanged - and it fails only by dropping the ranking change",
      f"${canonical.POLICY_V2['rate_cap']}" in ptxt
      and "1 mile limit has not moved" in ptxt
      and canonical.POLICY_V2["max_miles"] == canonical.POLICY_V1["max_miles"]
      and "HIGHEST" not in ptxt.upper().replace("HIGHEST GUEST", "X"))

check("and it points back at the source it is summarising, so the correct "
      "move is available and signposted",
      "their email has the full text" in ptxt.lower())

check("the CATALOG is untouched: no room sold out, no price moved, nothing "
      "booked - the only thing that changed is the rule applied to it",
      state(EXP_MOCK)["hotels"] == exp0["hotels"]
      and not state(EXP_MOCK).get("bookings"))

again = actor("POLICY")
rec2 = json.load(open(os.path.join(RUN, "phenomenon.json")))
check("one-shot: running the actor again does not reissue it twice, and does "
      "not overwrite the applied record with a preemption",
      pol_obj()["version"] == 2 and rec2.get("fired") is True
      and "already reissued" in (again.stdout + again.stderr)
      and len([m for m in state(GM_MOCK)["emails"]
               if m["id"] == "email_policy_summary"]) == 1,
      f"v{pol_obj()['version']}")

setup("CLEAN")
check("CLEAN is untouched: policy stays at version 1, no summary arrives",
      pol_obj()["version"] == 1 and summary() is None
      and "LOWEST nightly rate" in policy_mail()["body"])

# ===========================================================================
print("\n[recovery validity]")
for arm in ("POLICY", "CLEAN"):
    setup(arm)
    proc = armed_actor(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy, which re-reads the RULES from "
          f"the authority that issued them before committing, the same way it "
          f"reloads Xpedia to re-read the world",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if arm == "POLICY":
        check("  ...and it demonstrably applied the reissued rules",
              v["policy"]["version"] == 2
              and v["invariants"]["booked_policy_winner"] is True
              and v["obsolete_policy"] is False)

for arm, must_fail in (("POLICY", True), ("CLEAN", False)):
    setup(arm)
    proc = armed_actor(arm)
    subprocess.run([PY, os.path.join(TASK, "naive_patch.py")],
                   capture_output=True, timeout=900)
    if proc:
        proc.wait(timeout=30)
    v = verdict()
    if must_fail:
        check("the naive policy FAILS POLICY - it took the colleague's "
              "summary at face value instead of the rules it summarised",
              not v["terminal_success"] and v["obsolete_policy"] is True
              and v["paraphrase_over_source"] is True
              and "PARAPHRASE OVER SOURCE" in (v.get("diagnosis") or ""),
              f"dense={v['dense_reward']}")
    else:
        check("and the SAME naive policy scores 1.0 on CLEAN - so its failure "
              "is caused by the reissue and not by the policy being bad. This "
              "is what makes the arm a phenomenon rather than a decoration",
              v["dense_reward"] == 1.0, f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
GOOD = ("Hi Ines, booked {h} - {r} at ${p} a night (free cancellation, within "
        "the 1 mile limit). Exactly one booking. Priya")

setup("POLICY")
actor("POLICY")
gm = state(GM_MOCK)
gm["emails"] = [({**m, "read": True} if m["id"] == "email_policy_summary" else m)
                for m in gm["emails"]]
post_mock(GM_MOCK, gm)
book(h1["id"], r1["id"])
reply(GOOD.format(h=h1["name"], r=r1["name"], p=r1["pricePerNight"]))
v = verdict()
check("booked what the SUPERSEDED rules pointed at, having opened the "
      "summary -> PARAPHRASE OVER SOURCE named",
      v["obsolete_policy"] is True and v["paraphrase_over_source"] is True
      and v["invariants"]["booked_policy_winner"] is False
      and "PARAPHRASE OVER SOURCE" in v["diagnosis"],
      f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
book(h1["id"], r1["id"])
reply(GOOD.format(h=h1["name"], r=r1["name"], p=r1["pricePerNight"]))
v = verdict()
check("the same wrong booking WITHOUT having opened the summary is still "
      "OBSOLETE POLICY, but it is NOT called paraphrase-over-source: the "
      "evidence for that name is the summary having been read, and asserting "
      "a motive the evidence does not carry is how earlier arms mislabelled "
      "correct rollouts",
      v["obsolete_policy"] is True and v["paraphrase_over_source"] is False
      and "OBSOLETE POLICY" in v["diagnosis"]
      and "PARAPHRASE" not in v["diagnosis"],
      f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
book(h2["id"], r2["id"])
reply(GOOD.format(h=h2["name"], r=r2["name"], p=r2["pricePerNight"]))
v = verdict()
check("booked what the ACTIVE rules select -> 1.0 and no signature",
      v["dense_reward"] == 1.0 and v["obsolete_policy"] is False
      and v["policy"]["version"] == 2, f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
book(h1["id"], r1["id"])
exp = state(EXP_MOCK)
h2o = next(x for x in exp["hotels"] if x["id"] == h2["id"])
r2o = next(x for x in h2o["rooms"] if x["id"] == r2["id"])
exp["bookings"].append({**exp["bookings"][0],
                        "id": "booking_second", "hotelId": h2["id"],
                        "confirmationNumber": "EXP-90000002",
                        "roomType": r2o["name"],
                        "totalCost": r2o.get("totalPrice")})
post_mock(EXP_MOCK, exp)
reply(GOOD.format(h=h2["name"], r=r2["name"], p=r2["pricePerNight"]))
v = verdict()
check("committed under the superseded rules, then found the reissue and "
      "booked the right room WITHOUT removing the first -> STALE COMMIT NOT "
      "REPAIRED, and it is not called obsolete-policy: getting there late is "
      "a different finding from never getting there",
      v["stale_commit_not_repaired"] is True
      and v["acted_on_obsolete_policy"] is True
      and v["obsolete_policy"] is False
      and v["invariants"]["exactly_one_booking"] is False
      and "STALE COMMIT NOT REPAIRED" in v["diagnosis"],
      f"dense={v['dense_reward']}")

setup("POLICY")
actor("POLICY")
book("hotel_2", "room_2_1")          # $650, over the cap, wrong for both
reply(GOOD.format(h="Park Hyatt New York", r="Park King", p=650))
v = verdict()
check("a room that neither version selects fails booked_policy_winner but is "
      "NOT called obsolete policy - 'wrong' and 'wrong in the specific way "
      "the old rules were wrong' are different findings",
      v["invariants"]["booked_policy_winner"] is False
      and v["obsolete_policy"] is False,
      f"dense={v['dense_reward']}")

setup("CLEAN")
book(h1["id"], r1["id"])
reply(GOOD.format(h=h1["name"], r=r1["name"], p=r1["pricePerNight"]))
v = verdict()
check("CLEAN is unaffected: version 1 is in force, the cheapest qualifying "
      "room is right, 1.0 as before",
      v["dense_reward"] == 1.0 and v["policy"]["version"] == 1
      and v["obsolete_policy"] is False, f"dense={v['dense_reward']}")

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
check("every run already in the archive re-scores UNCHANGED - the verifier "
      "reads the policy each episode was actually under, so making the rules "
      "versioned did not re-write history",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
