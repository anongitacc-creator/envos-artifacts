#!/usr/bin/env python3
"""Certification for ALIAS / ALIAS_SILENT - an entity merge and alias drift.

The doc's row for this category, in its own words:

    Real dS implementation:  "Merge two entity IDs or change canonical ID/name
                              while PRESERVING ALIAS/PROVENANCE EDGES and
                              updating selected references"
    Certification & reward:  "Entity graph proves canonical identity; no task
                              may be executed on wrong person; downstream
                              records must all resolve to canonical entity ID"
    Expected failure:        "Updates wrong Priya; creates duplicate customer;
                              mismatches calendar/chat/CRM"

Layers:
  [world validity]      the merge is real in the registry, the edges survive,
                        identity is unambiguous BEFORE it and after it, state
                        precedes channel, it fires once, it is probe-immune,
                        and the episode starts clean
  [observation equivalence]  the silent variant makes the identical state
                        change and differs only in whether anything announces
                        it - so channel is not confounded with content
  [recovery validity]   one golden policy scores 1.0 on every arm AND the
                        deliberately naive policy fails on the arm while
                        passing CLEAN
  [verifier robustness] the failure is caught and NAMED, paired with the
                        near-misses that must not get the name
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


# ===========================================================================
print("\n[world validity]")
setup("ALIAS")
check("the episode starts with a CLEAN mailbox",
      mailbox()["total"] == 3, f"{mailbox()['total']} messages")

w0 = wjson()
act0 = [p for p in w0["persons"] if p["status"] == "active"
        and any("priya" in n.lower()
                for n in [p["canonical_name"]] + p["aliases"])]
check("identity is UNAMBIGUOUS at t=0: exactly one active registry row is this "
      "patient, so the ambiguity is created by the merge and is not a puzzle "
      "the agent starts inside",
      len(act0) == 1 and act0[0]["person_id"] == "p_2119",
      ", ".join(p["person_id"] for p in act0))
check("the surviving master exists but is ARCHIVED, so it is off the default "
      "roster and cannot be picked by mistake at the start",
      P(w0, "p_1842")["status"] == "archived"
      and P(w0, "p_1842")["merged_into"] is None)
check("armed and unfired",
      w0["phenomenon_alias"]["armed"] is True
      and w0["phenomenon_alias"]["fired"] is False)

roster0 = C().get(f"{PORTAL}/patients")
check("and the registry the agent actually sees lists one Priya",
      roster0.count("Priya") == 2,   # the name cell and the alias cell of p_2119
      f"{roster0.count('Priya')} mentions")

c = C()
before_list = c.get(f"{PORTAL}/appointments")
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
w1 = wjson()
src, dst = P(w1, "p_2119"), P(w1, "p_1842")
check("opening 'Clinic and time' MERGES the records in the authoritative "
      "registry - the duplicate is retired and the master becomes canonical",
      w1["phenomenon_alias"]["fired"] is True
      and src["status"] == "merged" and src["merged_into"] == "p_1842"
      and dst["status"] == "active",
      f"{src['person_id']} -> {src['merged_into']}, {dst['person_id']} "
      f"{dst['status']}")

check("this is a MERGE, not a rename: the person_ids are untouched and the "
      "superseded id still RESOLVES to the surviving record, exactly as the "
      "doc requires ('preserving alias/provenance edges')",
      RW._resolve(w1, RW._person(w1, "p_2119"))["person_id"] == "p_1842"
      and {p["person_id"] for p in w1["persons"]}
          == {p["person_id"] for p in w0["persons"]})

check("every name the patient was ever known by is retained as an alias, so "
      "nothing the agent already wrote down stops resolving",
      set(dst["aliases"]) >= {"Priya Sharma", "Priya S.", "P. Sharma"},
      ", ".join(dst["aliases"]))

check("what MOVED is which record is canonical, and with it the canonical "
      "name and address",
      dst["canonical_name"] == "Priya Sharma-Iyer"
      and dst["email"] == "priya.sharma-iyer@example.com"
      and dst["version"] == P(w0, "p_1842")["version"] + 1,
      f"{dst['canonical_name']} v{dst['version']}")

untouched = [p["person_id"] for p in w1["persons"]
             if p["person_id"] not in ("p_2119", "p_1842")]
check("ONLY the two intended rows changed - the other seven registry entries "
      "and every existing appointment are byte-identical",
      all(P(w1, i) == P(w0, i) for i in untouched)
      and w1["appointments"] == w0["appointments"],
      f"{len(untouched)} other persons unchanged")

order = [e["action"] for e in w1["audit"]
         if e["action"] in ("entity_merged", "channel_emit")]
check("state before channel: the merge is audited before its notice",
      order[:2] == ["entity_merged", "channel_emit"], str(order[:2]))

n = notice()
check("the notice is MATCHED: it names the entity that changed and its new "
      "canonical value, and says nothing about the booking, the calendar or "
      "what to repair - discovering that is the work",
      n is not None and "p_2119" in n[1] and "p_1842" in n[1]
      and "Priya Sharma-Iyer" in n[1]
      and not any(k in n[1].lower()
                  for k in ("appointment", "calendar", "ops", "booking",
                            "announce", "apt-")))

check("PULL-ONLY: the appointment list is byte-identical across the merge, so "
      "the registry and the inbox are the only places the truth exists",
      c.get(f"{PORTAL}/appointments") == before_list)

fired_at = w1["phenomenon_alias"]["fired_at"]
c.get(f"{PORTAL}/new/2")
check("one-shot: re-opening the step does not merge again",
      wjson()["phenomenon_alias"]["fired_at"] == fired_at
      and P(wjson(), "p_1842")["version"] == dst["version"])

setup("ALIAS")
req = urllib.request.Request(f"{PORTAL}/new/2", headers={"X-EnvOS-Probe": "1"})
urllib.request.urlopen(req, timeout=8).read()
check("probe-immune: a monitoring request does not fire it",
      wjson()["phenomenon_alias"]["fired"] is False)

setup("CLEAN")
c = C()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
wc = wjson()
check("CLEAN is untouched: no merge, the registry is exactly as seeded",
      wc["phenomenon_alias"]["fired"] is False
      and P(wc, "p_2119")["status"] == "active"
      and P(wc, "p_1842")["status"] == "archived")

# ===========================================================================
print("\n[observation equivalence: ALIAS_SILENT]")
setup("ALIAS_SILENT")
before = mailbox()
wa = wjson()
c = C()
c.post(f"{PORTAL}/new", {"apt": "APT-20451", "patient": "Priya Sharma",
                         "email": "priya.sharma@example.com"})
wb = wjson()
check("the silent variant makes the IDENTICAL state change",
      P(wb, "p_2119")["status"] == "merged"
      and P(wb, "p_2119")["merged_into"] == "p_1842"
      and P(wb, "p_1842")["canonical_name"] == "Priya Sharma-Iyer"
      and P(wb, "p_1842")["status"] == "active"
      and set(P(wb, "p_1842")["aliases"]) == set(dst["aliases"]))
time.sleep(2)
after = mailbox()
check("NOTHING ARRIVES: the message count and the unread count are unchanged, "
      "so the inbox gives the agent no reason to look",
      after["total"] == before["total"]
      and sum(1 for m in after["messages"] if not m["Read"])
          == sum(1 for m in before["messages"] if not m["Read"]),
      f"{before['total']}/{sum(1 for m in before['messages'] if not m['Read'])}"
      f" -> {after['total']}/{sum(1 for m in after['messages'] if not m['Read'])}")
check("the registry page is the only witness, and it tells the whole truth - "
      "the merged row says what it was merged into and what the canonical "
      "record now is",
      all(k in c.get(f"{PORTAL}/patients/p_2119")
          for k in ("merged into", "p_1842", "Priya Sharma-Iyer")))
check("the audit records that this one had no channel",
      any(e["action"] == "channel_emit" and "none" in str(e["detail"].get("channel"))
          for e in wb["audit"]))

# ===========================================================================
print("\n[recovery validity]")
for arm, expect_merge in (("ALIAS", True), ("ALIAS_SILENT", True),
                          ("CLEAN", False), ("REQCHG", False)):
    setup(arm)
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True)
    v = verdict()
    check(f"golden 1.0 on {arm} - ONE policy, which re-reads the registry "
          f"before writing the identity out, the same way it re-reads the "
          f"appointment list before booking",
          g.returncode == 0 and v["dense_reward"] == 1.0,
          f"dense={v['dense_reward']}")
    if expect_merge:
        check(f"  ...and on {arm} it demonstrably resolved the merge",
              v["metrics"]["registry_rechecked_after_merge"] is True
              and v["name_surfaces"]["canonical"] == "Priya Sharma-Iyer"
              and v["entity_binding"]["is_canonical_record"] is True)

for arm, must_fail in (("ALIAS", True), ("ALIAS_SILENT", True), ("CLEAN", False)):
    setup(arm)
    subprocess.run([PY, os.path.join(TASK, "naive_patch.py")], capture_output=True)
    v = verdict()
    if must_fail:
        check(f"the naive policy FAILS {arm} - it read the registry once and "
              f"never again",
              not v["terminal_success"] and v["wrong_entity"] is True
              and "WRONG ENTITY" in (v.get("diagnosis") or ""),
              f"dense={v['dense_reward']}")
    else:
        check("and the SAME naive policy scores 1.0 on CLEAN - so its failure "
              "is caused by the merge and not by the policy being bad. This is "
              "what makes the arm a phenomenon rather than a decoration",
              v["dense_reward"] == 1.0, f"dense={v['dense_reward']}")

# ===========================================================================
print("\n[verifier robustness]")
setup("ALIAS")
c = C()
trip(c, "Priya Sharma", "priya.sharma@example.com")
propagate(c, "Priya Sharma")
v = verdict()
check("carried the superseded name to all three surfaces -> WRONG ENTITY named",
      v["dense_reward"] == 0.8 and v["wrong_entity"] is True
      and v["invariants"]["times_agree"] is False
      and "WRONG ENTITY" in v["diagnosis"], f"dense={v['dense_reward']}")

setup("ALIAS")
c = C()
trip(c, "Priya Sharma-Iyer", "priya.sharma-iyer@example.com")
propagate(c, "Priya Sharma")
v = verdict()
check("resolved it on the booking but left the CALENDAR and chat on the old "
      "label -> still fails, and it is still the entity failure: a booking "
      "nobody else can match to the patient is the doc's "
      "'mismatches calendar/chat/CRM'",
      v["dense_reward"] == 0.8 and v["wrong_entity"] is True
      and v["name_surfaces"]["booking"] is True
      and v["name_surfaces"]["calendar"] is False,
      f"dense={v['dense_reward']}")

setup("ALIAS")
c = C()
trip(c, "Priya Sharma-Iyer", "priya.sharma-iyer@example.com")
propagate(c, "Priya Sharma-Iyer")
v = verdict()
check("resolved it everywhere -> 1.0 and no signature",
      v["dense_reward"] == 1.0 and v["wrong_entity"] is False,
      f"dense={v['dense_reward']}")

setup("ALIAS")
c = C()
trip(c, "Priya Sharma-Iyer", "priya.sharma-iyer@example.com")
propagate(c, "Priya Sharma-Iyer", chat=
          "Priya Sharma-Iyer's influenza vaccination is booked for 15:00 on "
          "2026-08-20 at Northgate Main (APT-20451). Note: her records were "
          "merged this morning - she was previously on file as Priya Sharma "
          "(p_2119), now p_1842.")
v = verdict()
check("a message that EXPLAINS the merge by naming the old identity is "
      "reporting, not asserting -> still 1.0. Four earlier arms each lost a "
      "correct rollout to a check that was one inflection too narrow",
      v["dense_reward"] == 1.0 and v["wrong_entity"] is False,
      f"dense={v['dense_reward']}")

setup("CLEAN")
c = C()
trip(c, "Priya Sharma", "priya.sharma@example.com")
propagate(c, "Priya Sharma")
v = verdict()
check("CLEAN is unaffected by the new term: no merge, no signature, 1.0 as "
      "before", v["dense_reward"] == 1.0 and v["wrong_entity"] is False
      and v["name_surfaces"]["checked"] is True,
      f"dense={v['dense_reward']}")

setup("ALIAS")
c = C()
trip(c, "Priya Sharma-Iyer", "priya.sharma-iyer@example.com")
v = verdict()
check("ran out of turns before writing the calendar and the chat -> "
      "times_agree fails because the surfaces do not agree, but this is NOT "
      "called an entity failure: 'wrong' and 'absent' are different things, "
      "and a truncated episode must not be reported as a phenomenon it "
      "actually handled correctly",
      v["dense_reward"] == 0.8 and v["wrong_entity"] is False
      and v["name_surfaces"]["booking"] is True
      and v["name_surfaces"]["present"]["calendar"] is False
      and "never reached" in v["diagnosis"], f"dense={v['dense_reward']}")

setup("ALIAS")
c = C()
trip(c, "Priya S.", "priya.s@northgate-health.example")
propagate(c, "Priya Sharma-Iyer")
v = verdict()
check("a record booked under an ALIAS is still found by the verifier - a "
      "merge must never make a real appointment invisible and score the "
      "environment instead of the model",
      len(v["created_ever"]) == 1 and v["invariants"]["exactly_one_booking"],
      f"created={v['created_ever']}")

# A world with no registry has no identity authority to check against, so the
# term must be inert - and the proof is not a synthetic world but every run
# already in the archive, re-scored with today's verifier. No score may move.
import glob  # noqa: E402
ARCHIVE = ("${ENVOS_ROOT}/envos-results/"
           "task-01-northgate-clinic/*/r*/world.json")
moved, n = [], 0
for f in sorted(glob.glob(ARCHIVE)):
    w_old = json.load(open(f))
    was = json.load(open(f.replace("world.json", "reward.json")))
    now = RW.analyse(w_old)
    n += 1
    if now["dense_reward"] != was["dense_reward"] or \
            now["terminal_success"] != was["terminal_success"]:
        moved.append(f"{f.split('/')[-3]}/{f.split('/')[-2]}: "
                     f"{was['dense_reward']} -> {now['dense_reward']}")
    # the term must be applied exactly when there IS an identity authority to
    # check against - never on a world that predates the registry, always on
    # one that has it
    if now["name_surfaces"]["checked"] != bool(w_old.get("persons")):
        moved.append(f"{f.split('/')[-2]}: identity term applied="
                     f"{now['name_surfaces']['checked']} but registry present="
                     f"{bool(w_old.get('persons'))}")
check("every run already in the archive re-scores UNCHANGED - the identity "
      "term is inert on a world with no registry, so extending times_agree "
      "did not silently re-write history",
      n > 0 and not moved, f"{n} archived runs, {len(moved)} moved")
for m in moved[:5]:
    print("        ", m)

setup("CLEAN")
c = C()
trip(c, "Priya Sharma", "priya.sharma@example.com")
propagate(c, "Priya Sharma")
w_reg = wjson()
w_noreg = copy.deepcopy(w_reg)
w_noreg.pop("persons", None)
for a in w_noreg["appointments"]:
    a.pop("person_id", None)
check("and the same episode scores identically with the registry present and "
      "absent, so the term adds a check without moving the baseline",
      RW.analyse(w_reg)["dense_reward"] == RW.analyse(w_noreg)["dense_reward"]
      and RW.analyse(w_noreg)["name_surfaces"]["checked"] is False,
      f"{RW.analyse(w_reg)['dense_reward']} == "
      f"{RW.analyse(w_noreg)['dense_reward']}")

bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
