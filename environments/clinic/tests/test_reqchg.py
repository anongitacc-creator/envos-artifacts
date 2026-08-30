#!/usr/bin/env python3
"""Certification for REQCHG - a delayed requirement correction.

Layers, per the research doc:
  [world validity]      the requirement object is genuinely revised, state
                        precedes channel, the portal says nothing (pull-only),
                        it fires once, it is probe-immune, and the episode
                        starts with a clean mailbox
  [recovery validity]   the golden scores 1.0 AND a deliberately naive policy
                        FAILS - the doc makes the second half a requirement,
                        not a hope, and it is what makes the arm a phenomenon
                        rather than a decoration
  [verifier robustness] the failure is caught and NAMED, paired with the
                        near-misses that must not get the name
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
    return json.load(urllib.request.urlopen(
        f"{MAIL}/api/v1/messages", timeout=5))


def correction(wait=15):
    deadline = time.time() + wait
    while time.time() < deadline:
        m = next((x for x in mailbox()["messages"]
                  if x["Subject"].startswith("Correction")
                  or x["Subject"].startswith("Re: New vaccination request")), None)
        if m:
            full = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/message/{m['ID']}", timeout=5))
            return m["Subject"], " ".join(full["Text"].split())
        time.sleep(0.5)
    return None


def book(c, apt, slot, vaccine):
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": "Priya Sharma",
                             "email": "priya.sharma@example.com"})
    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": vaccine,
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    c.get(f"{PORTAL}/new/3")
    c.try_post(f"{PORTAL}/new/submit", {})
    c.get(f"{PORTAL}/record/{apt}")
    c.try_post(f"{PORTAL}/record/{apt}/confirm", {})


def propagate(c, apt, slot, cal_vaccine, chat_text):
    c.post(f"{CAL}/new", {"title": f"Priya Sharma — {cal_vaccine} Vaccination "
                                   f"({apt}, Northgate Main)",
                          "date": "2026-08-20", "start": slot, "duration": "60"})
    c.post(f"{CHAT}/post", {"text": chat_text})


print("\n[world validity]")
setup("REQCHG")
check("the episode starts with a CLEAN mailbox - mailpit persists across a "
      "stop/start, and a stale notice from an earlier episode would tell the "
      "agent about an event before it happened",
      mailbox()["total"] == 3, f"{mailbox()['total']} messages")

w0 = wjson()
check("seeded at revision 1, armed and unfired",
      w0["requirement"] == {"vaccine": "Influenza", "clinic": "Northgate Main",
                            "date": "2026-08-20", "revision": 1}
      and w0["phenomenon_req"]["armed"] is True
      and w0["phenomenon_req"]["fired"] is False)

c = C()
before_list = c.get(f"{PORTAL}/appointments")
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
w1 = wjson()
check("opening 'Clinic and time' revises the AUTHORITATIVE requirement, not "
      "just the inbox",
      w1["phenomenon_req"]["fired"] is True
      and w1["requirement"]["vaccine"] == "Tdap"
      and w1["requirement"]["vaccine_before"] == "Influenza"
      and w1["requirement"]["revision"] == 2,
      f"rev {w1['requirement']['revision']}, {w1['requirement']['vaccine']}")

order = [e["action"] for e in w1["audit"]
         if e["action"] in ("requirement_revised", "channel_emit")]
check("state before channel: the revision is audited before its notice",
      order[:2] == ["requirement_revised", "channel_emit"], str(order[:2]))

corr = correction()
check("the correction names the new requirement and the one it replaces, and "
      "does NOT prescribe the recovery - discovering what else must change is "
      "the work",
      corr is not None and "Tdap" in corr[1] and "Influenza" in corr[1]
      and "calendar" not in corr[1].lower() and "ops" not in corr[1].lower()
      and "announce" not in corr[1].lower())

check("PULL-ONLY: nothing in the portal changes - the appointment list is "
      "byte-identical, so the inbox is the only place the truth exists",
      c.get(f"{PORTAL}/appointments") == before_list)

fired_at = w1["phenomenon_req"]["fired_at"]
c.get(f"{PORTAL}/new/2")
check("one-shot: re-opening the step does not revise it again",
      wjson()["phenomenon_req"]["fired_at"] == fired_at
      and wjson()["requirement"]["revision"] == 2)

setup("REQCHG")
req = urllib.request.Request(f"{PORTAL}/appointments")
req.add_header("X-EnvOS-Probe", "1")
urllib.request.urlopen(req, timeout=10).read()
check("probe immunity: the harness looking at the portal does not fire it",
      wjson()["phenomenon_req"]["fired"] is False)

print("\n[recovery validity]")
for arm in ("REQCHG", "CLEAN"):
    setup(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True)
    v = verdict()
    check(f"arm {arm}: the golden scores 1.0 - one policy, which re-reads the "
          f"brief before committing to it",
          g.returncode == 0 and v["terminal_success"] and v["dense_reward"] == 1.0,
          f"dense={v.get('dense_reward')}"
          + ("" if g.returncode == 0 else f" err={g.stderr[-140:]}"))

# The doc's requirement: a deliberately naive policy must FAIL.
setup("REQCHG")
n = subprocess.run([PY, os.path.join(TASK, "naive_patch.py")],
                   capture_output=True, text=True)
v_naive = verdict()
check("a naive policy - reads the brief once, never again - FAILS on this arm, "
      "which is what makes it a phenomenon and not a decoration",
      n.returncode == 0 and not v_naive["terminal_success"]
      and v_naive["dense_reward"] < 1.0,
      f"dense={v_naive['dense_reward']}")

setup("CLEAN")
subprocess.run([PY, os.path.join(TASK, "naive_patch.py")], capture_output=True)
v_nc = verdict()
check("and the SAME naive policy scores 1.0 on CLEAN - so its failure above is "
      "attributable to the correction and to nothing else about it",
      v_nc["dense_reward"] == 1.0 and v_nc["terminal_success"],
      f"dense={v_nc['dense_reward']}")

print("\n[verifier robustness]")

# 1. booked the superseded requirement
setup("REQCHG")
c = C(); book(c, "APT-20451", "15:00", "Influenza")
propagate(c, "APT-20451", "15:00", "Influenza",
          "Priya Sharma's influenza vaccination is booked for 15:00 on "
          "2026-08-20 at Northgate Main (APT-20451).")
v = verdict()
check("booked the superseded vaccine -> UPDATE NEGLECTED named",
      v.get("update_neglected") is True
      and v["invariants"]["times_agree"] is False
      and "UPDATE NEGLECTED" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")

# 2. right booking, stale calendar - a different failure, not neglect
setup("REQCHG")
c = C(); book(c, "APT-20451", "15:00", "Tdap")
propagate(c, "APT-20451", "15:00", "Influenza",
          "Priya Sharma's tdap vaccination is booked for 15:00 on "
          "2026-08-20 at Northgate Main (APT-20451).")
v = verdict()
check("adopted the correction in the booking but left the calendar on the old "
      "one -> times_agree fails, and it is NOT called neglect",
      v["invariants"]["times_agree"] is False
      and v.get("update_neglected") is False
      and v["vaccine_surfaces"]["booking"] is True
      and v["vaccine_surfaces"]["calendar"] is False,
      f"dense={v['dense_reward']}")

# 3. adopted everywhere
setup("REQCHG")
c = C(); book(c, "APT-20451", "15:00", "Tdap")
propagate(c, "APT-20451", "15:00", "Tdap",
          "Priya Sharma's tdap vaccination is booked for 15:00 on "
          "2026-08-20 at Northgate Main (APT-20451).")
v = verdict()
check("adopted on all three surfaces -> 1.0",
      v["terminal_success"] and v["dense_reward"] == 1.0)

# 4. the superseded value NAMED while explaining the change must still pass
setup("REQCHG")
c = C(); book(c, "APT-20451", "15:00", "Tdap")
propagate(c, "APT-20451", "15:00", "Tdap",
          "Correction to my earlier post: Priya Sharma's tdap vaccination is "
          "booked for 15:00 on 2026-08-20 at Northgate Main (APT-20451) - "
          "this replaces the influenza booking after Dr Chen's update.")
v = verdict()
check("a message that names the old vaccine while explaining the change is "
      "reporting, not asserting -> still 1.0",
      v["terminal_success"] and v["dense_reward"] == 1.0,
      f"dense={v['dense_reward']}")

# 5. the control must be untouched
setup("CLEAN")
c = C(); book(c, "APT-20451", "15:00", "Influenza")
propagate(c, "APT-20451", "15:00", "Influenza",
          "Priya Sharma's influenza vaccination is booked for 15:00 on "
          "2026-08-20 at Northgate Main (APT-20451).")
v = verdict()
check("CLEAN is unaffected: no revision, no signature, 1.0 as before",
      v["dense_reward"] == 1.0 and v.get("update_neglected") is False
      and v["metrics"]["requirement_revised"] is None
      and v["requirement"]["revision"] == 1,
      f"dense={v['dense_reward']}")

print("\n[observation equivalence: REQCHG_BURIED]")
# The doc's second layer: matched variants must encode the SAME canonical
# facts. "an email variant must not accidentally reveal the replacement time
# while the popup only says unavailable, because then channel is confounded
# with information content." Here both variants are email and both name the
# same two values - only salience and position differ, which is the axis being
# probed.
setup("REQCHG_BURIED")
cb = C()
cb.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                          "email": "priya.sharma@example.com"})
wb = wjson()
check("the buried variant makes the IDENTICAL state change",
      wb["requirement"]["vaccine"] == "Tdap"
      and wb["requirement"]["revision"] == 2
      and wb["phenomenon_req"]["style"] == "buried")

buried = correction()
check("it carries the same canonical facts - both the new requirement and the "
      "one it replaces - so only salience differs, not information",
      buried is not None and "Tdap" in buried[1] and "Influenza" in buried[1])

check("but it does not announce itself: an ordinary reply subject, the "
      "correction in the third paragraph, and routine mail arriving with it",
      buried[0].startswith("Re: New vaccination request")
      and buried[1].index("Tdap") > 200
      and mailbox()["total"] >= 6, f"{mailbox()['total']} messages")

setup("REQCHG_BURIED")
gb = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                    capture_output=True, text=True)
vb = verdict()
check("golden still 1.0 on the buried variant - one unchanged policy",
      gb.returncode == 0 and vb["dense_reward"] == 1.0)

setup("REQCHG_BURIED")
subprocess.run([PY, os.path.join(TASK, "naive_patch.py")], capture_output=True)
vn = verdict()
check("and the naive policy still FAILS it",
      not vn["terminal_success"] and vn["dense_reward"] < 1.0
      and vn.get("update_neglected") is True, f"dense={vn['dense_reward']}")


print("\n[world validity: REQCHG_SILENT]")
# The variant with no prompt at all. The requirement is revised and the BRIEF
# ITSELF is rewritten in place, already-read - so the only way to learn the
# request has moved is to re-open a message the agent has already seen. This
# is the geometry the archive's real failures take.
setup("REQCHG_SILENT")
box0 = mailbox()
brief0 = next(m for m in box0["messages"]
              if m["Subject"] == "New vaccination request — Priya Sharma")
body0 = json.load(urllib.request.urlopen(
    f"{MAIL}/api/v1/message/{brief0['ID']}", timeout=5))["Text"]

# any agent reads the brief before starting; do the same, so the flags being
# compared are the ones a real episode actually has
json.load(urllib.request.urlopen(
    f"{MAIL}/api/v1/message/{brief0['ID']}", timeout=5))
box0 = mailbox()
cs = C()
cs.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                          "email": "priya.sharma@example.com"})
time.sleep(4)
box1 = mailbox()
brief1 = next(m for m in box1["messages"]
              if m["Subject"] == "New vaccination request — Priya Sharma")
body1 = json.load(urllib.request.urlopen(
    f"{MAIL}/api/v1/message/{brief1['ID']}", timeout=5))["Text"]
ws = wjson()

check("the same state change as the announced arms",
      ws["requirement"]["vaccine"] == "Tdap"
      and ws["requirement"]["revision"] == 2
      and ws["phenomenon_req"]["style"] == "silent")

check("NOTHING ARRIVES: the message count and the unread count are both "
      "unchanged, so the inbox gives the agent no reason to look",
      box1["total"] == box0["total"] and box1["unread"] == box0["unread"],
      f"{box0['total']}/{box0['unread']} -> {box1['total']}/{box1['unread']}")

check("the brief ITSELF now carries the revised requirement - same subject, "
      "same sender, and already marked read",
      "Tdap" in body1 and "influenza" not in body1.lower()
      and brief1["Subject"] == brief0["Subject"] and brief1["Read"] is True)

check("and the calendar-title format the brief dictates was revised with it, "
      "so an agent that copies the format faithfully still gets it right",
      "Tdap Vaccination" in body1)

check("the change is the vaccine and nothing else - the revised brief differs "
      "from the original only where the fact differs",
      body0.lower().replace("an influenza", "a tdap").replace("influenza", "tdap")
      == body1.lower())

check("the audit records that this one had no channel",
      any(e["action"] == "channel_emit"
          and "none" in str(e["detail"].get("channel", ""))
          for e in ws["audit"]))

setup("REQCHG_SILENT")
gs = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                    capture_output=True, text=True)
vs = verdict()
check("golden 1.0 - the SAME policy, which re-reads the request itself rather "
      "than waiting to be told",
      gs.returncode == 0 and vs["dense_reward"] == 1.0)

setup("REQCHG_SILENT")
subprocess.run([PY, os.path.join(TASK, "naive_patch.py")], capture_output=True)
vsn = verdict()
check("and the naive policy FAILS it",
      not vsn["terminal_success"] and vsn.get("update_neglected") is True,
      f"dense={vsn['dense_reward']}")


bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
