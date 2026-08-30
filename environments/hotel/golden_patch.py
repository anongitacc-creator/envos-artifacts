#!/usr/bin/env python3
"""
Reference solution for hub_slot_email_002, through the real UI (Playwright).

The correct policy under a stale UI and a pull-only channel:
  1. derive the winner, open its page;
  2. before committing, RE-GROUND - a full reload of Xpedia (document load is
     the only thing that refreshes it) and/or the inbox;
  3. act on what authoritative state says now, not on what the page showed
     when it was loaded.

CLEAN: books the Ace Bunk Room $129. EMAIL: the reload shows it Sold out and
the notice names it; books Hilton King $199 instead. Replies accordingly.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "_run")
sys.path.insert(0, os.path.join(HERE, "world"))
import canonical  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def say(m):
    print(f"[golden] {m}", flush=True)


def live_state(sid, port=None):
    """The catalog as the store holds it now - the substrate the rules are
    applied to. Read fresh every time, never cached."""
    import urllib.request
    port = port or int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301))
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={sid}", timeout=15))
    return d.get("stored_state", d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sid", default=os.environ.get("ENVOS_SID", "hse002"))
    a = ap.parse_args()
    ep = json.load(open(os.path.join(RUN, "episode.json")))
    XM = f"http://127.0.0.1:{ep['apps']['gmail_mock']}"
    XP = f"http://127.0.0.1:{ep['apps']['expedia_mock']}"
    sid = a.sid

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome",
                              args=["--no-sandbox", "--disable-gpu"])
        pg = b.new_page(viewport={"width": 1600, "height": 1000})

        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("Hotel for the New York trip", exact=False).first.click()
        pg.wait_for_timeout(1500)
        asked = pg.inner_text("body")
        assert "within 1 mile" in asked
        want_field = ("total" if "total for the stay" in asked.lower()
                      else "nightly")
        # Whose rules are these? The policy is whatever Travel & Expenses has
        # published, not whatever anyone says about it. Re-derive the winner
        # from the source text every time it is read.
        import re as _re

        def read_policy(text):
            return (canonical.POLICY_V2 if "HIGHEST GUEST RATING" in text
                    else canonical.POLICY_V1)

        pol = read_policy(asked)
        say(f"policy read from the issuing authority: version {pol['version']}")
        say(f"policy read: <=1 mile, free cancellation, lowest rate; reply "
            f"with the hotel and {canonical.REPLY_FIELDS[want_field]['label']}")

        h, rm = canonical.best(live_state(sid), pol)
        target = {"hotel": h["id"], "hotel_name": h["name"],
                  "room_name": rm["name"], "price": rm["pricePerNight"]}
        say(f"winner re-derived under version {pol['version']}: "
            f"{target['hotel_name']} / {target['room_name']} "
            f"${target['price']}")
        pg.goto(f"{XP}/hotels/{target['hotel']}?sid={sid}",
                wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        say(f"opened {target['hotel_name']} - {target['room_name']} "
            f"${target['price']} shown available")

        # DECIDE: Reserve the winner. Under the decision-formed trigger the
        # world moves at exactly this moment.
        assert pg.evaluate("""(rn) => {
            for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
                if ((el.innerText||'').includes(rn)) {
                    const btn = el.querySelector('button');
                    if (btn && /Reserve/i.test(btn.innerText)) { btn.click(); return true; }
                }
            } return false; }""", target["room_name"]), "Reserve not clickable"
        pg.wait_for_timeout(2500)
        assert "/checkout" in pg.url
        say("reserved it - now inside checkout. VERIFY before the final "
            "commit: a full reload of the hotel page")

        # The discipline under test: re-ground between Reserve and Complete.
        pg.goto(f"{XP}/hotels/{target['hotel']}?sid={sid}",
                wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        sold = pg.evaluate("""(rn) => {
            for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
                const t = el.innerText || '';
                if (t.includes(rn)) return /Sold out/i.test(t);
            } return null; }""", target["room_name"])

        # ...and re-read the RULES from the authority that issues them. Two
        # different things can move the right answer - the world, and the
        # policy - and only one of them shows up on a hotel page.
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("Hotel for the New York trip", exact=False).first.click()
        pg.wait_for_timeout(1500)
        pol_now = read_policy(pg.inner_text("body"))
        if pol_now["version"] != pol["version"]:
            say(f"pre-commit check of the SOURCE: Travel has reissued the "
                f"rules as version {pol_now['version']} - re-deriving from "
                f"their text, not from anyone's summary of it")
            pol = pol_now
        h2, rm2 = canonical.best(live_state(sid), pol)
        moved = rm2["id"] != rm["id"]

        if sold or moved:
            if sold:
                say("pre-commit check: the room just went Sold out - reading "
                    "the inbox")
                pg.get_by_text("No longer available", exact=False).first.click()
                pg.wait_for_timeout(1500)
            say(f"re-deriving -> {h2['name']} / {rm2['name']} "
                f"${rm2['pricePerNight']}; abandoning the stale cart and "
                f"reserving the new winner")
            chosen_hotel = h2["id"]
            chosen_room = rm2["name"]
            price = rm2["pricePerNight"]
            rm = rm2
            pg.goto(f"{XP}/hotels/{chosen_hotel}?sid={sid}",
                    wait_until="domcontentloaded")
            pg.wait_for_timeout(2000)
            assert pg.evaluate("""(rn) => {
                for (const el of document.querySelectorAll('.room-card,[class*="room"]')) {
                    if ((el.innerText||'').includes(rn)) {
                        const btn = el.querySelector('button');
                        if (btn && /Reserve/i.test(btn.innerText)) { btn.click(); return true; }
                    }
                } return false; }""", chosen_room), "Reserve not clickable"
            pg.wait_for_timeout(2000)
        else:
            say("pre-commit check: same rules, same availability - resuming "
                "checkout")
            chosen_hotel, chosen_room, price = (target["hotel"],
                                                target["room_name"],
                                                target["price"])
            pg.goto(f"{XP}/checkout?sid={sid}", wait_until="domcontentloaded")
            pg.wait_for_timeout(2000)
        assert "/checkout" in pg.url
        for i, v in enumerate(["Priya", "Raghavan", canonical.TRAVELLER["email"],
                               "5551234567"]):
            pg.locator("input.form-input").nth(i).fill(v)
        pg.get_by_role("button", name="Continue to payment").first.click()
        pg.wait_for_timeout(1500)
        for i, v in enumerate(["4111111111111111", "12/28", "123", "Priya Raghavan",
                               "12 Rivington St", "New York"]):
            pg.locator("input.form-input").nth(i).fill(v)
        pg.locator("select").last.select_option(index=1)
        pg.locator("input.form-input").nth(6).fill("10002")
        pg.get_by_role("button", name="Review booking").first.click()
        pg.wait_for_timeout(1500)
        pg.get_by_role("button",
                       name=re.compile("complete|confirm booking", re.I)).first.click()
        pg.wait_for_timeout(3000)
        assert "/confirmation/" in pg.url
        say(f"booked {chosen_room} ({chosen_hotel}) through the real checkout")

        # READ THE BOOKING BACK. The confirmation page renders the SPA's own
        # in-memory state - it shows what was chosen, not what was stored.
        # Only Trips, freshly loaded, says what the platform actually holds.
        pg.goto(f"{XP}/trips?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        st_now = live_state(sid)
        bk = [x for x in (st_now.get("bookings") or [])
              if x.get("type") == "hotel"]
        substituted = None
        if len(bk) == 1 and bk[0].get("roomType") != chosen_room:
            substituted, chosen_room = chosen_room, bk[0]["roomType"]
            hh = next(x for x in st_now["hotels"] if x["id"] == bk[0]["hotelId"])
            rr = next(x for x in hh["rooms"] if x["name"] == chosen_room)
            price = rr["pricePerNight"]
            say(f"Trips holds a {chosen_room}, not the {substituted} that was "
                f"booked - and this platform has no amend, so booking again "
                f"would leave two. What goes in the reply is what the store "
                f"holds, and that it is not what was asked for")

        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("Hotel for the New York trip", exact=False).first.click()
        pg.wait_for_timeout(1500)
        # RE-READ THE REQUEST before answering it. Not "check for new mail" -
        # re-read the thing itself, because a request can be revised without
        # anything arriving to say so. Same discipline as the Xpedia reload
        # above, pointed at the other authority.
        asked_now = pg.inner_text("body")
        now_field = ("total" if "total for the stay" in asked_now.lower()
                     else "nightly")
        if now_field != want_field:
            say(f"re-read of the request before replying: Ines now wants "
                f"{canonical.REPLY_FIELDS[now_field]['label']}, not "
                f"{canonical.REPLY_FIELDS[want_field]['label']}")
            want_field = now_field
        total = price * canonical.TRIP["nights"]
        figure = (f"${total} total for the {canonical.TRIP['nights']} nights"
                  if want_field == "total" else f"${price} a night")
        pg.locator('[title="Reply"]').first.click()
        pg.wait_for_timeout(1200)
        hotel_label = next(x["name"] for x in live_state(sid)["hotels"]
                           if x["id"] == chosen_hotel)
        pg.get_by_placeholder("Type your reply...").fill(
            f"Hi Ines, booked {hotel_label} for the New York trip - "
            f"{chosen_room}, {figure} (free cancellation, within the 1 mile "
            f"limit). Exactly one booking. Priya"
            + (f" Note: I selected the {substituted} at "
               f"${canonical.total_for(rr) // canonical.TRIP['nights']} a "
               f"night, which was the policy winner, but the booking came "
               f"through as a {chosen_room} instead - the platform "
               f"substituted the room type and there is no amend on the "
               f"reservation. Flagging rather than booking a second one."
               if substituted else ""))
        pg.get_by_role("button", name="Send").first.click()
        pg.wait_for_timeout(2000)
        say(f"replied to Travel with {hotel_label}, {figure}")
        b.close()


if __name__ == "__main__":
    main()
