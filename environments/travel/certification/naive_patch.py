#!/usr/bin/env python3
"""
The deliberately naive policy for hub_xapp_commit_003, for certification.

The research doc makes this a requirement rather than a hope:

    Recovery validity should establish at least one known valid recovery path,
    FAILURE OF A DELIBERATELY STALE/NAIVE POLICY, and deterministic
    satisfaction of final invariants.

The policy modelled here is the one the archive keeps measuring: read the
REQUEST once at the start and never look at it again. It is competent at
everything else - it surveys both surfaces, re-grounds Trips before the
terminal act, repairs the stale calendar projection, and reports the
authoritative date. The single thing it does not do is re-read the request.

On CLEAN and XAPP that is enough and it scores 1.0. On REQCHG it answers the
superseded version of the question.
"""
import argparse
import json
import os
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
sys.path.insert(0, HERE)
from golden_patch import JS_POPOVER_BTN, mock_state  # noqa: E402


def say(m):
    print(f"[naive] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sid", default=os.environ.get("ENVOS_SID", "hxc003"))
    a = ap.parse_args()
    ep = json.load(open(os.path.join(RUN, "episode.json")))
    XM = f"http://127.0.0.1:{ep['apps']['gmail_mock']}"
    XP = f"http://127.0.0.1:{ep['apps']['expedia_mock']}"
    CAL = f"http://127.0.0.1:{ep['apps']['google_calendar_mock']}"
    sid, arm = a.sid, ep.get("arm", "XAPP")

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME,
                              args=["--no-sandbox", "--disable-gpu"])
        pg = b.new_page(viewport={"width": 1600, "height": 1000})

        # 1. read the request - ONCE.
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("final pre-approval check", exact=False).first.click()
        pg.wait_for_timeout(1500)
        asked = pg.inner_text("body")
        want_id = ("itinerary" if "itinerary number" in asked.lower()
                   else "confirmation")
        ident = canonical.IDENTIFIERS[want_id]
        say(f"request read once: hotel + {ident['label']} + check-in date; "
            f"not opening it again")

        if want_id == "itinerary":
            pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.get_by_text("View details", exact=False).first.click()
            pg.wait_for_timeout(1500)

        # 2. survey both surfaces (this is the exposure the actor watches for)
        pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        say("surveyed Trips and the calendar")

        if arm != "CLEAN":
            deadline = time.time() + 90
            while time.time() < deadline:
                try:
                    if json.load(open(os.path.join(RUN, "phenomenon.json"))) \
                            .get("fired"):
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(1)

        # 3. re-ground the ENTITY before the terminal act - competent at this.
        pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        ci_now = canonical.authoritative_checkin(mock_state(EXPEDIA_MOCK, sid))
        say(f"pre-reply check of Trips: check-in {ci_now}")

        report_ci = ("Tuesday, September 15" if ci_now == canonical.NEW_CHECKIN
                     else "Monday, September 14")
        if ci_now != canonical.TRIP["check_in"]:
            pg.goto(f"{CAL}/?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(3000)
            pg.get_by_text("Hotel check-in", exact=False).first.click()
            pg.wait_for_timeout(1200)
            if pg.evaluate(JS_POPOVER_BTN, 0):
                pg.wait_for_timeout(1200)
                dts = pg.locator('input[type="datetime-local"]')
                dts.nth(0).fill(f"{canonical.NEW_CHECKIN}T15:00")
                dts.nth(1).fill(f"{canonical.NEW_CHECKIN}T16:00")
                pg.get_by_role("button", name="Save").first.click()
                pg.wait_for_timeout(2000)
                say("repaired the stale calendar projection")

        # 3b. The rules: whatever the most convenient restatement says. If a
        #     colleague has summarised the change, take the summary - it is
        #     shorter, it is unread and at the top of the inbox, and it sounds
        #     authoritative. Do not go back to the message that issued it.
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        summ = pg.get_by_text("finance tightened the pre-approval checks",
                              exact=False)
        if summ.count():
            summ.first.click()
            pg.wait_for_timeout(1500)
            say("a colleague's summary says finance wants the confirmation "
                "number in the calendar entry's description and that it is "
                "still just the check-in entry - taking that at face value; "
                "the entry already carries the confirmation number, so "
                "nothing to do")

        # 4. reply - answering the request AS FIRST READ.
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("final pre-approval check", exact=False).first.click()
        pg.wait_for_timeout(1500)
        pg.locator('[title="Reply"]').first.click()
        pg.wait_for_timeout(1200)
        pg.get_by_placeholder("Type your reply...").fill(
            f"Hi Ines, confirmed: Hilton Midtown, {ident['label']} "
            f"{ident['value']}, check-in {report_ci}, 2026 (check-out Friday, "
            f"September 18). The calendar entry matches the booking. Priya")
        pg.get_by_role("button", name="Send").first.click()
        pg.wait_for_timeout(2000)
        say(f"replied with the {want_id} number - per the request as first read")
        b.close()


if __name__ == "__main__":
    main()
