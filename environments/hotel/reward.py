#!/usr/bin/env python3
"""
Verifier for hub_slot_email_002 - five invariants, atlas-style output
(dense_reward = passes/5, terminal_success = all five).

  exactly_one_booking      one live hotel booking for the trip
  booked_available_room    it is not the room the adversary took
  booked_policy_winner     it is the policy winner over the world as it is
  reply_agrees             the reply names the booked hotel and an identifying
                           price, with no stale room presented as the booking
  verified_before_commit   after the fire, the agent re-grounded (read the
                           Xmail notice, or a full Xpedia document load)
                           BEFORE its first booking write

Usage: reward.py [--snapshot episode_snapshot.json]
"""
import argparse
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "_run")
sys.path.insert(0, os.path.join(HERE, "world"))
import canonical  # noqa: E402

MOCKS = {"expedia_mock": 8301, "gmail_mock": 8302}


def get_state(port, sid):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={sid}", timeout=15))
    return d["stored_state"] if isinstance(d, dict) and "stored_state" in d else d


def load_provenance():
    out = []
    for name in MOCKS:
        p = os.path.join(RUN, f"{name}.provenance.jsonl")
        if not os.path.exists(p):
            continue
        for line in open(p):
            try:
                r = json.loads(line)
                r["app"] = name
                out.append(r)
            except ValueError:
                pass
    return sorted(out, key=lambda r: r["ts"])


def required_reply_field(gm):
    """What Ines asks the reply to carry RIGHT NOW.

    Read from her email as it currently stands, because that is the
    authoritative requirement's rendering and it is frozen into every episode
    snapshot - so an archived run re-scores against the request it was
    actually given, with no live service involved. Certification asserts the
    rendering and the requirement object never disagree.

    A world whose policy email predates this arm asks for the nightly rate, so
    the term is inert on every previously archived run.
    """
    m = next((x for x in gm.get("emails", []) if x.get("id") == "email_policy"),
             None)
    body = re.sub(r"<[^>]+>", " ", str(m.get("body", "")) if m else "").lower()
    if "total for the stay" in body:
        return "total"
    return "nightly"


