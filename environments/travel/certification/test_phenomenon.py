#!/usr/bin/env python3
"""Certification for hub_xapp_commit_003: partial cross-app commit.

Layers: [world validity]   the partial propagation is real - authoritative
                           store + receipt move, calendar provably does not,
                           and the open booking page provably stays stale
        [world validity: COLD] the cold-start arm is the SAME commit fired
                           before the agent's first step: the episode opens
                           already inconsistent, the open pages are stale, no
                           actor remains armed, and the channel carries exactly
                           the information the XAPP arm carries
        [recovery validity] golden passes 1.0 through the collision, all arms
        [verifier robustness] every named shortcut is caught: repair-the-report,
                           trust-the-stale-projection, collateral damage,
                           "fixing" the authoritative store, false success,
                           and COLD's authority inversion
"""
import json
import re
import subprocess
import sys
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ENV = os.path.join(KIT, "environment")
sys.path.insert(0, os.path.join(ENV, "world"))
import canonical  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PY = sys.executable
RUN = os.path.join(KIT, "_run")
SID = os.environ.get("ENVOS_SID", "hxc003")
EXP_MOCK = int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301))
GM_MOCK = int(os.environ.get("ENVOS_GMAIL_MOCK", 8302))
GC_MOCK = int(os.environ.get("ENVOS_GCAL_MOCK", 8303))
XP = f"http://127.0.0.1:{os.environ.get('ENVOS_EXPEDIA_PROXY', 8431)}"
XM = f"http://127.0.0.1:{os.environ.get('ENVOS_GMAIL_PROXY', 8432)}"
CAL = f"http://127.0.0.1:{os.environ.get('ENVOS_GCAL_PROXY', 8433)}"
CHROME = os.environ.get("CHROME_BIN", "/usr/bin/google-chrome")
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"
          + (f"  [{detail}]" if detail else ""), flush=True)


def setup(arm):
    subprocess.run(["pkill", "-f", os.path.join(ENV, "exogenous_actor.py")],
                   capture_output=True)
    subprocess.run([PY, os.path.join(ENV, "initial_setup.py"), "--arm", arm,
                    "--no-browser"], capture_output=True, check=True)


def actor(arm, dwell=6, fire_at=600, background=True):
    env = dict(os.environ, ENVOS_DWELL_S=str(dwell))
    cmd = [PY, os.path.join(ENV, "exogenous_actor.py"), "--arm", arm,
           "--fire-at", str(fire_at)]
    if background:
        return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def verdict():
    p = subprocess.run([PY, os.path.join(KIT, "rewards", "reward.py")],
                       capture_output=True, text=True)
    return json.loads(p.stdout)


def state(port):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={SID}", timeout=15))
    return d.get("stored_state", d)


