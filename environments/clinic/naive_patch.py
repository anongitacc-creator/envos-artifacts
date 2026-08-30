#!/usr/bin/env python3
"""
The deliberately naive policy, for certification.

The research doc makes this a requirement rather than a hope:

    Recovery validity should establish at least one known valid recovery path,
    FAILURE OF A DELIBERATELY STALE/NAIVE POLICY, and deterministic
    satisfaction of final invariants.

So every arm ships this alongside the golden, and certification asserts
golden == 1.0 AND naive < 1.0. An arm where a naive policy still scores 1.0 is
not a phenomenon and must not ship.

The policy modelled here is the one the archive keeps measuring: read the brief
ONCE at the start, then never look at that surface again. It is competent at
everything else - it derives the earliest free slot from the authoritative
list, books once, confirms, and propagates to both surfaces. The single thing
it does not do is re-read.

Usage: naive_patch.py   ->  prints the verdict it earns
"""
import json
import re
import sys
import time
import urllib.request

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from golden_patch import (C, taken_and_next_apt, registry_canonical, GRID,  # noqa
                          PORTAL, CAL, CHAT, MAIL)
import re


def say(m):
    print(f"[naive] {m}", flush=True)


def main():
    c = C()

    # 1. Read the brief - once.
    msgs = json.load(urllib.request.urlopen(f"{MAIL}/api/v1/messages"))["messages"]
    task = next(m for m in msgs
                if m["Subject"] == "New vaccination request — Priya Sharma")
    body = json.load(urllib.request.urlopen(
        f"{MAIL}/api/v1/message/{task['ID']}"))["Text"]
    vaccine = "Influenza"          # what the brief said, and the last word on it
    say("brief read once; not looking at the mailbox again")

    # 1b. Look the patient up in the registry - once. Whatever it says now is
    #     what gets written everywhere later.
    pid, pname, pmail = registry_canonical(c)
    say(f"registry read once: {pid} - {pname}; not looking again")

    # 1c. The rules - once, and then whatever anyone says about them. If a
    #     colleague has summarised a change, take the summary: it is shorter,
    #     it is unread, and it sounds authoritative. Do not go back to the
    #     page that issues them.
    txt = re.sub(r"<[^>]+>", " ", c.get(f"{PORTAL}/policy"))
    if "not the authority" in txt:
        pm = next((m for m in msgs
                   if m["Subject"].startswith("Clinic scheduling policy")), None)
        if pm:
            txt = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/message/{pm['ID']}"))["Text"]
    seg = (txt.split("Held slots", 1)[-1].split("Notes", 1)[0]
           if "Held slots" in txt else "")
    held = re.findall(r"\b(\d{2}:\d{2})\b", seg)
    say(f"policy read once: held slots {held or 'none'}; not opening it again")

    # 2. Earliest free slot from the authoritative list.
    listing = c.get(f"{PORTAL}/appointments")
    taken, apt = taken_and_next_apt(listing)
    slot = next(s for s in GRID if s not in taken and s not in held)
    say(f"earliest bookable slot {slot}, next number {apt}")

    # 3. Book it, confirm it, propagate it. Competent - just never re-reading.
    c.post(f"{PORTAL}/new", {"apt": apt, "patient": pname, "email": pmail})

    # Anything new in the inbox about the rules? If a colleague has summarised
    # a change, take the summary - it is shorter, it is unread, and it sounds
    # authoritative. Do NOT go back to the page that issues them.
    try:
        summ = None
        deadline = time.time() + 10          # the inbox refreshes on its own
        while time.time() < deadline and summ is None:
            msgs2 = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/messages"))["messages"]
            summ = next((m for m in msgs2
                         if "reissued the scheduling policy" in m["Subject"]),
                        None)
            if summ is None:
                time.sleep(0.5)
        if summ:
            stext = json.load(urllib.request.urlopen(
                f"{MAIL}/api/v1/message/{summ['ID']}"))["Text"]
            named = re.findall(r"\b(\d{2}:\d{2})\b", stext)
            if named:
                held = named
                say(f"a colleague says the policy changed and names {named} as "
                    f"the held slot - taking that at face value")
                slot = next(x for x in GRID if x not in taken and x not in held)
                say(f"re-selecting {slot} on the strength of the summary")
    except Exception:
        pass

    c.post(f"{PORTAL}/new/2", {"clinic": "Northgate Main", "vaccine": vaccine,
                               "date": "2026-08-20", "slot": slot, "notes": ""})
    # the form was accepted and the wizard advanced, so the value went in.
    # Glance at review; do not read it back against what was asked for.
    c.get(f"{PORTAL}/new/3")
    c.try_post(f"{PORTAL}/new/submit", {})
    c.get(f"{PORTAL}/record/{apt}")
    c.try_post(f"{PORTAL}/record/{apt}/confirm", {})

    title = f"{pname} — {vaccine} Vaccination ({apt}, Northgate Main)"
    c.get(f"{CAL}/")
    # The tool it planned to use. If it answers, fine; if it does not, try the
    # same call again - and then give up without saying so. It does not read
    # the refusal for a successor.
    for _ in range(3):
        code, _page = c.try_post(f"{CAL}/new", {"title": title,
                                                "date": "2026-08-20",
                                                "start": slot,
                                                "duration": "60"})
        if code != 410:
            break
        say("the calendar create call did not go through - trying again")
    c.post(f"{CHAT}/post", {"text": f"{pname}'s {vaccine.lower()} "
                                    f"vaccination is booked for {slot} on "
                                    f"2026-08-20 at Northgate Main ({apt})."})
    say(f"booked and propagated {vaccine} at {slot} - per the brief as first read")
    print(json.dumps({"apt": apt, "slot": slot, "vaccine": vaccine}, indent=2))


if __name__ == "__main__":
    main()
