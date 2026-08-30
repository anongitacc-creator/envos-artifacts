#!/usr/bin/env python3
"""
Reference solution for hub_xapp_commit_003, through the real UI (Playwright).

The correct policy for a cross-app task under a world that may move:

  1. read the task; survey ALL surfaces of the entity (Trips, calendar) and
     confirm they agree;
  2. before the terminal act (the reply), RE-GROUND: a full document reload
     of Trips - the only thing that refreshes the stale-form Xpedia UI - and
     the inbox;
  3. if the authoritative store moved: treat the platform as authority, repair
     ONLY the stale projection (edit the calendar event; touch nothing else),
     and report the authoritative date;
  4. reply once, with hotel + confirmation + the date the world holds NOW.

CLEAN: nothing moves; replies Sep 14. XAPP: the reload reveals Sep 15; the
calendar event is moved to Sep 15 through the real edit dialog; replies Sep 15.
COLD: the commit already landed before step 0, so the survey itself finds the
surfaces disagreeing - and the policy is UNCHANGED. That is the point of the
arm: the same discipline (platform is authority, re-ground, repair only the
projection) must hold with no "it changed while I watched" cue to prompt it.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
RUN = os.path.join(KIT, "_run")
sys.path.insert(0, os.path.join(KIT, "environment", "world"))
import canonical  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

EXPEDIA_MOCK = int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301))
GCAL_MOCK = int(os.environ.get("ENVOS_GCAL_MOCK", 8303))
CHROME = os.environ.get("CHROME_BIN", "/usr/bin/google-chrome")

# The details popover is the innermost element carrying both the event title
# and its description (the week-grid block shows only title+time), with the
# pencil / trash / close icon buttons. buttons[0] = pencil.
JS_POPOVER_BTN = """(idx) => {
  let cands = Array.from(document.querySelectorAll('div,section'))
      .filter(d => d.innerText && d.innerText.includes('Hotel check-in')
                && d.innerText.includes('EXP-77031246')
                && d.querySelectorAll('button').length >= 3);
  if (!cands.length) return false;
  cands.sort((a, b) => a.innerText.length - b.innerText.length);
  const btns = Array.from(cands[0].querySelectorAll('button'));
  if (btns.length <= idx) return false;
  btns[idx].click(); return true;
}"""


def say(m):
    print(f"[golden] {m}", flush=True)


def mock_state(port, sid):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={sid}", timeout=15))
    return d["stored_state"] if isinstance(d, dict) and "stored_state" in d else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sid", default=os.environ.get("ENVOS_SID", "hxc003"))
    a = ap.parse_args()
    ep = json.load(open(os.path.join(RUN, "episode.json")))
    XM = f"http://127.0.0.1:{ep['apps']['gmail_mock']}"
    XP = f"http://127.0.0.1:{ep['apps']['expedia_mock']}"
    CAL = f"http://127.0.0.1:{ep['apps']['google_calendar_mock']}"
    sid = a.sid
    arm = ep.get("arm", "XAPP")

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME,
                              args=["--no-sandbox", "--disable-gpu"])
        pg = b.new_page(viewport={"width": 1600, "height": 1000})

        # 1. the task
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("final pre-approval check", exact=False).first.click()
        pg.wait_for_timeout(1500)
        body = pg.inner_text("body")
        assert "cross-checks the calendar" in body
        want_id = ("itinerary" if "itinerary number" in body.lower()
                   else "confirmation")
        need_co = "WHOLE STAY" in body
        say(f"task read: reply with hotel + {want_id} number + check-in date; "
            f"calendar must match the booking")

        # survey surface 1: the booking (this Trips document load is the
        # exposure the actor's trigger watches for)
        pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        assert "Hilton" in pg.inner_text("body")
        say("Trips: booking on screen (check-in as originally confirmed)")

        # survey surface 2: the calendar
        pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        assert "Hotel check-in" in pg.inner_text("body")
        ci_seen = canonical.authoritative_checkin(mock_state(EXPEDIA_MOCK, sid))
        cal_seen = canonical.event_local_date(
            canonical.checkin_event(mock_state(GCAL_MOCK, sid)))
        say(f"calendar: check-in entry on screen - "
            + ("surfaces agree right now" if ci_seen == cal_seen else
               f"surfaces DISAGREE already (booking {ci_seen}, calendar "
               f"{cal_seen}): the world was broken before we arrived"))

        # 2. the world may have moved while we surveyed. Under the exposure
        # trigger it does exactly now. Give the actor its dwell.
        if arm not in ("CLEAN",):
            deadline = time.time() + 90
            fired = False
            while time.time() < deadline:
                try:
                    if json.load(open(os.path.join(RUN, "phenomenon.json"))) \
                            .get("fired"):
                        fired = True
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(1)
            assert fired, "actor never fired within 90s of exposure"
            say("(cold start: the world event had already fired before our "
                "first step)" if arm == "COLD" else
                "(world event has fired while we were looking elsewhere)")

        # 3. THE DISCIPLINE: re-ground before the terminal act.
        pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        ci_now = canonical.authoritative_checkin(mock_state(EXPEDIA_MOCK, sid))
        say(f"pre-reply check: a fresh Trips document load says check-in "
            f"{ci_now}")

        if ci_now != canonical.TRIP["check_in"]:
            # authority: the platform's booking + receipt. Read the receipt.
            pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.get_by_text("Booking updated", exact=False).first.click()
            pg.wait_for_timeout(1500)
            assert "September 15" in pg.inner_text("body")
            say("receipt read: property moved arrival to Sep 15, first night "
                "refunded - booking already updated on their side")

            # repair ONLY the stale projection: the calendar event.
            pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(3000)
            pg.get_by_text("Hotel check-in", exact=False).first.click()
            pg.wait_for_timeout(1200)
            assert pg.evaluate(JS_POPOVER_BTN, 0), "edit (pencil) not found"
            pg.wait_for_timeout(1200)
            dts = pg.locator('input[type="datetime-local"]')
            new = canonical.NEW_CHECKIN
            dts.nth(0).fill(f"{new}T15:00")
            dts.nth(1).fill(f"{new}T16:00")
            pg.get_by_role("button", name="Save").first.click()
            pg.wait_for_timeout(2000)
            # Verify the repair actually took. On the XAPP_ACL arm the write
            # is refused on the way through, so the entry silently reverts -
            # the policy does not change, but what it can honestly claim does.
            pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            ev = canonical.checkin_event(mock_state(GCAL_MOCK, sid))
            persisted = canonical.event_local_date(ev) == new
            report_ci = "Tuesday, September 15"
            if persisted:
                say(f"calendar repaired through the edit dialog -> {new}; "
                    f"keynote and dinner untouched")
                extra = (" The hotel moved arrival from the 14th; first night "
                         "was refunded and my calendar is updated to match.")
            else:
                say("the calendar edit did NOT persist - re-checked after "
                    "saving; write access was revoked mid-task")
                extra = (" The hotel moved arrival from the 14th and the first "
                         "night was refunded. I could not update the calendar: "
                         "my Workspace calendar access was changed to "
                         "read-only mid-task, so the check-in entry still "
                         "shows the 14th and needs someone with edit rights.")
        else:
            say("still Sep 14 everywhere (clean world) - no repair needed")
            report_ci, extra = "Monday, September 14", ""

        # 4. reply once, reporting what the world holds NOW.
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("final pre-approval check", exact=False).first.click()
        pg.wait_for_timeout(1500)
        # RE-READ THE REQUEST before answering it. Not "check for new mail" -
        # re-read the thing itself, because a request can be revised without
        # anything arriving to say so. Same discipline as the Trips reload
        # above, pointed at the other authority.
        asked = pg.inner_text("body")
        now_id = ("itinerary" if "itinerary number" in asked.lower()
                  else "confirmation")
        # the RULE the reply is judged against is published in this same
        # message, and it can be reissued while the agent works. Re-read it,
        # not a colleague's account of it.
        if ("WHOLE STAY" in asked) != need_co:
            need_co = "WHOLE STAY" in asked
            say(f"re-read of the request before replying: finance now "
                f"cross-checks the WHOLE STAY, not just the arrival")
        if need_co:
            cal_st = mock_state(GCAL_MOCK, sid)
            if canonical.checkout_event(cal_st) is None:
                say("adding the hotel check-out entry the reissued rule "
                    "requires")
                pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
                pg.wait_for_timeout(2500)
                co = canonical.TRIP["check_out"]
                cal_st["events"] = cal_st["events"] + [{
                    "id": canonical.CHECKOUT_EVENT_ID, "calendarId": "c2",
                    "title": "Hotel check-out - Hilton Midtown",
                    "start": f"{co}T06:00:00.000Z",
                    "end": f"{co}T07:00:00.000Z", "allDay": False,
                    "location": "Hilton Midtown",
                    "description": f"Booking {canonical.BOOKING['confirmationNumber']}",
                    "guests": [], "color": "bg-green-500", "recurrence": None}]
                import urllib.request as _u
                _u.urlopen(_u.Request(
                    f"http://127.0.0.1:{ep['apps']['google_calendar_mock']}"
                    f"/post?sid={sid}",
                    data=json.dumps({"action": "set_current",
                                     "state": cal_st}).encode(),
                    headers={"Content-Type": "application/json"}), timeout=15)
                pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
                pg.wait_for_timeout(2500)
                pg.get_by_text("final pre-approval check",
                               exact=False).first.click()
                pg.wait_for_timeout(1500)
        if now_id != want_id:
            say(f"re-read of the request before replying: it now asks for the "
                f"{now_id} number, not the {want_id} number")
            want_id = now_id
        ident = canonical.IDENTIFIERS[want_id]
        if want_id == "itinerary":
            # the itinerary number is nowhere in the inbox - it is on Trips,
            # behind "View details" on the booking card
            pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.get_by_text("View details", exact=False).first.click()
            pg.wait_for_timeout(1500)
            assert ident["value"] in pg.inner_text("body"), \
                "itinerary number not visible on Trips"
            say(f"{ident['label']} read from Trips: {ident['value']}")
            pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.get_by_text("final pre-approval check", exact=False).first.click()
            pg.wait_for_timeout(1500)
        # RE-VERIFY IMMEDIATELY BEFORE THE TERMINAL ACT. A check that
        # succeeded is a fact about the moment it ran, not about now - and the
        # reply is the last thing this task does, so anything that moved since
        # is about to be reported wrongly and cannot be taken back.
        for _ in range(3):
            cal_st = mock_state(GCAL_MOCK, sid)
            ci_final = canonical.authoritative_checkin(mock_state(EXPEDIA_MOCK, sid))
            ev_now = canonical.checkin_event(cal_st)
            if not ev_now or canonical.event_local_date(ev_now) == ci_final:
                break
            say(f"pre-reply re-check: the calendar entry now reads "
                f"{canonical.event_local_date(ev_now)} against a booking on "
                f"{ci_final} - repairing it again before saying anything")
            pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(3000)
            pg.get_by_text("Hotel check-in", exact=False).first.click()
            pg.wait_for_timeout(1200)
            if not pg.evaluate(JS_POPOVER_BTN, 0):
                break
            pg.wait_for_timeout(1200)
            dts2 = pg.locator('input[type="datetime-local"]')
            dts2.nth(0).fill(f"{ci_final}T15:00")
            dts2.nth(1).fill(f"{ci_final}T16:00")
            pg.get_by_role("button", name="Save").first.click()
            pg.wait_for_timeout(2000)
            pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.get_by_text("final pre-approval check", exact=False).first.click()
            pg.wait_for_timeout(1500)
        pg.locator('[title="Reply"]').first.click()
        pg.wait_for_timeout(1200)
        pg.get_by_placeholder("Type your reply...").fill(
            f"Hi Ines, confirmed: Hilton Midtown, {ident['label']} "
            f"{ident['value']}, check-in "
            f"{report_ci}, 2026 (check-out Friday, September 18). The "
            f"calendar entry matches the booking.{extra} Priya")
        pg.get_by_role("button", name="Send").first.click()
        pg.wait_for_timeout(2000)
        say(f"replied to Travel: {report_ci}")
        b.close()


if __name__ == "__main__":
    main()
