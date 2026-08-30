#!/usr/bin/env python3
"""Certification for hub_slot_email_002: stale-UI, email-only channel."""
import json
import re
import subprocess
import sys
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TASK, "world"))
import canonical  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PY = sys.executable
RUN = os.path.join(TASK, "_run")
SID = "hse002"
XP, XM = "http://127.0.0.1:8411", "http://127.0.0.1:8412"
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""),
          flush=True)


def setup(arm):
    # a scenario that crashed mid-wait leaks its actor; a stray actor then
    # races the next scenario and corrupts phenomenon.json
    subprocess.run(["pkill", "-f", os.path.join(TASK, "exogenous_actor.py")],
                   capture_output=True)
    subprocess.run([PY, os.path.join(TASK, "initial_setup.py"), "--arm", arm,
                    "--no-browser"], capture_output=True, check=True)


def actor(arm, dwell=6, fire_at=600, background=True):
    env = dict(os.environ, ENVOS_DWELL_S=str(dwell))
    cmd = [PY, os.path.join(TASK, "exogenous_actor.py"), "--arm", arm,
           "--fire-at", str(fire_at)]
    if background:
        return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def verdict():
    p = subprocess.run([PY, os.path.join(TASK, "reward.py")],
                       capture_output=True, text=True)
    return json.loads(p.stdout)


def state(port):
    d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/state?sid={SID}"))
    return d.get("stored_state", d)


def checkout(pg):
    for i, v in enumerate(["Priya", "Raghavan", canonical.TRAVELLER["email"],
                           "5551234567"]):
        pg.locator("input.form-input").nth(i).fill(v)
    pg.get_by_role("button", name="Continue to payment").first.click()
    pg.wait_for_timeout(1200)
    for i, v in enumerate(["4111111111111111", "12/28", "123", "Priya Raghavan",
                           "12 Rivington St", "New York"]):
        pg.locator("input.form-input").nth(i).fill(v)
    pg.locator("select").last.select_option(index=1)
    pg.locator("input.form-input").nth(6).fill("10002")
    pg.get_by_role("button", name="Review booking").first.click()
    pg.wait_for_timeout(1200)
    pg.get_by_role("button", name=re.compile("complete|confirm booking", re.I)).first.click()
    pg.wait_for_timeout(2500)


