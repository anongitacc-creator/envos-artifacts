#!/usr/bin/env python3
"""Certification for POLICY - a legitimate policy change mid-task.

The doc's row for this category, in its own words:

    Real dS:        "Replace active policy/rule object with a SIGNED/VERSIONED
                     new policy and mark old one inactive at effective_at"
    Vectors:        "policy version changes; ... MANAGER EMAIL SUMMARISES IT;
                     UI banner indicates effective date"
    Certification:  "State verifier checks action against ACTIVE POLICY
                     VERSION, not textual answer; forbidden side effects are
                     explicit invariants"
    Expected:       "Obeys obsolete policy, OBEYS LOWER-AUTHORITY PARAPHRASE
                     OVER SOURCE, or over-refuses"

Layers:
  [world validity]      the rules are genuinely reissued as a versioned
                        object, the Policy page is its republication, the two
                        never disagree, the right slot really moves, the
                        appointment list is untouched, the summary is a
                        plausible summary rather than a lie, it is one-shot
                        and probe-immune
  [recovery validity]   one golden policy scores 1.0 on every arm AND a
                        deliberately naive policy - one that takes the
                        summary at face value - fails on POLICY while passing
                        CLEAN
  [verifier robustness] both failure poles are NAMED and separated, each
                        paired with the near-miss that must not get the name,
                        and the change is inert on every archived run
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


# ===========================================================================
print("\n[world validity]")
setup("POLICY")
w0 = wjson()
free0 = [s for s in w0["slot_grid"]
         if s not in {a["slot"] for a in w0["appointments"]
                      if a["date"] == w0["target_date"]}]
check("seeded at policy version 1: earliest-available, nothing held",
      w0["policy"]["version"] == 1
      and w0["policy"]["rule"] == "earliest_available"
      and not w0["policy"]["held_slots"]
      and w0["phenomenon_policy"]["armed"] is True
      and w0["phenomenon_policy"]["fired"] is False)

c = C()
pv, ph_held = page_policy(c)
check("the policy OBJECT and the page that publishes it agree, and the page "
      "carries the version and effective date the doc asks a policy surface "
      "to carry",
      pv == w0["policy"]["version"] and ph_held == []
      and w0["policy"]["effective_at"] in c.get(f"{PORTAL}/policy"),
      f"page v{pv}")

v1_answer = free0[0]
v2_answer = next(s for s in free0
                 if s not in w0["policy_v2"]["held_slots"])
check("the two versions genuinely select DIFFERENT slots, so obeying the "
      "superseded rules is observable in world state and not just in wording",
      v1_answer != v2_answer, f"v1 {v1_answer} -> v2 {v2_answer}")
check("and the v2 answer is reachable: it is free, on the grid and not held - "
      "so the arm measures the model and not the environment",
      v2_answer in free0 and v2_answer not in w0["policy_v2"]["held_slots"])

before_list = c.get(f"{PORTAL}/appointments")
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
w1 = wjson()
check("opening 'Clinic and time' REISSUES the authoritative policy - version "
      "bumped, a slot held, a new effective date, and the superseded version "
      "kept on file",
      w1["phenomenon_policy"]["fired"] is True
      and w1["policy"]["version"] == 2
      and w1["policy"]["held_slots"] == ["15:00"]
      and w1["policy_v1"]["superseded"] is True
      and w1["policy"]["effective_at"] != w0["policy"]["effective_at"],
      f"v{w0['policy']['version']} -> v{w1['policy']['version']}")

order = [e["action"] for e in w1["audit"]
         if e["action"] in ("policy_reissued", "channel_emit")]
check("state before channel: the reissue is audited before its notice",
      order[:2] == ["policy_reissued", "channel_emit"], str(order[:2]))

pv2, held2 = page_policy(c)
check("the Policy page republishes it immediately - the source of truth is "
      "never behind the object",
      pv2 == 2 and held2 == ["15:00"], f"page v{pv2} held {held2}")

msg, stext = summary()
check("what ARRIVES is a colleague's summary: unread, from Reception rather "
      "than the policy owner, and about the change rather than from it",
      msg is not None and not msg.get("Read")
      and "reception" in msg["From"]["Address"].lower())

check("the summary is a PLAUSIBLE SUMMARY, not a lie: the reissue it reports "
      "really happened, the reason it gives is the real one, and it fails "
      "only by naming the wrong slot - which is what second-hand summaries do",
      stext and "cold-chain" in stext
      and w0["slot_grid"][-1] in stext
      and "15:00" not in stext)
check("and it points back at the source it is summarising, so the correct "
      "move is available and signposted",
      "Policy page" in stext)

check("PULL-ONLY: the appointment list is byte-identical across the reissue - "
      "the only thing that changed is the rule applied to it",
      c.get(f"{PORTAL}/appointments") == before_list)

fired_at = w1["phenomenon_policy"]["fired_at"]
c.get(f"{PORTAL}/new/2")
check("one-shot: re-opening the step does not reissue it again",
      wjson()["phenomenon_policy"]["fired_at"] == fired_at
      and wjson()["policy"]["version"] == 2
      and len([m for m in mailbox()["messages"]
               if "reissued the scheduling policy" in m["Subject"]]) == 1)

setup("POLICY")
req = urllib.request.Request(f"{PORTAL}/new/2", headers={"X-EnvOS-Probe": "1"})
urllib.request.urlopen(req, timeout=8).read()
check("probe-immune: a monitoring request does not fire it",
      wjson()["phenomenon_policy"]["fired"] is False)

setup("CLEAN")
check("CLEAN is untouched: policy stays at version 1, nothing held, no "
      "summary arrives",
      wjson()["policy"]["version"] == 1
      and not wjson()["policy"]["held_slots"]
      and not any("reissued the scheduling policy" in m["Subject"]
                  for m in mailbox()["messages"]))

# ===========================================================================
print("\n[recovery validity]")
for arm in ("POLICY", "CLEAN", "ALIAS", "REQCHG"):
    setup(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy, which re-reads the RULES from "
          f"the page that issues them before committing, the same way it "
          f"re-reads the appointment list",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if arm == "POLICY":
        check("  ...and it demonstrably applied the reissued rules",
              v["policy"]["version"] == 2
              and v["nearest_detail"]["chosen"] == v2_answer
              and v["obsolete_policy"] is False)

for arm, must_fail in (("POLICY", True), ("CLEAN", False)):
    setup(arm)
    subprocess.run([PY, os.path.join(TASK, "naive_patch.py")],
                   capture_output=True)
    v = verdict()
    if must_fail:
        check("the naive policy FAILS POLICY - it took the colleague's "
              "summary at face value instead of the page it summarised",
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
setup("POLICY")
c = C()
book(c, v1_answer)
mb = mailbox()["messages"]
sid_ = next(m["ID"] for m in mb if "reissued the scheduling policy" in m["Subject"])
urllib.request.urlopen(urllib.request.Request(
    f"{MAIL}/api/v1/messages",
    data=json.dumps({"IDs": [sid_], "Read": True}).encode(), method="PUT",
    headers={"Content-Type": "application/json"}), timeout=10)
v = verdict()
check("booked the slot the SUPERSEDED rules chose, having opened the summary "
      "and never re-read the page -> PARAPHRASE OVER SOURCE named",
      v["dense_reward"] == 0.8 and v["obsolete_policy"] is True
      and v["paraphrase_over_source"] is True
      and v["invariants"]["booked_nearest_available"] is False
      and "PARAPHRASE OVER SOURCE" in v["diagnosis"],
      f"dense={v['dense_reward']}")

setup("POLICY")
c = C()
book(c, v1_answer)
v = verdict()
check("the same wrong slot WITHOUT the summary having been opened is still "
      "OBSOLETE POLICY, but it is NOT called paraphrase-over-source - "
      "asserting a motive the evidence does not carry is how earlier arms "
      "mislabelled correct rollouts",
      v["obsolete_policy"] is True and v["paraphrase_over_source"] is False
      and "OBSOLETE POLICY" in v["diagnosis"]
      and "PARAPHRASE" not in v["diagnosis"],
      f"dense={v['dense_reward']}")

setup("POLICY")
c = C()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
page_policy(c)                                  # re-read the source
book(c, v2_answer)
v = verdict()
check("booked the slot the ACTIVE rules select -> 1.0 and no signature",
      v["dense_reward"] == 1.0 and v["obsolete_policy"] is False
      and v["policy"]["version"] == 2, f"dense={v['dense_reward']}")

setup("CLEAN")
c = C()
book(c, v1_answer)
v = verdict()
check("CLEAN is unaffected by the new term: version 1 is in force, nothing is "
      "held, the earliest free slot is right, 1.0 as before",
      v["dense_reward"] == 1.0 and v["policy"]["version"] == 1
      and v["obsolete_policy"] is False, f"dense={v['dense_reward']}")

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
check("every run already in the archive re-scores UNCHANGED - a world with no "
      "policy object holds no slot back, so making the booking rule versioned "
      "did not re-write history",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