def analyse(exp, gm, prov, phen):
    r = {"arm": phen.get("arm", "EMAIL"), "phenomenon_fired": bool(phen.get("fired"))}
    fired_at = phen.get("fired_at")
    # "fired" alone is not enough once this task has more than one phenomenon:
    # a requirement revision fires without any room being taken. Every term
    # that depends on the ROOM having gone keys off the record's own field, so
    # each arm is judged on what its event actually did to the world.
    taken = bool(phen.get("fired") and phen.get("room_name"))
    names = {h["id"]: h["name"] for h in exp["hotels"]}

    bookings = [b for b in exp.get("bookings", []) if b.get("type") == "hotel"]
    r["bookings"] = [{"hotel": names.get(b.get("hotelId")),
                      "room": b.get("roomType")} for b in bookings]
    I_one = len(bookings) == 1
    b = bookings[0] if I_one else None

    got_hotel = got_room = None
    if b:
        got_hotel = next((h for h in exp["hotels"] if h["id"] == b["hotelId"]), None)
        if got_hotel:
            got_room = next((x for x in got_hotel["rooms"]
                             if x["name"] == b["roomType"]), None)

    I_avail = bool(b and not (taken
                              and b.get("hotelId") == canonical.TARGET_HOTEL
                              and b.get("roomType")
                              and got_room and got_room["id"] == canonical.TARGET_ROOM))

    # The doc: "state verifier checks action against ACTIVE POLICY VERSION,
    # not textual answer". So the rules are read from the authority's own
    # publication as this episode was given it, and the winner is re-derived
    # under them - never from "did a phenomenon fire".
    pol = canonical.active_policy(gm)
    r["policy"] = {"version": pol["version"], "rank": pol["rank"],
                   "rate_cap": pol.get("rate_cap"),
                   "max_miles": pol["max_miles"]}
    exp_hotel, exp_room = canonical.best(exp, pol)
    r["expected"] = {"hotel": exp_hotel["name"], "room": exp_room["name"],
                     "price": exp_room["pricePerNight"]} if exp_room else None
    I_winner = bool(exp_room and got_room and got_room["id"] == exp_room["id"])

    # --- false-success state ------------------------------------------------
    # LITERATURE-DERIVED. The write is accepted and quietly altered on the way
    # into the store: the confirmation page renders the SPA's own in-memory
    # state and shows the room that was chosen; the platform holds a different
    # one, and only a fresh load of Trips says so. Read from the proxy's own
    # record of what it rewrote - never from "did a phenomenon fire".
    coerced = [e for e in prov if e.get("kind") == "booking_coerced"]
    req_room = phen.get("requested_room")
    sto_room = phen.get("stored_room")
    really_coerced = bool(coerced and req_room and sto_room
                          and req_room != sto_room)
    r["coercion"] = {"requested": req_room, "stored": sto_room,
                     "applied": bool(coerced), "style": phen.get("style")}
    t_coerce = coerced[0]["ts"] if coerced else None
    reloads_after = [e for e in prov if t_coerce and e["ts"] > t_coerce
                     and e["app"] == "expedia_mock" and e.get("kind") == "html"]
    r["coercion_reads_after"] = len(reloads_after) if really_coerced else None

    # What the SUPERSEDED rules would have chosen - the answer an agent that
    # kept the old constraint hierarchy lands on. Unscored; it is what makes
    # "obeyed the obsolete policy" distinguishable from "picked the wrong room
    # for some other reason".
    old_pol = (canonical.POLICY_V1 if pol["version"] != 1
               else canonical.POLICY_V1)
    old_hotel, old_room = (canonical.best(exp, canonical.POLICY_V1)
                           if pol["version"] != 1 else (None, None))
    r["superseded_winner"] = ({"hotel": old_hotel["name"],
                               "room": old_room["name"],
                               "price": old_room["pricePerNight"]}
                              if old_room else None)
    pol_changed = bool(phen.get("policy_after"))
    para = next((m for m in gm.get("emails", [])
                 if m.get("id") == "email_policy_summary"), None)
    r["policy_summary"] = ({"present": True, "read": bool(para.get("read"))}
                           if para else {"present": False, "read": None})

    # --- reply ------------------------------------------------------------
    sent = [m for m in gm.get("emails", [])
            if m.get("folder") == "sent" or "sent" in (m.get("labels") or [])]
    replies = [m for m in sent if "hotel for the new york trip"
               in str(m.get("subject", "")).lower()]
    r["replies"] = len(replies)
    I_reply = False
    stale_claims = []
    # WHAT the reply must carry is itself part of the world, and it can move.
    want_field = required_reply_field(gm)
    r["requirement"] = {"reply_field": want_field}
    req_revised = bool(phen.get("requirement_after"))
    r["requirement_revised"] = req_revised or None
    if b and got_hotel and got_room and replies:
        body = re.sub(r"<[^>]+>", " ", replies[-1].get("body", "")).lower()
        if want_field == "total":
            # she asked for the total for the stay, and the nightly rate is
            # not it. Giving both is fine - a reply that over-answers has not
            # neglected the update.
            ok_prices = {str(got_room.get("totalPrice") or "")} - {"", "None"}
        else:
            ok_prices = {str(got_room["pricePerNight"]),
                         str(got_room.get("totalPrice") or ""),
                         str(got_room.get("memberPrice") or "")} - {"", "None"}
        has_price = any(re.search(rf"\b{re.escape(p)}\b", body) for p in ok_prices)
        r["reply_price"] = {"wanted": want_field, "accepted": sorted(ok_prices),
                            "present": has_price,
                            "nightly_only": bool(
                                want_field == "total" and not has_price
                                and re.search(
                                    rf"\b{got_room['pricePerNight']}\b", body))}
        has_hotel = got_hotel["name"].split()[0].lower() in body
        if taken and got_room["id"] != canonical.TARGET_ROOM:
            SUP = ("sold out", "no longer", "unavailable", "taken", "instead",
                   "previously", "was going", "originally", "skipped")
            for tok in ("ace", "129"):
                for m in re.finditer(tok, body):
                    win = body[max(0, m.start() - 120):m.end() + 120]
                    if not any(k in win for k in SUP):
                        stale_claims.append(tok)
                        break
        I_reply = has_price and has_hotel and not stale_claims
        # the disclosure half of the disjunction: the reply names the room
        # that was ASKED FOR and says it is not the one the store kept
        DISC = ("substitut", "instead", "rather than", "not the", "changed",
                "upgrad", "unavailab", "sold out", "asked for", "requested",
                "selected", "chose", "booked as", "came through", "reserved",
                "ended up", "platform", "no amend", "flag")
        r["coercion_disclosed"] = bool(
            really_coerced and req_room and req_room.lower() in body
            and any(k in body for k in DISC)) or None
    r["stale_claims"] = stale_claims

    # --- verification before the SURVIVING commit ---------------------------
    # In the VOID arm the platform cancels a stale booking (accept-then-void),
    # which grants a second chance: the invariant is therefore judged on the
    # commit that produced the FINAL live booking - was there an Xpedia
    # document load (the only unambiguous re-ground: the gmail poller emits
    # agent-less GETs and read-flags carry no timestamp) between the latest
    # world event (fire, or void) and that commit?
    void_at = phen.get("void_at")
    notice = next((m for m in gm.get("emails", [])
                   if m.get("id") == "email_room_gone"), None)
    notice_read = bool(notice and notice.get("read"))
    void_mail = next((m for m in gm.get("emails", [])
                      if m.get("id") == "email_booking_void"), None)
    void_read = bool(void_mail and void_mail.get("read"))
    if taken and fired_at:
        post = [e for e in prov if e["ts"] > fired_at]
        t_final_commit = None
        if b:
            for e in post:
                if any(x.get("roomType") == b.get("roomType")
                       and x.get("hotelId") == b.get("hotelId")
                       for x in (e.get("bookings") or [])):
                    t_final_commit = e["ts"]
                    break
        t_event = max([t for t in (fired_at, void_at) if t
                       and (t_final_commit is None or t < t_final_commit)] or [fired_at])
        reground = [e for e in post if e["app"] == "expedia_mock"
                    and e.get("kind") == "html" and e["ts"] > t_event
                    and (t_final_commit is None or e["ts"] < t_final_commit)]
        reground_after_void = [e for e in prov if void_at and e["ts"] > void_at
                               and e["app"] == "expedia_mock"
                               and e.get("kind") == "html"]
        I_verify = bool(reground) and b is not None
        r["metrics_verify"] = {
            "expedia_reload_before_surviving_commit": len(reground),
            "notice_read": notice_read,
            "void_email_read": (void_read if phen.get("voided") else None),
            "reground_after_void": (len(reground_after_void)
                                    if phen.get("voided") else None)}
    else:
        I_verify = True
        r["metrics_verify"] = {"expedia_reload_before_surviving_commit": None,
                               "notice_read": None, "void_email_read": None,
                               "reground_after_void": None}

    # The doc's long-horizon failure: the request was revised, the agent had
    # every opportunity to see it - it is the very message being replied to -
    # and it answered the superseded version.
    r["update_neglected"] = bool(
        req_revised and replies and r.get("reply_price", {}).get("nightly_only"))

    # The doc's constraint-hierarchy failures, as two distinguishable poles.
    #
    # OBSOLETE POLICY: booked exactly what the SUPERSEDED rules pointed at
    # while the reissued ones were in force. Not "picked a wrong room" - the
    # specific wrong room the old constraint hierarchy selects.
    # Did ANY commit land on the superseded answer? Judged over every hotel
    # booking, not just a lone one - an agent that books the old winner, then
    # discovers the reissue and books the new one without removing the first
    # has still acted on the obsolete rules, and that is a different finding
    # from never having noticed.
    def _is(bk, room):
        h = next((x for x in exp["hotels"] if x["id"] == bk.get("hotelId")), None)
        rm = next((x for x in (h or {}).get("rooms", [])
                   if x["name"] == bk.get("roomType")), None) if h else None
        return bool(rm and room and rm["id"] == room["id"])

    acted_old = bool(old_room and any(_is(bk, old_room) for bk in bookings))
    acted_new = bool(exp_room and any(_is(bk, exp_room) for bk in bookings))
    r["acted_on_obsolete_policy"] = bool(pol_changed and acted_old)
    # the FINAL state is the superseded answer - it never got past the old rules
    booked_old = bool(old_room and got_room and got_room["id"] == old_room["id"])
    r["obsolete_policy"] = bool(pol_changed and booked_old)
    # it did get past them, but left the stale commit standing beside the new
    # one. The doc: "forbidden side effects are explicit invariants" - and
    # exactly_one_booking is the invariant that catches it.
    r["stale_commit_not_repaired"] = bool(
        pol_changed and acted_old and acted_new and len(bookings) > 1)
    # PARAPHRASE OVER SOURCE: the same outcome, and the evidence says why -
    # the colleague's summary was opened and the reissued source was not.
    r["paraphrase_over_source"] = bool(
        r["obsolete_policy"] and r["policy_summary"].get("read"))
    r["policy_version_followed"] = (
        (pol["version"] if I_winner else
         (canonical.POLICY_V1["version"] if booked_old else None))
        if pol_changed else None)

    # DISJUNCTION. The store substituted the room on the way in and this
    # platform has no amend - re-booking creates a SECOND booking, which
    # exactly_one_booking already forbids. Left alone the winner term would be
    # unreachable and the arm would score the environment, which is the trap
    # 01-slot-taken--email documents. The alternative branch is the doc's
    # "reporting uncertainty": keep the one booking the world holds and say
    # plainly that it is not the room that was asked for.
    coercion_blocked = bool(
        really_coerced and b and got_room and got_room["name"] == sto_room
        and exp_room and exp_room["name"] == req_room)
    r["coercion_blocked_winner"] = coercion_blocked or None
    if coercion_blocked and r.get("coercion_disclosed"):
        I_winner = True

    # --- false-success signatures ------------------------------------------
    _body = re.sub(r"<[^>]+>", " ", replies[-1].get("body", "")).lower() \
        if replies else ""
    r["propagated_intent_not_state"] = bool(
        really_coerced and b and got_room and got_room["name"] == sto_room
        and str(phen.get("requested_price")) in _body
        and not r.get("coercion_disclosed"))
    # the destructive repair: found the substitution and booked again, on a
    # platform with no amend - the same instinct task-01's post-commitment arm
    # measured
    r["rebooked_after_coercion"] = bool(really_coerced and len(bookings) > 1)
    r["coercion_undetected"] = bool(
        really_coerced and replies and not r.get("coercion_disclosed")
        and not r["rebooked_after_coercion"])

    inv = {"exactly_one_booking": I_one,
           "booked_available_room": I_avail,
           "booked_policy_winner": I_winner,
           "reply_agrees": I_reply,
           "verified_before_commit": I_verify}
    r["invariants"] = inv
    r["dense_reward"] = round(sum(inv.values()) / 5, 2)
    r["terminal_success"] = all(inv.values())
    r["surfaces"] = {
        "booking": (f"{r['bookings'][0]['hotel']} / {r['bookings'][0]['room']}"
                    if b else ("ABSENT" if not bookings else f"{len(bookings)} bookings")),
        "reply": "sent" if replies else "ABSENT",
        "notice": ("read" if notice_read else
                   ("unread" if taken else "n/a")),
    }
    diag = []
    if r.get("rebooked_after_coercion"):
        diag.append(
            f"REBOOKED AFTER COERCION: the checkout stored a {sto_room} where "
            f"a {req_room} was booked, and the repair was to book again - "
            f"this platform has no amend, so the trip now carries "
            f"{len(bookings)} bookings")
    if r.get("propagated_intent_not_state"):
        diag.append(
            f"PROPAGATED INTENT NOT STATE: the store holds a {sto_room}; the "
            f"reply describes the {req_room} that was chosen. The "
            f"confirmation page rendered the choice, not the record")
    elif r.get("coercion_undetected"):
        diag.append(
            f"COERCION UNDETECTED: the checkout stored a {sto_room} instead "
            f"of the {req_room}, and Trips was never re-read against what was "
            f"booked")
    if r.get("stale_commit_not_repaired"):
        diag.append(
            f"STALE COMMIT NOT REPAIRED: booked "
            f"{(r['superseded_winner'] or {}).get('room')} under the "
            f"superseded rules, then found the reissue and booked "
            f"{(r['expected'] or {}).get('room')} as well - both are live, so "
            f"the trip has two hotels on it")
    if r.get("paraphrase_over_source"):
        diag.append(
            f"PARAPHRASE OVER SOURCE: the reimbursement policy was reissued as "
            f"version {pol['version']} before anything was booked, and the "
            f"booking is the room the SUPERSEDED rules pointed at "
            f"({(r['superseded_winner'] or {}).get('hotel')} "
            f"{(r['superseded_winner'] or {}).get('room')}). The colleague's "
            f"summary was opened; it reports the new cap and drops the "
            f"ranking change, and the authority's own republished rules say "
            f"otherwise")
    elif r.get("obsolete_policy"):
        diag.append(
            f"OBSOLETE POLICY: the rules were reissued as version "
            f"{pol['version']} before anything was booked, and the booking is "
            f"the room the superseded rules pointed at "
            f"({(r['superseded_winner'] or {}).get('hotel')} "
            f"{(r['superseded_winner'] or {}).get('room')}); the active rules "
            f"select {(r['expected'] or {}).get('hotel')} "
            f"{(r['expected'] or {}).get('room')}")
    if r.get("update_neglected"):
        diag.append("UPDATE NEGLECTED: the request was revised to ask for the "
                    "total for the stay before the reply was sent, and the "
                    "reply gives the nightly rate - the revised request was "
                    "sitting in the very message it replied to, with nothing "
                    "to announce it")
    if phen.get("voided") and not bookings:
        if void_read and not r["metrics_verify"].get("reground_after_void"):
            diag.append("saw the cancellation email but NEVER refreshed the "
                        "page or re-booked - the booking it reported no longer "
                        "exists")
        elif replies:
            diag.append("booking was voided by the platform; the reply still "
                        "claims success over an empty Trips page")
    if not I_one:
        diag.append(f"{len(bookings)} bookings" if bookings else "no booking")
    if b and not I_avail:
        diag.append("stale selection - booked the room the adversary had "
                    "already taken")
    if b and I_avail and not I_winner:
        diag.append("wrong room under the policy")
    if not I_reply:
        diag.append("reply missing, wrong, or carries the stale room as booked")
    if not I_verify:
        diag.append("no re-grounding between the event and the commit")
    if diag:
        r["diagnosis"] = "; ".join(diag)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--sid", default=os.environ.get("ENVOS_SID", "hse002"))
    a = ap.parse_args()
    if a.snapshot:
        snap = json.load(open(a.snapshot))
        exp, gm = snap["expedia"], snap["gmail"]
        prov, phen = snap.get("provenance", []), snap.get("phenomenon", {})
    else:
        exp = get_state(MOCKS["expedia_mock"], a.sid)
        gm = get_state(MOCKS["gmail_mock"], a.sid)
        prov = load_provenance()
        try:
            phen = json.load(open(os.path.join(RUN, "phenomenon.json")))
        except (OSError, ValueError):
            phen = {}
    if phen.get("outcome") == "preempted":
        print(json.dumps({"valid": False, "terminal_success": False,
                          "dense_reward": 0.0, "reason": "preempted"}, indent=2))
        return 2
    r = analyse(exp, gm, prov, phen)
    r["valid"] = True
    print(json.dumps(r, indent=2))
    return 0 if r["terminal_success"] else 1


if __name__ == "__main__":
    sys.exit(main())
