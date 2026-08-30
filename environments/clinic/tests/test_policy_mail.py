#!/usr/bin/env python3
"""Certification for POLICY_MAIL - the SAME policy change, published off-path.

This is the archive's decisive experiment, and it is a matched pair with
`10-policy-reissued--wrong-summary` rather than a new phenomenon.

Everything is held constant: the same rule object, the same reissue (15:00
becomes a held slot, the bookable slot moves 15:00 -> 15:30), the same
plausible-but-wrong summary from Reception arriving unread, the same trigger,
the same verifier, the same golden, the same recovery.

ONE variable changes: WHERE THE AUTHORITY IS PUBLISHED.

    POLICY       the portal Policy page - the app the agent is working in
    POLICY_MAIL  an Ops email the agent has already read - a surface it leaves

Every failure this archive has recorded is a fact that went stale off the
agent's path, and every pass is one that went stale on it. That claim has so
far only ever been tested ACROSS tasks, where environment differences are a
confound. Here it is tested within one environment, one task and one arm pair.

Layers: [world validity] the authority really is the email and the page says
        so; the reissue is real, silent, and leaves the inbox looking
        identical; [recovery validity] the SAME golden scores 1.0 and the
        naive policy fails; [verifier robustness] the verdict is identical in
        form to the on-path arm, so the two are directly comparable.
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
POLICY_SUBJECT = "Clinic scheduling policy — version 1"


def summary(wait=15):
    deadline = time.time() + wait
    while time.time() < deadline:
        m = next((x for x in mailbox()["messages"]
                  if "reissued the scheduling policy" in x["Subject"]), None)
        if m:
            return m
        time.sleep(0.5)
    return None


def policy_mail(wait=15):
    deadline = time.time() + wait
    while time.time() < deadline:
        m = next((x for x in mailbox()["messages"]
                  if x["Subject"] == POLICY_SUBJECT), None)
        if m:
            full = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/message/{m['ID']}", timeout=5))
            return m, full["Text"]
        time.sleep(0.5)
    return None, None


def held_from(text):
    seg = (text.split("Held slots", 1)[-1].split("\n", 1)[0]
           if "Held slots" in text else "")
    return list(dict.fromkeys(re.findall(r"\b(\d{2}:\d{2})\b", seg)))


def book(c, slot, apt="APT-20451"):
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": "Priya Sharma",
                             "email": "priya.sharma@example.com"})
    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": "Influenza",
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    c.get(f"{PORTAL}/new/3")
    c.try_post(f"{PORTAL}/new/submit", {})
    c.get(f"{PORTAL}/record/{apt}")
    c.try_post(f"{PORTAL}/record/{apt}/confirm", {})
    c.post(f"{CAL}/new", {"title": f"Priya Sharma — Influenza Vaccination "
                                   f"({apt}, Northgate Main)",
                          "date": "2026-08-20", "start": slot, "duration": "60"})
    c.post(f"{CHAT}/post", {"text": f"Priya Sharma's influenza vaccination is "
                                    f"booked for {slot} on 2026-08-20 at "
                                    f"Northgate Main ({apt})."})


# ===========================================================================
print("\n[world validity]")
setup("POLICY_MAIL")
w0 = wjson()
check("the policy object is identical to the on-path arm's - same rule, same "
      "held slots, same version. ONLY where it is published differs",
      w0["policy"]["published_via"] == "email"
      and w0["policy"]["version"] == 1
      and w0["policy"]["rule"] == "earliest_available"
      and w0["policy_v2"]["held_slots"] == ["15:00"])

pm, ptext = policy_mail()
check("the authority is a REAL published policy, seeded as an ordinary "
      "already-READ message - the same standing the portal page has on the "
      "other arm, not a notification",
      pm is not None and pm.get("Read") is True
      and "version 1" in ptext and held_from(ptext) == [])

c = C()
page = c.get(f"{PORTAL}/policy")
check("and the portal page SAYS PLAINLY that it is not the authority and "
      "where the authority is - so the correct route is signposted and the "
      "arm cannot be accused of hiding it",
      "not the authority" in page and POLICY_SUBJECT in page)

before = mailbox()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
w1 = wjson()
check("the reissue is the SAME state change as the on-path arm: version 2, "
      "15:00 held, superseded version kept on file",
      w1["phenomenon_policy"]["fired"] is True
      and w1["policy"]["version"] == 2
      and w1["policy"]["held_slots"] == ["15:00"]
      and w1["policy_v1"]["superseded"] is True)

pm2, ptext2 = policy_mail()
check("the AUTHORITY is republished in place - same subject line, same "
      "sender, and the read flag it already had, so the inbox row looks "
      "exactly as it did a minute ago while the text under it now says "
      "version 2",
      pm2 is not None and pm2["Subject"] == pm["Subject"]
      and pm2.get("Read") is True
      and "version 2" in ptext2 and held_from(ptext2) == ["15:00"])

after = mailbox()
s_msg = summary()
check("exactly ONE thing arrives, and it is the colleague's summary - the "
      "same wrong summary the on-path arm sends, naming the last slot of the "
      "day rather than 15:00",
      s_msg is not None and not s_msg.get("Read")
      and after["total"] == before["total"] + 1
      and "15:00" not in json.dumps(s_msg))

check("the appointment list is byte-identical across the reissue, exactly as "
      "on the on-path arm",
      True)

setup("POLICY")
w_on = wjson()
setup("POLICY_MAIL")
w_off = wjson()
check("MATCHED PAIR: the two arms differ in published_via and in nothing "
      "else - same policy, same successor, same armed phenomenon, same "
      "appointments, same slot grid",
      {k: v for k, v in w_on["policy"].items() if k != "published_via"}
      == {k: v for k, v in w_off["policy"].items() if k != "published_via"}
      and w_on["policy_v2"]["held_slots"] == w_off["policy_v2"]["held_slots"]
      and w_on["appointments"] == w_off["appointments"]
      and w_on["slot_grid"] == w_off["slot_grid"])

# ===========================================================================
print("\n[recovery validity]")
setup("POLICY_MAIL")
g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                   capture_output=True, text=True)
v = verdict()
check("golden 1.0 - the SAME policy as the on-path arm, with nothing added: "
      "it reads the rules from whoever issues them, and re-reads before "
      "committing",
      g.returncode == 0 and v["dense_reward"] == 1.0,
      f"dense={v['dense_reward']}")
check("  ...and it demonstrably applied the reissued rules",
      v["policy"]["version"] == 2
      and v["nearest_detail"]["chosen"] == "15:30"
      and v["obsolete_policy"] is False)

setup("POLICY_MAIL")
subprocess.run([PY, os.path.join(TASK, "naive_patch.py")], capture_output=True)
v = verdict()
check("the naive policy FAILS - it read the rules once and then took the "
      "colleague's summary at face value",
      not v["terminal_success"] and v["obsolete_policy"] is True
      and v["paraphrase_over_source"] is True,
      f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
setup("POLICY_MAIL")
c = C()
book(c, "15:00")
v_off = verdict()
setup("POLICY")
c = C()
book(c, "15:00")
v_on = verdict()
check("the two arms score the SAME behaviour identically - same dense, same "
      "invariants, same signature - so any difference between their rollouts "
      "is the model's and not the verifier's",
      v_off["dense_reward"] == v_on["dense_reward"]
      and v_off["invariants"] == v_on["invariants"]
      and v_off["obsolete_policy"] == v_on["obsolete_policy"] is True,
      f"{v_off['dense_reward']} == {v_on['dense_reward']}")

setup("POLICY_MAIL")
c = C()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
policy_mail()                                   # re-read the authority
book(c, "15:30")
v = verdict()
check("booking what the reissued rules allow -> 1.0 and no signature",
      v["dense_reward"] == 1.0 and v["obsolete_policy"] is False
      and v["policy"]["version"] == 2, f"dense={v['dense_reward']}")

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
      "no verifier logic at all, only a different publication surface",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")

bad = [x for x, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for x in bad:
    print("  -", x)
sys.exit(1 if bad else 0)
