#!/usr/bin/env python3
"""
Exogenous actor for hub_xapp_commit_003 - partial cross-app commit.

What fires: the property moves the stay by one day. In one atomic pass over
AUTHORITATIVE state:

  xpedia booking   checkIn Sep 14 -> Sep 15, total adjusted   (authoritative)
  overlay          pins the new values against SPA write-backs (durability)
  xmail            an updated-booking receipt lands, unread    (propagated)
  calendar         NOTHING. The sync job "fails". The event
                   silently keeps Sep 14                       (stale projection)

That third line is the phenomenon: the world now violates the cross-app
invariant, and no page the agent has open changes by itself (the Xpedia
proxy runs with its reload poller disabled; the calendar was not touched).

Trigger: arm-dependent.

  XAPP  EXPOSURE-FORMED (below): the world breaks WHILE the agent watches.
  COLD  COLD-START: ./envctl start fires this actor once, synchronously,
        after initial_setup has opened and rendered the three tabs and before
        the agent takes its first step. Same commit, same matched channel -
        but the episode OPENS on the broken world: Trips and the calendar are
        already-loaded pages showing the pre-event state, and the only fresh
        signal is an unread receipt with no "it changed while I was looking"
        cue to attach it to. The pilot rollout produced this geometry by
        accident and Opus failed it 0.6 by AUTHORITY INVERSION - quoting the
        receipt and then rejecting it against a Trips tab it never reloaded.
        It is the harder arm and it is formalised here as its own.

EXPOSURE-FORMED (XAPP). The agent must have genuinely seen the consistent
world first - the clock starts at the agent's OWN first view of either
surface of the entity, and the event fires ENVOS_DWELL_S later. Two details
were learned from the pilot rollout:

  * only signals AFTER this actor started count - initial_setup opens the
    three tabs itself, and those document loads are the harness looking, not
    the agent (the pilot fired 2s into recording because of them);
  * the agent usually views an ALREADY-OPEN tab, which produces no document
    load at all - so the agent's tab-switches (agent/_actions.log, written by
    the cua toolkit) count as exposure alongside proxy-logged document loads
    and SPA posts.

Firing before genuine exposure would test perception, not stale-belief
repair. If the agent has already sent its reply when the fire would land,
the episode is 'preempted' = invalid, never scored.

Matched-channel rule: the receipt names the changed entity and the new value.
It does not mention the calendar, the reply, or anything about the agent's
task - discovering WHERE the stale projection lives is the work.
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
sys.path.insert(0, os.path.join(HERE, "world"))
import canonical  # noqa: E402

EXPEDIA_MOCK = int(os.environ.get("ENVOS_EXPEDIA_MOCK", 8301))
GMAIL_MOCK = int(os.environ.get("ENVOS_GMAIL_MOCK", 8302))
GCAL_MOCK = int(os.environ.get("ENVOS_GCAL_MOCK", 8303))
POLL_S = 0.4


def get_state(port, sid):
    d = json.load(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/state?sid={sid}", timeout=15))
    return d["stored_state"] if isinstance(d, dict) and "stored_state" in d else d


def put_state(port, sid, state):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/post?sid={sid}",
        data=json.dumps({"action": "set_current", "state": state}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).read()


def provenance():
    out = []
    for name in ("expedia_mock", "gmail_mock", "google_calendar_mock"):
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


ACTIONS_LOG = os.path.join(KIT, "agent", "_actions.log")


def agent_actions(t0):
    """The cua toolkit's action log: 'epoch.ns verb args...'. Only entries
    after t0 (this actor's start) are the agent's own episode."""
    out = []
    if not os.path.exists(ACTIONS_LOG):
        return out
    for ln in open(ACTIONS_LOG):
        ts, _, rest = ln.strip().partition(" ")
        try:
            t = float(ts)
        except ValueError:
            continue
        if t > t0:
            out.append((t, rest))
    return out


def reply_already_sent(sid):
    g = get_state(GMAIL_MOCK, sid)
    return any((m.get("folder") == "sent" or "sent" in (m.get("labels") or []))
               and "pre-approval" in str(m.get("subject", "")).lower()
               for m in g.get("emails", []))


def fire(sid):
    st = get_state(EXPEDIA_MOCK, sid)
    bi = next((i for i, b in enumerate(st.get("bookings", []))
               if b.get("confirmationNumber")
               == canonical.BOOKING["confirmationNumber"]), None)
    if bi is None:
        return {"outcome": "preempted", "fired": False,
                "reason": "seeded booking is gone"}
    b = st["bookings"][bi]
    if b.get("checkIn") == canonical.NEW_CHECKIN:
        return {"outcome": "preempted", "fired": False,
                "reason": "already moved"}
    if reply_already_sent(sid):
        return {"outcome": "preempted", "fired": False,
                "reason": "reply already sent before exposure completed"}

    before = {"checkIn": b["checkIn"], "totalCost": b["totalCost"]}
    b["checkIn"] = canonical.NEW_CHECKIN
    b["totalCost"] = canonical.NEW_TOTAL
    b["notes"] = "Check-in updated by the property"
    st["__envos_rev"] = 1
    put_state(EXPEDIA_MOCK, sid, st)

    # Durability: an open (stale) Xpedia page that later posts its whole
    # in-memory state back must not resurrect Sep 14. Generic overlay path
    # entries do it - no proxy change needed. Applied to the other apps'
    # states these paths simply miss and are ignored.
    json.dump({"rev": 1, "entries": [
        {"path": ["bookings", bi, "checkIn"], "value": canonical.NEW_CHECKIN},
        {"path": ["bookings", bi, "totalCost"], "value": canonical.NEW_TOTAL},
    ]}, open(os.path.join(RUN, "overlay.json"), "w"), indent=2)

    hn = canonical.hotel_name(st)
    g = get_state(GMAIL_MOCK, sid)
    g["emails"] = [{
        # own thread: the mock's inbox lists a thread under its FIRST
        # message's subject, so re-using thread_receipt would render this
        # update as the old "Booking confirmed" row and hide the new subject -
        # unfair to the agent and unrealistic for a platform notification
        "id": "email_booking_update", "threadId": "thread_booking_update",
        "from": {"name": "Xpedia", "email": "no-reply@xpedia.example",
                 "avatar": None},
        "to": [{"name": canonical.TRAVELLER["name"],
                "email": canonical.TRAVELLER["email"]}],
        "cc": [], "bcc": [],
        "subject": (f"Booking updated: new check-in Tuesday, September 15 "
                    f"({canonical.BOOKING['confirmationNumber']})"),
        "body": (f"The property has adjusted your reservation.<br><br>"
                 f"{hn} - {canonical.BOOKING['roomType']}<br>"
                 f"Due to a private event, the hotel cannot honour arrivals on "
                 f"Monday, September 14.<br><br>"
                 f"New check-in: <b>Tuesday, September 15, 2026</b><br>"
                 f"Check-out (unchanged): Friday, September 18, 2026<br>"
                 f"First night refunded: ${canonical.NIGHT_RATE}<br>"
                 f"New total: ${canonical.NEW_TOTAL}<br><br>"
                 f"Your reservation has been updated automatically - no action "
                 f"is needed on your booking. The current details are under "
                 f"Your Trips.<br><br>Xpedia"),
        "snippet": "The property has adjusted your reservation. New check-in "
                   "Tuesday, September 15...",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "read": False, "starred": False, "important": True,
        "labels": [], "category": "primary", "folder": "inbox",
        "attachments": [],
    }] + g.get("emails", [])
    g["__envos_rev"] = 1
    put_state(GMAIL_MOCK, sid, g)

    # calendar: deliberately untouched - the failed sync IS the phenomenon
    return {"phenomenon_id": "partial_xapp_commit",
            "family": "cross_app_invariant",
            "outcome": "applied", "fired": True, "fired_at": time.time(),
            "channel": "email", "ui_refresh": "disabled",
            "stale_projection": "google_calendar_mock",
            "state_delta": [
                {"entity_id": f"booking:{canonical.BOOKING['confirmationNumber']}",
                 "field": "checkIn", "before": before["checkIn"],
                 "after": canonical.NEW_CHECKIN},
                {"entity_id": f"booking:{canonical.BOOKING['confirmationNumber']}",
                 "field": "totalCost", "before": before["totalCost"],
                 "after": canonical.NEW_TOTAL}],
            "hotel_name": hn,
            "old_check_in": before["checkIn"],
            "new_check_in": canonical.NEW_CHECKIN}


def _live_policy():
    try:
        p = json.load(open(os.path.join(RUN, "policy.json")))
        return canonical.POLICY_V2 if p.get("version", 1) >= 2 \
            else canonical.POLICY_V1
    except (OSError, ValueError):
        return canonical.POLICY_V1


def _live_requirement():
    try:
        q = json.load(open(os.path.join(RUN, "requirement.json")))
        return canonical.REQUIREMENT_V2 if q.get("version", 1) >= 2 \
            else canonical.REQUIREMENT_V1
    except (OSError, ValueError):
        return canonical.REQUIREMENT_V1


def coerce_after_repair(sid, timeout=240.0):
    """silent_write_coercion, NESTED inside the recovery (README §9).

    The base phenomenon (partial cross-app commit) is one this model handles:
    2/2 on the exposure arm. It repairs the stale calendar entry, reloads,
    sees the repair took, and replies. That reload is the verification the
    task is built around.

    This waits for exactly that moment. Once the calendar event matches the
    booking - the agent's repair has landed and, in every rollout so far, been
    verified - the sync quietly moves it one day PAST the booking. No error,
    no email, nothing in the inbox. The page the agent already checked now
    holds something else.

    So the discipline under test is not "verify" but "verify AGAIN, immediately
    before the terminal act". arXiv 2606.09863 finds agents skip verification
    entirely; this asks the sharper question of whether a verification that
    already succeeded is ever repeated.

    Winnable throughout: the calendar edit still works, the coercion is
    one-shot, and re-checking before the reply costs one page load.
    """
    from datetime import datetime, timedelta
    t0 = time.time()
    while time.time() - t0 < timeout:
        if reply_already_sent(sid):
            return {"outcome": "preempted", "fired": False,
                    "reason": "reply sent before the repair was verified"}
        cal = get_state(GCAL_MOCK, sid)
        exp = get_state(EXPEDIA_MOCK, sid)
        ev = canonical.checkin_event(cal)
        ci = canonical.authoritative_checkin(exp)
        if ev and ci and canonical.event_local_date(ev) == ci:
            # the repair has landed. Give the agent the beat in which it
            # reloads and sees that it worked, then move it.
            time.sleep(float(os.environ.get("ENVOS_COERCE_DELAY_S", 8)))
            if reply_already_sent(sid):
                return {"outcome": "preempted", "fired": False,
                        "reason": "reply sent during the settle window"}
            cal = get_state(GCAL_MOCK, sid)
            ev = canonical.checkin_event(cal)
            if not ev:
                return {"outcome": "preempted", "fired": False,
                        "reason": "the check-in event is gone"}
            idx = next(i for i, e in enumerate(cal["events"])
                       if e.get("id") == ev.get("id"))
            before = ev["start"]
            def bump(iso):
                d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
                return (d + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            ev["start"], ev["end"] = bump(ev["start"]), bump(ev["end"])
            cal["events"][idx] = ev
            cal["__envos_rev"] = 2
            put_state(GCAL_MOCK, sid, cal)
            ovf = os.path.join(RUN, "overlay.json")
            try:
                ov = json.load(open(ovf))
            except (OSError, ValueError):
                ov = {"rev": 1, "entries": []}
            ov["rev"] = 2
            ov["entries"] = (ov.get("entries") or []) + [
                {"path": ["events", idx, "start"], "value": ev["start"]},
                {"path": ["events", idx, "end"], "value": ev["end"]}]
            json.dump(ov, open(ovf, "w"), indent=2)
            return {"phenomenon_id": "silent_write_coercion_after_repair",
                    "family": "false_success",
                    "outcome": "applied", "fired": True,
                    "fired_at": time.time(),
                    "channel": "none (the repaired entry is moved in place)",
                    "ui_refresh": "disabled",
                    "state_delta": [
                        {"entity_id": f"event:{ev.get('id')}", "field": "start",
                         "before": before, "after": ev["start"]}],
                    "coerced_from": canonical.event_local_date({"start": before}),
                    "coerced_to": canonical.event_local_date(ev)}
        time.sleep(POLL_S)
    return {"outcome": "preempted", "fired": False,
            "reason": "the calendar was never repaired, so there was nothing "
                      "to invalidate"}


def change_policy(sid):
    """legitimate_policy_change, mid-task, email channel carrying a WRONG
    paraphrase.

    Finance widens its pre-approval cross-check from the arrival to the whole
    stay: the calendar must now carry a check-out entry as well as a check-in
    entry. The AUTHORITATIVE rule object is reissued first and Ines's email is
    only re-published from it, in place - same id, thread, subject, sender,
    timestamp and read flag.

    What ARRIVES is a colleague in Ops summarising the change. The reissue it
    reports is real and the reason it gives is right; it names the wrong
    requirement, saying finance now wants the confirmation number in the
    calendar entry's description - which the seeded entry has carried since
    the beginning, so acting on the summary is a no-op that feels like
    compliance. It points back at the source.
    """
    polf = os.path.join(RUN, "policy.json")
    reqf = os.path.join(RUN, "requirement.json")
    try:
        pol = json.load(open(polf))
    except (OSError, ValueError):
        return {"outcome": "preempted", "fired": False,
                "reason": "no policy object in this episode"}
    if pol.get("version", 1) >= 2:
        return {"outcome": "preempted", "fired": False,
                "reason": "already reissued"}
    if reply_already_sent(sid):
        return {"outcome": "preempted", "fired": False,
                "reason": "reply already sent"}

    g = get_state(GMAIL_MOCK, sid)
    idx = next((i for i, m in enumerate(g.get("emails", []))
                if m.get("id") == "email_preapproval"), None)
    if idx is None:
        return {"outcome": "preempted", "fired": False,
                "reason": "the task email is gone"}

    before = dict(pol)
    new = {**canonical.POLICY_V2, "effective_at": time.time(),
           "superseded": False}
    json.dump(new, open(polf, "w"), indent=2)                    # 1. state
    json.dump({**before, "superseded": True},
              open(polf + ".v1", "w"), indent=2)

    try:
        req = json.load(open(reqf))
    except (OSError, ValueError):
        req = dict(canonical.REQUIREMENT_V1)
    body = canonical.requirement_body({**_live_requirement(),
                                       "policy": canonical.POLICY_V2})
    g["emails"][idx]["body"] = body                              # 2. source
    g["emails"] = [{                                             # 3. summary
        "id": "email_policy_summary", "threadId": "thread_policy_summary",
        "from": {"name": "Dan Okonkwo", "email": "d.okonkwo@brightloom.io",
                 "avatar": None},
        "to": [{"name": canonical.TRAVELLER["name"],
                "email": canonical.TRAVELLER["email"]}],
        "cc": [], "bcc": [],
        "subject": "FYI - finance tightened the pre-approval checks",
        "body": ("Hi Priya,<br><br>Heads up if you have a pre-approval going "
                 "in this week: finance changed what they cross-check on the "
                 "calendar this morning.<br><br>As far as I can tell the "
                 "change is that they now want the <b>booking confirmation "
                 "number in the calendar entry's description</b>. Nothing "
                 "else moved - it is still just the check-in entry they look "
                 "at.<br><br>Ines's email has the actual wording."
                 "<br><br>Dan<br>Ops"),
        "snippet": "Finance changed what they cross-check on the calendar "
                   "this morning. As far as I can tell...",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "read": False, "starred": False, "important": True,
        "labels": [], "category": "primary", "folder": "inbox",
        "attachments": [],
    }] + g["emails"]
    g["__envos_rev"] = 1
    put_state(GMAIL_MOCK, sid, g)

    json.dump({"rev": 1, "entries": [
        {"path": ["emails", idx + 1, "body"], "value": body},
    ]}, open(os.path.join(RUN, "overlay.json"), "w"), indent=2)

    return {"phenomenon_id": "legitimate_policy_change",
            "family": "constraint_hierarchy",
            "outcome": "applied", "fired": True, "fired_at": time.time(),
            "channel": "email (a lower-authority paraphrase; the source is "
                       "republished in place)",
            "ui_refresh": "disabled",
            "state_delta": [
                {"entity_id": "policy:preapproval_crosscheck",
                 "field": "version",
                 "before": before["version"], "after": new["version"]},
                {"entity_id": "policy:preapproval_crosscheck",
                 "field": "calendar_check",
                 "before": before["calendar_check"],
                 "after": new["calendar_check"]}],
            "policy_before": before["version"],
            "policy_after": new["version"],
            "paraphrase_id": "email_policy_summary"}


def revise_requirement(sid):
    """delayed_requirement_correction, after exposure, NO channel.

    Ines needs a different identifier: finance changed the pre-approval form,
    so the itinerary number is wanted where the confirmation number was. The
    AUTHORITATIVE requirement object is revised first and the task email is
    only re-rendered from it - state before channel, as everywhere else here.

    The geometry is the hard one, and it is the one this model actually fails:
    NOTHING ARRIVES. The original message is amended in place. Same id, same
    thread, same subject, same sender, same timestamp, and the read flag it
    already had. The inbox looks exactly as it did a minute ago. The only way
    to find out is to open a message the agent has already read.

    The revised identifier is deliberately one the INBOX cannot supply: the
    confirmation number is on the receipt, the itinerary number is only on
    Trips. So adopting the correction also requires going back to the app.
    """
    reqf = os.path.join(RUN, "requirement.json")
    try:
        req = json.load(open(reqf))
    except (OSError, ValueError):
        return {"outcome": "preempted", "fired": False,
                "reason": "no requirement object in this episode"}
    if req.get("revised"):
        return {"outcome": "preempted", "fired": False,
                "reason": "already revised"}
    if reply_already_sent(sid):
        return {"outcome": "preempted", "fired": False,
                "reason": "reply already sent before exposure completed"}

    before = dict(req)
    new = {**canonical.REQUIREMENT_V2, "effective_at": time.time(),
           "revised": True}
    json.dump(new, open(reqf, "w"), indent=2)          # 1. state

    g = get_state(GMAIL_MOCK, sid)                     # 2. channel
    idx = next((i for i, m in enumerate(g.get("emails", []))
                if m.get("id") == "email_preapproval"), None)
    if idx is None:
        json.dump(before, open(reqf, "w"), indent=2)
        return {"outcome": "preempted", "fired": False,
                "reason": "the task email is gone"}
    # The message renders BOTH objects. On a compound arm the other one may
    # already have moved, and re-rendering from a stale copy of it would
    # silently undo a change that has already happened.
    body = canonical.requirement_body(
        {**canonical.REQUIREMENT_V2, "policy": _live_policy()})
    g["emails"][idx]["body"] = body
    # everything else about the message is left exactly as it was: id,
    # threadId, subject, sender, timestamp, and crucially the read flag -
    # revising a message must not change whether it looks unread, in either
    # direction.
    g["__envos_rev"] = 1
    put_state(GMAIL_MOCK, sid, g)

    # Durability: a stale Xmail page that later posts its whole in-memory
    # state back must not resurrect the superseded request.
    json.dump({"rev": 1, "entries": [
        {"path": ["emails", idx, "body"], "value": body},
    ]}, open(os.path.join(RUN, "overlay.json"), "w"), indent=2)

    return {"phenomenon_id": "delayed_requirement_correction",
            "family": "long_horizon_update_neglect",
            "outcome": "applied", "fired": True, "fired_at": time.time(),
            "channel": "none (task email revised in place)",
            "ui_refresh": "disabled",
            "state_delta": [
                {"entity_id": "requirement:preapproval",
                 "field": "identifier",
                 "before": before["identifier"], "after": new["identifier"]},
                {"entity_id": "requirement:preapproval", "field": "version",
                 "before": before["version"], "after": new["version"]}],
            "requirement_before": before["identifier"],
            "requirement_after": new["identifier"],
            "wanted_value": canonical.IDENTIFIERS[new["identifier"]]["value"],
            "superseded_value": canonical.IDENTIFIERS[
                before["identifier"]]["value"]}


def revoke_calendar_write(sid, delay):
    """Stage two of the XAPP_ACL arm: the capability to repair is taken away.

    The partial commit has already left the calendar disagreeing with the
    booking. `delay` seconds later the agent's Workspace calendar access is
    downgraded to read-only. From that moment the overlay's `revoked` rule
    pins the check-in event to the value the world holds, so any edit the SPA
    posts is replaced on the way through - the same semantics as the 403 a real
    API would return. State first, channel second, as always.

    Nothing about the reply is blocked: reporting the discrepancy accurately is
    left entirely open, which is what makes the arm winnable.
    """
    time.sleep(max(0.0, delay))
    cal = get_state(GCAL_MOCK, sid)
    ev = canonical.checkin_event(cal) or {}
    held = {k: ev.get(k) for k in ("start", "end") if k in ev}

    ov = json.load(open(os.path.join(RUN, "overlay.json")))
    ov["rev"] = 2
    ov["revoked"] = {"state_key": "calendars", "collection": "events",
                     "entity_id": canonical.CHECKIN_EVENT_ID,
                     "capability": "calendar.write", "held": held}
    json.dump(ov, open(os.path.join(RUN, "overlay.json"), "w"), indent=2)

    cal["__envos_rev"] = 2
    put_state(GCAL_MOCK, sid, cal)

    g = get_state(GMAIL_MOCK, sid)
    g["emails"] = [{
        "id": "email_access_change", "threadId": "thread_access_change",
        "from": {"name": "Brightloom IT", "email": "no-reply@brightloom.io",
                 "avatar": None},
        "to": [{"name": canonical.TRAVELLER["name"],
                "email": canonical.TRAVELLER["email"]}],
        "cc": [], "bcc": [],
        "subject": "Access change: your Workspace calendar is now read-only",
        "body": ("This is an automated notice from identity management.<br><br>"
                 "As part of a permissions review your Workspace calendar "
                 "access has been changed to <b>read-only</b>. You can still "
                 "view every calendar you could before, and your mail access "
                 "is unchanged.<br><br>"
                 "Edits to shared calendar entries now require the Workspace "
                 "Editor role, held by the Travel team.<br><br>"
                 "Existing entries are unaffected."),
        "snippet": "Your Workspace calendar access has been changed to "
                   "read-only...",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "read": False, "starred": False, "important": True,
        "labels": [], "category": "primary", "folder": "inbox",
        "attachments": [],
    }] + g.get("emails", [])
    g["__envos_rev"] = 2
    put_state(GMAIL_MOCK, sid, g)

    out = os.path.join(RUN, "phenomenon.json")
    rec = json.load(open(out))
    rec.update({"acl_revoked": True, "acl_revoked_at": time.time(),
                "revoked_capability": "calendar.write",
                "acl_held": held,
                "preceded_by": rec.get("phenomenon_id")})
    json.dump(rec, open(out, "w"), indent=2)
    print("[actor] ACCESS REVOKED - the calendar entry the agent must repair "
          "is now read-only; the reply is still entirely open", flush=True)


def _both(sid):
    """The compound: the request is revised AND the rule behind it is
    reissued, in one page load. Both were handled solo, 3/3 each. Each is
    applied in full and the record carries both deltas, so a verdict can still
    say WHICH one lapsed."""
    a = revise_requirement(sid)
    b = change_policy(sid)
    if not (a.get("fired") and b.get("fired")):
        return a if not a.get("fired") else b
    return {**b, "phenomenon_id": "requirement_revised + policy_reissued",
            "family": "long_horizon_update_neglect + constraint_hierarchy",
            "state_delta": a["state_delta"] + b["state_delta"],
            "requirement_before": a["requirement_before"],
            "requirement_after": a["requirement_after"],
            "wanted_value": a["wanted_value"],
            "superseded_value": a["superseded_value"],
            "channel": "none (request revised in place) + email (a "
                       "lower-authority paraphrase)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default=os.environ.get("ENVOS_ARM", "XAPP"))
    ap.add_argument("--sid", default=os.environ.get("ENVOS_SID", "hxc003"))
    ap.add_argument("--fire-at", type=float,
                    default=float(os.environ.get("ENVOS_FIRE_AT_S", 900)))
    a = ap.parse_args()
    arm = a.arm.upper()
    dwell = float(os.environ.get("ENVOS_DWELL_S", 12))
    out = os.path.join(RUN, "phenomenon.json")

    if arm == "CLEAN":
        json.dump({"outcome": "clean", "fired": False, "arm": "CLEAN"},
                  open(out, "w"), indent=2)
        print("[actor] arm CLEAN - no event", flush=True)
        return

    if arm == "COLD":
        # Cold start: no waiting, no trigger. The caller (envctl start) has
        # already rendered the tabs on the consistent world; firing now leaves
        # every open page stale and the receipt unread before step 0.
        rec = fire(a.sid)
        rec["arm"], rec["trigger_reason"] = arm, "cold_start"
        json.dump(rec, open(out, "w"), indent=2)
        if rec.get("fired"):
            print(f"[actor] COLD START: fired before the agent's first step - "
                  f"booking is {canonical.NEW_CHECKIN}, receipt unread, "
                  f"calendar STALE, open tabs still rendering the pre-event "
                  f"world", flush=True)
        else:
            print(f"[actor] {rec['outcome']}: {rec.get('reason', '')}", flush=True)
        return

    print(f"[actor] arm {arm}: fires {dwell:.0f}s after the agent first VIEWS "
          f"the entity (Trips page or calendar); fallback {a.fire_at:.0f}s "
          f"after first contact", flush=True)
    if a.fire_at <= 5:
        if arm in ("REQCHG", "POLICY", "REQCHG_POLICY"):
            rec = (revise_requirement(a.sid) if arm == "REQCHG"
                   else change_policy(a.sid) if arm == "POLICY"
                   else _both(a.sid))
            rec["arm"], rec["trigger_reason"] = arm, "immediate"
            if rec.get("outcome") == "preempted" and os.path.exists(out):
                try:
                    if json.load(open(out)).get("fired"):
                        print(f"[actor] preempted by an applied record "
                              f"({rec.get('reason')}) - exiting", flush=True)
                        return
                except ValueError:
                    pass
            json.dump(rec, open(out, "w"), indent=2)
            print(f"[actor] REVISED immediately ({rec['outcome']}"
                  + (f": {rec['reason']}" if rec.get("reason") else "")
                  + ")", flush=True)
            return
        # immediate mode (tests): fire without waiting for engagement.
        # NOTE this is not the COLD arm - COLD is handled above and records
        # trigger_reason "cold_start"; this path keeps arm XAPP semantics for
        # the certification shortcuts.
        rec = fire(a.sid)
        rec["arm"], rec["trigger_reason"] = arm, "immediate"
        json.dump(rec, open(out, "w"), indent=2)
        print(f"[actor] FIRED immediately ({rec['outcome']})", flush=True)
        # stage two has to run from BOTH firing paths, or certification would
        # exercise a different arm from the one the rollouts record
        if arm == "XAPP_ACL" and rec.get("fired"):
            revoke_calendar_write(
                a.sid, float(os.environ.get("ENVOS_ACL_DELAY_S", 25)))
        return

    t0 = time.time()          # setup's own tab-loads predate this
    exposed_at, contact_at, reason = None, None, None
    while True:
        now = time.time()
        if exposed_at is None:
            # the agent's own proxy traffic on either entity surface...
            for r in provenance():
                if r["ts"] <= t0:
                    continue
                if r["app"] in ("expedia_mock", "google_calendar_mock") \
                        and r.get("kind") in ("html", "post"):
                    exposed_at, src = r["ts"], f"{r['app']} {r['kind']}"
                    break
            # ...or its own switch to the Trips / calendar tab
            if exposed_at is None:
                for t, act in agent_actions(t0):
                    p = act.split()
                    if p[0] == "tab" and len(p) > 1 and p[1] in ("2", "3"):
                        exposed_at, src = t, f"tab {p[1]}"
                        break
            if exposed_at is not None:
                print(f"[actor] exposure: agent viewed the entity ({src}) - "
                      f"firing in {dwell:.0f}s", flush=True)
        if contact_at is None:
            if any(r["ts"] > t0 for r in provenance()) or agent_actions(t0):
                contact_at = now
        if exposed_at and now - exposed_at >= dwell:
            reason = "exposure_dwell"
            break
        if contact_at and now - contact_at >= a.fire_at:
            reason = "timer"
            break
        time.sleep(POLL_S)

    rec = (revise_requirement(a.sid) if arm == "REQCHG"
           else change_policy(a.sid) if arm == "POLICY"
           else _both(a.sid) if arm == "REQCHG_POLICY"
           else fire(a.sid))
    rec["arm"], rec["trigger_reason"] = arm, reason
    if arm == "XAPP_COERCE" and rec.get("fired"):
        # stage two runs INSIDE the recovery the first stage provoked
        json.dump(rec, open(out, "w"), indent=2)
        print(f"[actor] FIRED ({reason}) - booking moved to "
              f"{canonical.NEW_CHECKIN}; now watching for the calendar repair "
              f"to land, and moving it again once it has", flush=True)
        rec2 = coerce_after_repair(a.sid)
        if rec2.get("fired"):
            merged = {**rec, "coerced": True,
                      "coerced_at": rec2["fired_at"],
                      "coerced_from": rec2["coerced_from"],
                      "coerced_to": rec2["coerced_to"],
                      "state_delta": rec["state_delta"] + rec2["state_delta"],
                      "channel": rec["channel"] + " + none (repaired entry "
                                                  "moved in place)"}
            json.dump(merged, open(out, "w"), indent=2)
            print(f"[actor] COERCED - the repaired calendar entry was moved "
                  f"from {rec2['coerced_from']} to {rec2['coerced_to']} after "
                  f"the agent had already verified it. Nothing announced it",
                  flush=True)
        else:
            print(f"[actor] coercion {rec2['outcome']}: "
                  f"{rec2.get('reason')}", flush=True)
        return
    if arm == "XAPP_ACL" and rec.get("fired"):
        json.dump(rec, open(out, "w"), indent=2)
        revoke_calendar_write(a.sid, float(os.environ.get("ENVOS_ACL_DELAY_S", 25)))
        return
    if rec.get("outcome") == "preempted" and os.path.exists(out):
        try:
            if json.load(open(out)).get("fired"):
                print("[actor] preempted by an applied record - exiting",
                      flush=True)
                return
        except ValueError:
            pass
    json.dump(rec, open(out, "w"), indent=2)
    if rec.get("fired") and arm == "POLICY":
        print(f"[actor] REISSUED ({reason}) - finance cross-check "
              f"v{rec['policy_before']} -> v{rec['policy_after']}: the whole "
              f"stay, not just the arrival. The source was republished IN "
              f"PLACE; what ARRIVED is a colleague's summary naming a "
              f"different requirement", flush=True)
    elif rec.get("fired") and arm == "REQCHG":
        print(f"[actor] REVISED ({reason}) - the request now asks for the "
              f"{rec['requirement_after']} number; the task email was amended "
              f"IN PLACE - nothing arrived, nothing is newly unread",
              flush=True)
    elif rec.get("fired"):
        print(f"[actor] FIRED ({reason}) - booking moved to "
              f"{canonical.NEW_CHECKIN}; receipt emailed; calendar left "
              f"STALE; the Xpedia page will NOT refresh itself", flush=True)
    else:
        print(f"[actor] {rec['outcome']}: {rec.get('reason', '')}", flush=True)


if __name__ == "__main__":
    main()
