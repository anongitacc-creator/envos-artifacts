#!/usr/bin/env python3
"""
The deliberately naive policy for hub_slot_email_002, for certification.

The research doc makes this a requirement rather than a hope:

    Recovery validity should establish at least one known valid recovery path,
    FAILURE OF A DELIBERATELY STALE/NAIVE POLICY, and deterministic
    satisfaction of final invariants.

This is the golden policy with exactly two disciplines removed, both of them
about re-reading an AUTHORITY rather than the world:

  * it reads the REQUEST once and never opens it again;
  * it reads the RULES once, and if anything later says the rules moved it
    takes the most convenient restatement - the colleague's summary sitting
    unread in the inbox - instead of going back to the text that issued them.

Everything else is identical: it derives the winner from the rules it holds,
reloads Xpedia before committing, and recovers if the room goes.

On CLEAN and EMAIL that is enough and it scores 1.0. On REQCHG it answers the
superseded question; on POLICY it books what the superseded rules pointed at.
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
    print(f"[naive] {m}", flush=True)


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
        say(f"rules read ONCE: version {pol['version']}")
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

        # The rules: whatever the most convenient restatement says. If a
        # colleague has summarised the change, take the summary - it is
        # shorter, it is unread and at the top of the inbox, and it sounds
        # authoritative. Do not go back to the text that issued the rules.
        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        summary = pg.get_by_text("Travel tightened the hotel rules",
                                 exact=False)
        if summary.count():
            summary.first.click()
            pg.wait_for_timeout(1500)
            txt = pg.inner_text("body")
            m = _re.search(r"\$(\d+) a night cap", txt)
            if m:
                pol = {**pol, "rate_cap": int(m.group(1))}
                say(f"a colleague's summary says there is now a "
                    f"${m.group(1)} cap and 'everything else is as it was' - "
                    f"taking that at face value")
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
        # the confirmation page says the booking is confirmed, so it is. Do
        # not go and look at what the platform actually stored.
        say(f"booked {chosen_room} ({chosen_hotel}) through the real checkout")
        substituted = None

        pg.goto(f"{XM}/?sid={sid}", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.get_by_text("Hotel for the New York trip", exact=False).first.click()
        pg.wait_for_timeout(1500)
        # NO re-read of the request: it was read once, at the start.
        total = price * canonical.TRIP["nights"]
        figure = (f"${total} total for the {canonical.TRIP['nights']} nights"
                  if want_field == "total" else f"${price} a night")
        pg.locator('[title="Reply"]').first.click()
        pg.wait_for_timeout(1200)
        hotel_label = next(x["name"] for x in live_state(sid)["hotels"]
                           if x["id"] == chosen_hotel)
        pg.get_by_placeholder("Type your reply...").fill(
            f"Hi Ines, booked {hotel_label} for the New York trip - {figure} "
            f"(free cancellation, within the 1 mile limit). Exactly one "
            f"booking. Priya")
        pg.get_by_role("button", name="Send").first.click()
        pg.wait_for_timeout(2000)
        say(f"replied to Travel with {hotel_label}, {figure}")
        b.close()


if __name__ == "__main__":
    main()
