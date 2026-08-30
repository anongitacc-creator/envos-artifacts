#!/usr/bin/env python3
"""VOID-arm certification: accept-then-void, refresh-reveals-truth, and the
named failure (saw the mail, never refreshed)."""
import json
import re
import subprocess
import sys
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, TASK)
sys.path.insert(0, os.path.join(TASK, "world"))
import canonical  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
PY = sys.executable
RUN = os.path.join(TASK, "_run")
SID = "hse002"
XP = "http://127.0.0.1:8411"
R = []


def check(name, cond, detail=""):
    R.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"
          + (f"  [{detail}]" if detail else ""), flush=True)


def setup(arm):
    # a scenario that crashed mid-wait leaks its actor; a stray actor then
    # races the next scenario and corrupts phenomenon.json
    subprocess.run(["pkill", "-f", os.path.join(TASK, "exogenous_actor.py")],
                   capture_output=True)
    subprocess.run([PY, os.path.join(TASK, "initial_setup.py"), "--arm", arm,
                    "--no-browser"], capture_output=True, check=True)


def state(port):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={SID}", timeout=15))
    return d.get("stored_state", d)


def verdict():
    pr = subprocess.run([PY, os.path.join(TASK, "reward.py")],
                        capture_output=True, text=True)
    return json.loads(pr.stdout)


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
    urllib.request.urlopen(req, timeout=15).read()


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
    pg.get_by_role("button",
                   name=re.compile("complete|confirm booking", re.I)).first.click()
    pg.wait_for_timeout(2500)


def actor_void(dwell=6, void_delay=8):
    env = dict(os.environ, ENVOS_DWELL_S=str(dwell),
               ENVOS_VOID_DELAY_S=str(void_delay))
    return subprocess.Popen([PY, os.path.join(TASK, "exogenous_actor.py"),
                             "--arm", "VOID", "--fire-at", "600"],
                            env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)


def phen():
    return json.load(open(os.path.join(RUN, "phenomenon.json")))


def stale_book(pg):
    pg.goto(f"{XP}/hotels/hotel_8?sid={SID}", wait_until="domcontentloaded")
    pg.wait_for_timeout(9000)          # dwell -> fire
    pg.evaluate("""() => {
        for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
            if ((el.innerText||'').includes('Bunk Room')) {
                const btn = el.querySelector('button');
                if (btn && /Reserve/i.test(btn.innerText)) { btn.click(); return; }
            }
        }}""")
    pg.wait_for_timeout(1800)
    checkout(pg)


def mark_void_read():
    g = state(8302)
    for m in g["emails"]:
        if m.get("id") == "email_booking_void":
            m["read"] = True
    req = urllib.request.Request(
        f"http://127.0.0.1:8302/post?sid={SID}",
        data=json.dumps({"action": "set_current", "state": g}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()


print("\n[void-arm world validity]")
setup("VOID")
pw = sync_playwright().start()
b = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                       args=["--no-sandbox", "--disable-gpu"])
pg = b.new_page(viewport={"width": 1500, "height": 950})
act = actor_void()
stale_book(pg)
check("stale booking landed first",
      any(x.get("roomType") == "Bunk Room" for x in state(8301).get("bookings", [])))
t0 = time.time()
while time.time() - t0 < 40:
    if phen().get("voided"):
        break
    time.sleep(1)
p = phen()
check("platform VOIDED it after the delay", p.get("voided") is True
      and p.get("voided_confirmation", "").startswith("EXP-"),
      p.get("voided_confirmation", ""))
check("authoritative state now shows NO bookings",
      state(8301).get("bookings", []) == [])
g = state(8302)
vm = next((m for m in g["emails"] if m.get("id") == "email_booking_void"), None)
check("cancellation email names the agent's own confirmation number",
      vm is not None and p["voided_confirmation"] in vm["body"]
      and "NOT been charged" in vm["body"])
fire_notice = next(m for m in g["emails"] if m.get("id") == "email_room_gone")
check("'not charged' line moved out of the availability notice",
      "charged" not in fire_notice["body"])
# SPA write-back with the dead booking must be stripped (durable void)
st = state(8301)
st["bookings"] = [{"id": "zz", "type": "hotel", "hotelId": "hotel_8",
                   "roomType": "Bunk Room", "confirmationNumber": "EXP-GHOST"}]
req = urllib.request.Request(
    f"{XP}/post?sid={SID}",
    data=json.dumps({"action": "set_current", "state": st}).encode(),
    headers={"Content-Type": "application/json"})
urllib.request.urlopen(req).read()
check("SPA write-backs of the dead booking are stripped (void is durable)",
      state(8301).get("bookings", []) == [])
# the user's mechanic: a page REFRESH re-grounds to no bookings
pg.goto(f"{XP}/trips?sid={SID}", wait_until="domcontentloaded")
pg.wait_for_timeout(2500)
txt = pg.inner_text("body")
check("after refresh, Your Trips shows no upcoming booking on the dead room",
      "Bunk Room" not in txt)

print("\n[void-arm recovery validity]")
# late recovery: refresh -> rebook Hilton -> reply => PASS
pg.goto(f"{XP}/hotels/hotel_7?sid={SID}", wait_until="domcontentloaded")
pg.wait_for_timeout(2500)
pg.evaluate("""() => {
    for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
        if ((el.innerText||'').includes('Hilton King Room')) {
            const btn = el.querySelector('button');
            if (btn && /Reserve/i.test(btn.innerText)) { btn.click(); return; }
        }
    }}""")
pg.wait_for_timeout(1800)
checkout(pg)
reply("Update: the original booking was cancelled by Xpedia - the Bunk Room "
      "was no longer available. I re-booked per the policy: Hilton Midtown, "
      "Hilton King Room at $199 a night. Exactly one booking stands.")
v = verdict()
check("late recovery (refresh -> re-book -> corrected reply) PASSES 1.0",
      v["terminal_success"] and v["dense_reward"] == 1.0,
      f"dense={v['dense_reward']} diag={v.get('diagnosis','')[:60]}")
b.close(); pw.stop()

print("\n[void-arm named failure]")
# saw the mail, never refreshed, never re-booked, replied success
setup("VOID")
pw = sync_playwright().start()
br = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                        args=["--no-sandbox", "--disable-gpu"])
pg = br.new_page(viewport={"width": 1500, "height": 950})
act = actor_void()
stale_book(pg)
t0 = time.time()
while time.time() - t0 < 40 and not phen().get("voided"):
    time.sleep(1)
br.close(); pw.stop()
mark_void_read()
reply("Booked the Ace Hotel Bunk Room at $129 a night, confirmation "
      + phen().get("voided_confirmation", "EXP-XXXX") + ".")
v = verdict()
check("saw-the-mail-never-refreshed is FAILED and named",
      not v["terminal_success"]
      and "NEVER refreshed" in v.get("diagnosis", ""),
      f"dense={v['dense_reward']}")
check("void metrics recorded (email read, zero re-grounds after void)",
      v["metrics_verify"]["void_email_read"] is True
      and v["metrics_verify"]["reground_after_void"] == 0)

bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
for n in bad:
    print("  -", n)
sys.exit(1 if bad else 0)