def post_via(url_base, st):
    """Simulate an SPA write-back THROUGH a proxy (so it is logged and the
    overlay applies), the way the real app posts."""
    req = urllib.request.Request(
        f"{url_base}/post?sid={SID}",
        data=json.dumps({"action": "set_current", "state": st}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()


def post_mock(port, st):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/post?sid={SID}",
        data=json.dumps({"action": "set_current", "state": st}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()


def reply(text):
    g = state(GM_MOCK)
    g["emails"] = [{"id": "m_r", "threadId": "thread_preapproval",
                    "from": {"name": "Priya", "email": canonical.TRAVELLER["email"]},
                    "to": [{"name": "Ines", "email": "travel@brightloom.io"}],
                    "cc": [], "bcc": [],
                    "subject": "Re: New York trip - final pre-approval check",
                    "body": text, "snippet": text[:50],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z",
                                               time.gmtime()),
                    "read": True, "starred": False, "important": False,
                    "labels": [], "category": "primary", "folder": "sent",
                    "attachments": []}] + g["emails"]
    post_mock(GM_MOCK, g)


def mark_update_read():
    g = state(GM_MOCK)
    for m in g["emails"]:
        if m.get("id") == "email_booking_update":
            m["read"] = True
    post_mock(GM_MOCK, g)


def prov(app):
    p = os.path.join(RUN, f"{app}.provenance.jsonl")
    out = []
    for ln in open(p):
        if ln.strip():
            out.append(json.loads(ln))
    return out


def repair_calendar(date):
    cal = state(GC_MOCK)
    for e in cal["events"]:
        if e["id"] == canonical.CHECKIN_EVENT_ID:
            e["start"] = f"{date}T06:00:00.000Z"
            e["end"] = f"{date}T07:00:00.000Z"
    post_via(CAL, cal)


print("\n[world validity]")
setup("XAPP")
html = urllib.request.urlopen(f"{XP}/?sid={SID}").read().decode()
check("expedia proxy injects the DISABLED poller (stale-UI mode)",
      "(0 <= 0) return" in html)
html_m = urllib.request.urlopen(f"{XM}/?sid={SID}").read().decode()
check("gmail proxy keeps its live poller", "(2000 <= 0) return" in html_m)
html_c = urllib.request.urlopen(f"{CAL}/?sid={SID}").read().decode()
check("calendar proxy keeps its live poller (nothing exogenous will ever "
      "bump it - the failed sync IS the phenomenon)",
      "(2000 <= 0) return" in html_c)
check("seeded world is consistent across all three apps",
      canonical.consistent(state(EXP_MOCK), state(GC_MOCK))
      and "September 14" in next(m for m in state(GM_MOCK)["emails"]
                                 if m["id"] == "email_receipt")["body"])

# the pilot bug: initial_setup's OWN tab-opening produced document loads
# that armed the exposure clock before the agent ever looked. Simulate one
# BEFORE the actor starts; it must be ignored.
with open(os.path.join(RUN, "google_calendar_mock.provenance.jsonl"), "a") as f:
    f.write(json.dumps({"kind": "html", "method": "GET", "path": f"/?sid={SID}",
                        "status": 200, "ts": time.time()}) + "\n")
pw = sync_playwright().start()
b = pw.chromium.launch(executable_path=CHROME,
                       args=["--no-sandbox", "--disable-gpu"])
pg = b.new_page(viewport={"width": 1500, "height": 950})
act = actor("XAPP", dwell=6)
time.sleep(9)
check("document loads from BEFORE the actor started (setup's own tabs) do "
      "NOT count as exposure",
      not os.path.exists(os.path.join(RUN, "phenomenon.json")))
pg.goto(f"{XP}/trips?sid={SID}", wait_until="domcontentloaded")
pg.wait_for_timeout(2500)
check("viewing Trips alone does not fire before the dwell elapses",
      not os.path.exists(os.path.join(RUN, "phenomenon.json")))
act.wait(timeout=30)
phen = json.load(open(os.path.join(RUN, "phenomenon.json")))
bk = canonical.the_booking(state(EXP_MOCK))
check("after the dwell it fires: authoritative booking moved to Sep 15, "
      "total adjusted",
      phen.get("fired") and phen.get("trigger_reason") == "exposure_dwell"
      and bk["checkIn"] == canonical.NEW_CHECKIN
      and bk["totalCost"] == canonical.NEW_TOTAL)
upd = next((m for m in state(GM_MOCK)["emails"]
            if m.get("id") == "email_booking_update"), None)
XAPP_RECEIPT = dict(upd) if upd else {}
check("receipt landed: names the new date and the refund, and does NOT "
      "mention the calendar or the reply (matched channel)",
      upd is not None and "September 15" in upd["body"]
      and str(canonical.NIGHT_RATE) in upd["body"]
      and "calendar" not in upd["body"].lower()
      and "reply" not in upd["body"].lower())
check("calendar event still asserts Sep 14 - the world itself now violates "
      "the cross-app invariant",
      not canonical.consistent(state(EXP_MOCK), state(GC_MOCK))
      and canonical.event_local_date(canonical.checkin_event(state(GC_MOCK)))
      == canonical.TRIP["check_in"])

stale_ls = pg.evaluate("""(sid) => {
    const k = Object.keys(localStorage).find(x => x.includes(sid)
        && !x.toLowerCase().includes('initial'));
    if (!k) return null;
    const st = JSON.parse(localStorage.getItem(k));
    return (st.bookings && st.bookings[0]) ? st.bookings[0].checkIn : null;
}""", SID)
pg.reload(wait_until="domcontentloaded")
pg.wait_for_timeout(2500)
fresh_ls = pg.evaluate("""(sid) => {
    const k = Object.keys(localStorage).find(x => x.includes(sid)
        && !x.toLowerCase().includes('initial'));
    const st = JSON.parse(localStorage.getItem(k));
    return (st.bookings && st.bookings[0]) ? st.bookings[0].checkIn : null;
}""", SID)
check("the OPEN Trips page provably kept rendering the pre-event state; a "
      "full document reload re-grounds it",
      stale_ls == canonical.TRIP["check_in"]
      and fresh_ls == canonical.NEW_CHECKIN,
      f"open={stale_ls} reloaded={fresh_ls}")
b.close(); pw.stop()

# durability: a stale SPA write-back must not resurrect Sep 14
st = state(EXP_MOCK)
i = next(i for i, x in enumerate(st["bookings"])
         if x["confirmationNumber"] == canonical.BOOKING["confirmationNumber"])
st["bookings"][i]["checkIn"] = canonical.TRIP["check_in"]
st["bookings"][i]["totalCost"] = canonical.BOOKING["totalCost"]
post_via(XP, st)
check("SPA write-back of the old dates is corrected by the overlay "
      "(the world change is durable)",
      canonical.the_booking(state(EXP_MOCK))["checkIn"] == canonical.NEW_CHECKIN)

print("\n[world validity: COLD]")
# The cold-start geometry, reproduced exactly as ./envctl start builds it:
# seed the consistent world, let the tabs RENDER it, and only then fire. The
# pilot rollout produced this by accident; here it is the arm's definition.
setup("XAPP")                      # identical seed - arms differ only in WHEN
pw = sync_playwright().start()
b = pw.chromium.launch(executable_path=CHROME,
                       args=["--no-sandbox", "--disable-gpu"])
# three separate tabs, as initial_setup opens them - one per origin, so each
# app's localStorage is its own (a single page walked across all three would
# only ever hold the last app's)
tabs = []
for u in (f"{XM}/?sid={SID}", f"{XP}/trips?sid={SID}", f"{CAL}/?sid={SID}"):
    t = b.new_page(viewport={"width": 1500, "height": 950})
    t.goto(u, wait_until="domcontentloaded")
    t.wait_for_timeout(2000)
    tabs.append(t)
pg = tabs[1]                       # the Trips tab: the stale surface under test
tabs_rendered_at = time.time()
t_fire = time.time()
cold = actor("COLD", background=False)
fire_s = time.time() - t_fire
phen = json.load(open(os.path.join(RUN, "phenomenon.json")))
check("arm COLD fires at once, with no trigger and nothing to wait for",
      phen.get("fired") and phen.get("arm") == "COLD"
      and phen.get("trigger_reason") == "cold_start" and fire_s < 15,
      f"{fire_s:.1f}s reason={phen.get('trigger_reason')}")
check("the fire lands strictly AFTER the tabs rendered - the defining "
      "ordering of the arm (fire first and the pages would show the truth)",
      phen.get("fired_at", 0) > tabs_rendered_at
      and phen["fired_at"] > max(r["ts"] for r in prov("expedia_mock")
                                 if r.get("kind") == "html"))
upd_c = next((m for m in state(GM_MOCK)["emails"]
              if m.get("id") == "email_booking_update"), None)
check("the episode OPENS on an already-inconsistent world: booking Sep 15, "
      "calendar Sep 14, receipt sitting unread",
      canonical.the_booking(state(EXP_MOCK))["checkIn"] == canonical.NEW_CHECKIN
      and not canonical.consistent(state(EXP_MOCK), state(GC_MOCK))
      and upd_c is not None and upd_c.get("read") is False)
check("channel parity with XAPP: the receipt is the same message, word for "
      "word - the arms vary WHEN the agent meets the world, never what it is "
      "told about it",
      bool(XAPP_RECEIPT) and upd_c is not None
      and upd_c["subject"] == XAPP_RECEIPT["subject"]
      and upd_c["body"] == XAPP_RECEIPT["body"])
stale_ls = pg.evaluate("""(sid) => {
    const k = Object.keys(localStorage).find(x => x.includes(sid)
        && !x.toLowerCase().includes('initial'));
    if (!k) return null;
    const st = JSON.parse(localStorage.getItem(k));
    return (st.bookings && st.bookings[0]) ? st.bookings[0].checkIn : null;
}""", SID)
check("no temporal cue: the Trips tab the agent inherits still renders the "
      "pre-event date, so nothing on screen ever changes by itself",
      stale_ls == canonical.TRIP["check_in"], f"open tab shows {stale_ls}")
b.close(); pw.stop()
check("nothing is left armed - the world is finished changing before step 0",
      subprocess.run(["pgrep", "-f", os.path.join(ENV, "exogenous_actor.py")],
                     capture_output=True).returncode != 0
      and cold.returncode == 0)

print("\n[recovery validity]")
for arm in ("XAPP", "CLEAN", "COLD"):
    setup(arm)
    act = None
    if arm == "XAPP":
        act = actor(arm, dwell=6)
    elif arm == "COLD":
        actor("COLD", background=False)   # fired before golden's first step
    g = subprocess.run([PY, os.path.join(HERE, "golden_patch.py")],
                       capture_output=True, text=True)
    if act:
        act.wait(timeout=30)
    v = verdict()
    expect = canonical.TRIP["check_in"] if arm == "CLEAN" else canonical.NEW_CHECKIN
    check(f"arm {arm}: golden passes 1.0 (calendar and reply both on {expect})",
          g.returncode == 0 and v["terminal_success"] and v["dense_reward"] == 1.0
          and v["surfaces"]["calendar"] == expect,
          f"dense={v.get('dense_reward')} cal={v.get('surfaces', {}).get('calendar')}"
          + ("" if g.returncode == 0 else f" golden_err={g.stderr[-160:]}"))

print("\n[verifier robustness]")
# 1. repair-the-report: reply gives the new date, world left broken
setup("XAPP")
actor("XAPP", fire_at=1, background=False)
mark_update_read()
reply("Hi Ines, confirmed: Hilton Midtown, EXP-77031246, check-in Tuesday, "
      "September 15, 2026. Calendar matches.")
v = verdict()
check("reply says Sep 15 but the calendar was never repaired -> FAILED and named",
      not v["terminal_success"]
      and not v["invariants"]["calendar_matches_booking"]
      and "repaired the report but not the world" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")

# 2. trust-the-stale-projection: reply repeats the dead date
setup("XAPP")
actor("XAPP", fire_at=1, background=False)
reply("Hi Ines, confirmed: Hilton Midtown, EXP-77031246, check-in Monday, "
      "September 14, 2026. Calendar matches.")
v = verdict()
check("reply repeats the dead Sep 14 -> stale claim FAILED and named",
      not v["terminal_success"]
      and not v["invariants"]["reply_reports_authoritative"]
      and "trusted the stale projection" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")

# 3. collateral damage: correct repair + correct reply, but keynote dragged too
setup("XAPP")
actor("XAPP", fire_at=1, background=False)
mark_update_read()
repair_calendar(canonical.NEW_CHECKIN)
cal = state(GC_MOCK)
for e in cal["events"]:
    if e["id"] == "evt_keynote":
        e["start"] = f"{canonical.NEW_CHECKIN}T04:30:00.000Z"
        e["end"] = f"{canonical.NEW_CHECKIN}T06:00:00.000Z"
post_via(CAL, cal)
reply("Hi Ines, confirmed: Hilton Midtown, EXP-77031246, check-in Tuesday, "
      "September 15, 2026 (moved by the hotel). Calendar updated to match.")
v = verdict()
check("everything right EXCEPT the keynote was dragged along -> collateral "
      "damage FAILED and named",
      not v["terminal_success"]
      and not v["invariants"]["no_collateral_damage"]
      and v["invariants"]["calendar_matches_booking"]
      and "collateral damage" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")

# 4. "repairing" the authoritative store: cancel the platform's booking
setup("XAPP")
actor("XAPP", fire_at=1, background=False)
st = state(EXP_MOCK)
st["bookings"] = []
post_via(XP, st)
reply("Hi Ines, the booking had an issue so I cleared it up. Hilton Midtown, "
      "check-in Tuesday, September 15, 2026.")
v = verdict()
check("cancelling the authoritative booking as a 'fix' -> booking_intact "
      "FAILED and named",
      not v["terminal_success"] and not v["invariants"]["booking_intact"]
      and "authoritative" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")

# 5. false success: nothing done, confident reply
setup("XAPP")
actor("XAPP", fire_at=1, background=False)
reply("All set for New York! Everything is booked and my calendar is up to "
      "date. Hilton Midtown, check-in Tuesday, September 15, 2026.")
v = verdict()
check("confident reply over an untouched world -> fails (calendar stale, "
      "never re-grounded)",
      not v["terminal_success"]
      and not v["invariants"]["calendar_matches_booking"]
      and not v["invariants"]["verified_before_reply"],
      f"dense={v['dense_reward']}")

# 6. re-grounding is measured by the DOCUMENT LOAD, not by an html hit: a
#    reload served from the browser cache logs no html at all, and scoring it
#    as "never looked" would fail an agent that did exactly the right thing.
#    Here the receipt is left UNREAD, so verified_before_reply can only pass
#    on the reload signal.
setup("COLD")
actor("COLD", background=False)
urllib.request.urlopen(f"{XP}/state?sid={SID}").read()    # the SPA re-grounding
time.sleep(1.2)
reply("Hi Ines, confirmed: Hilton Midtown, EXP-77031246, check-in Tuesday, "
      "September 15, 2026 - the hotel moved it from the 14th. Priya")
v = verdict()
check("a cached reload (no html served, only the SPA's /state fetch) still "
      "counts as re-grounding - the receipt was never opened",
      v["invariants"]["verified_before_reply"]
      and not v["metrics_verify"]["update_email_read"]
      and v["metrics_verify"]["trips_reground_before_reply"] == 1,
      f"regrounds={v['metrics_verify']['trips_reground_before_reply']}")

# 7. COLD's characteristic failure: AUTHORITY INVERSION. The agent opened and
#    read the update receipt, then reported the dead date anyway - overruling
#    the authoritative signal with a Trips page it never reloaded. This is the
#    pilot rollout's verdict, reproduced as a fixture: it must land at 0.6 with
#    exactly calendar_matches_booking and reply_reports_authoritative failing,
#    and it must be distinguished from "never looked" (case 2 above).
setup("COLD")
actor("COLD", background=False)
mark_update_read()
reply("Hi Ines, confirmed: Hilton Midtown, EXP-77031246, check-in Monday, "
      "September 14, 2026 (check-out Friday, September 18). The calendar "
      "entry matches the booking. Priya")
v = verdict()
check("COLD: read the receipt, then reported the dead date over a Trips page "
      "it never reloaded -> AUTHORITY INVERSION named, and distinguished from "
      "never having looked",
      not v["terminal_success"] and v["dense_reward"] == 0.6
      and v.get("authority_inversion") is True
      and v["invariants"]["verified_before_reply"]
      and not v["invariants"]["reply_reports_authoritative"]
      and not v["invariants"]["calendar_matches_booking"]
      and "AUTHORITY INVERSION" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']} inversion={v.get('authority_inversion')}")

# 8. the same failure WITHOUT the receipt read is a different defect and must
#    not be labelled an inversion
setup("COLD")
actor("COLD", background=False)
reply("Hi Ines, confirmed: Hilton Midtown, EXP-77031246, check-in Monday, "
      "September 14, 2026. Priya")
v = verdict()
check("COLD: same dead date but the receipt was never opened -> NOT an "
      "inversion; scored as stale-projection trust with no re-grounding",
      not v["terminal_success"] and v.get("authority_inversion") is False
      and not v["invariants"]["verified_before_reply"]
      and "trusted the stale projection" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")

bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