def reply(text):
    g = state(8302)
    g["emails"] = [{"id": "m_r", "threadId": "thread_policy",
                    "from": {"name": "Priya", "email": canonical.TRAVELLER["email"]},
                    "to": [{"name": "Ines", "email": "travel@brightloom.io"}],
                    "cc": [], "bcc": [],
                    "subject": "Re: Hotel for the New York trip - booking policy",
                    "body": text, "snippet": text[:50],
                    "timestamp": "2026-09-07T12:00:00.000Z", "read": True,
                    "starred": False, "important": False, "labels": [],
                    "category": "primary", "folder": "sent",
                    "attachments": []}] + g["emails"]
    req = urllib.request.Request(
        f"http://127.0.0.1:8302/post?sid={SID}",
        data=json.dumps({"action": "set_current", "state": g}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()


print("\n[world validity]")
setup("EMAIL")
html = urllib.request.urlopen(f"{XP}/?sid={SID}").read().decode()
check("expedia proxy injects the DISABLED poller (stale-UI mode)",
      "(0 <= 0) return" in html)
html_m = urllib.request.urlopen(f"{XM}/?sid={SID}").read().decode()
check("gmail proxy keeps its live poller", "(2000 <= 0) return" in html_m)
ov = json.load(open(os.path.join(RUN, "overlay.json")))
check("overlay carries no rejection rule - stale bookings will LAND",
      "contended" not in ov)

pw = sync_playwright().start()
b = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                       args=["--no-sandbox", "--disable-gpu"])
pg = b.new_page(viewport={"width": 1500, "height": 950})
act = actor("EMAIL", dwell=6)
pg.goto(f"{XP}/hotels/hotel_8?sid={SID}", wait_until="domcontentloaded")
pg.wait_for_timeout(9000)
check("viewing the room alone does NOT fire (decision-formed trigger)",
      not os.path.exists(os.path.join(RUN, "phenomenon.json")))
pg.evaluate("""() => {
    for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
        if ((el.innerText||'').includes('Bunk Room')) {
            const btn = el.querySelector('button');
            if (btn && /Reserve/i.test(btn.innerText)) { btn.click(); return; }
        }
    }}""")
pg.wait_for_timeout(3000)
act.wait(timeout=30)
phen = json.load(open(os.path.join(RUN, "phenomenon.json")))
check("clicking Reserve on the target fires it - the decision is the trigger",
      phen.get("fired")
      and phen.get("trigger_reason") == "agent_reserved_target_room")
check("the agent is now inside a client-side checkout that will not refresh",
      "/checkout" in pg.url)
check("authoritative state flipped",
      state(8301)["hotels"][7]["rooms"][0]["availability"] == "sold out")
check("notice landed in Xmail state, names only the lost room",
      any(m["id"] == "email_room_gone" and "Hilton" not in m["body"]
          and "199" not in m["body"] for m in state(8302)["emails"]))
check("the open checkout still presents the dead room as the purchase",
      "Ace Hotel" in pg.inner_text("body"))
pg.goto(f"{XP}/hotels/hotel_8?sid={SID}", wait_until="domcontentloaded")
pg.wait_for_timeout(2500)
check("a full document reload re-grounds it to Sold out",
      pg.evaluate("""() => {
          for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
              const t = el.innerText || '';
              if (t.includes('Bunk Room')) return /Sold out/i.test(t);
          } return null; }""") is True)
b.close(); pw.stop()

print("\n[recovery validity]")
for arm in ("EMAIL", "CLEAN"):
    setup(arm)
    act = actor(arm, dwell=6) if arm == "EMAIL" else None
    g = subprocess.run([PY, os.path.join(TASK, "golden_patch.py")],
                       capture_output=True, text=True)
    if act:
        act.wait(timeout=30)
    v = verdict()
    expect_room = "Hilton King Room" if arm == "EMAIL" else "Bunk Room"
    check(f"arm {arm}: golden passes 1.0 booking the {expect_room}",
          g.returncode == 0 and v["terminal_success"] and v["dense_reward"] == 1.0
          and v["bookings"] and v["bookings"][0]["room"] == expect_room,
          f"dense={v.get('dense_reward')} b={v.get('bookings')}")

print("\n[verifier robustness]")
# stale submission through the genuinely stale page
setup("EMAIL")
pw = sync_playwright().start()
b = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                       args=["--no-sandbox", "--disable-gpu"])
pg = b.new_page(viewport={"width": 1500, "height": 950})
act = actor("EMAIL", dwell=6)
pg.goto(f"{XP}/hotels/hotel_8?sid={SID}", wait_until="domcontentloaded")
pg.wait_for_timeout(3000)
clicked = pg.evaluate("""() => {
    for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
        if ((el.innerText||'').includes('Bunk Room')) {
            const btn = el.querySelector('button');
            if (btn && /Reserve/i.test(btn.innerText)) { btn.click(); return true; }
        }
    } return false; }""")
pg.wait_for_timeout(1800)
act.wait(timeout=30)      # under the decision trigger the click IS the fire
check("Reserve goes through to checkout while the world moves at that instant",
      clicked and "/checkout" in pg.url)
checkout(pg)
b.close(); pw.stop()
reply("Booked the Ace Hotel Bunk Room at $129 a night.")
v = verdict()
check("the stale booking LANDS and is failed as stale selection",
      not v["terminal_success"]
      and not v["invariants"]["booked_available_room"]
      and "stale selection" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")
check("no re-grounding before the commit is called out",
      not v["invariants"]["verified_before_commit"])

# false success: no booking at all, confident reply
setup("EMAIL")
actor("EMAIL", dwell=6, fire_at=1, background=False)
reply("Booked Hilton Midtown at $199 a night.")
v = verdict()
check("reply without any booking fails",
      not v["terminal_success"] and not v["invariants"]["exactly_one_booking"])

bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
