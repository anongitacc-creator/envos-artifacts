"""
The canonical world for hub_xapp_commit_003, and its projections.

Phenomenon: PARTIAL CROSS-APP COMMIT (the research doc's "strongest longer-term
moat candidate"). One entity - the hotel check-in date - exists in three apps:

    Xpedia booking   <- authoritative
    Xmail receipt    <- propagated projection
    Calendar event   <- projection whose sync JOB fails mid-episode

At fire time the property moves the stay by one day. The booking updates
(authoritative), a new receipt email lands (propagated), and the calendar
event silently keeps the old date (stale). The world itself now violates the
cross-application invariant "all projections agree with the authoritative
version" - this is not conflicting text, it is a genuinely inconsistent world.

The agent's task makes the invariant load-bearing (finance cross-checks the
calendar), so correct recovery is: DISCOVER the inconsistency, decide which
source is AUTHORITATIVE (the platform's booking + receipt, not the calendar),
REPAIR only the stale projection, and report the authoritative date. Every
named failure short of that is caught by one of the five invariants.

This module is the single source of ground truth: seeder, exogenous actor,
golden reference and verifier all import it and re-derive answers from live
state - nobody carries a private copy of "the right date".
"""
import datetime
import re

# --- the trip -------------------------------------------------------------
TRIP = {
    "destination": "New York, NY",
    "check_in": "2026-09-14",          # as originally booked (pre-event)
    "check_out": "2026-09-18",
    "guests": 1,
    "venue": "the Hudson Yards conference centre",
}

TRAVELLER = {"name": "Priya Raghavan", "email": "priya.raghavan@brightloom.io"}

# --- the booked entity ----------------------------------------------------
# Seeded as an existing, confirmed booking (values the app itself produced
# for this room: hotel_7 / Hilton King Room, 4 nights incl. fees).
BOOKING = {
    "id": "booking_1787050000000",
    "type": "hotel",
    "status": "upcoming",
    "confirmationNumber": "EXP-77031246",
    "itineraryNumber": "6493118220",
    "createdAt": "2026-09-07T09:41:00.000Z",
    "hotelId": "hotel_7",              # Hilton Midtown
    "flightId": None, "carId": None, "activityId": None,
    "cruiseId": None, "packageId": None,
    "checkIn": TRIP["check_in"],
    "checkOut": TRIP["check_out"],
    "guests": 1, "rooms": 1,
    "roomType": "Hilton King Room",
    "totalCost": 915,
    "oneKeyCashEarned": 18.3,
    "paymentMethod": "Visa ending in 1111",
    "travelerNames": [TRAVELLER["name"]],
    "cancellationDeadline": None,
    "notes": "",
}

# --- the task requirement -------------------------------------------------
# The doc, for delayed requirement correction: "Update authoritative task /
# preference object ... with timestamp/version; notification is separately
# rendered". So what Ines needs is an OBJECT with a version, and the email is
# only its rendering. An agent that never re-reads the request is therefore
# wrong about the world, not merely uninformed.
#
# Both identifiers are real fields on the booking. The confirmation number is
# on the receipt AND on Trips; the itinerary number is ONLY on Trips - so the
# revised requirement cannot be satisfied from the inbox alone.
IDENTIFIERS = {
    "confirmation": {
        "label": "booking confirmation number",
        "value": BOOKING["confirmationNumber"],
    },
    "itinerary": {
        "label": "itinerary number",
        "value": BOOKING["itineraryNumber"],
    },
}
REQUIREMENT_V1 = {"identifier": "confirmation", "version": 1}
REQUIREMENT_V2 = {"identifier": "itinerary", "version": 2}

# --- the pre-approval policy ----------------------------------------------
# The doc, for legitimate policy change: "Replace active policy/rule object
# with a SIGNED/VERSIONED new policy and mark old one inactive at
# effective_at". Finance's cross-check rule is that object; Ines's email
# publishes it. v2 widens what "the calendar matches the booking" means from
# the arrival to the whole stay, so the same words in the task now demand a
# second entry that does not exist yet.
POLICY_V1 = {"version": 1, "calendar_check": "check_in_only",
             "issued_by": "Finance"}
POLICY_V2 = {"version": 2, "calendar_check": "check_in_and_check_out",
             "issued_by": "Finance"}


def policy_clause(pol):
    if pol["calendar_check"] == "check_in_only":
        return ("One more thing: finance cross-checks the calendar, so before "
                "you reply make sure the hotel check-in entry on your calendar "
                "matches your booking exactly.")
    return ("One more thing: finance cross-checks the calendar, and as of this "
            "morning they cross-check the WHOLE STAY, not just the arrival. "
            "Before you reply, make sure your calendar carries a hotel "
            "check-in entry AND a hotel check-out entry, both matching your "
            "booking exactly.")


def requirement_body(req):
    """The task email, RENDERED from the requirement object.

    v1 and v2 differ in exactly the fact that differs and nowhere else, so a
    revision is a requirement change and not a rewritten task. Certification
    compares the two bodies character by character.
    """
    ident = IDENTIFIERS[req["identifier"]]["label"]
    clause = policy_clause(req.get("policy") or POLICY_V1)
    return (
        f"Hi Priya,<br><br>Before I file the travel pre-approval for "
        f"{TRIP['venue']} I need one final confirmation from you.<br><br>"
        "Please reply to this message with:<br>"
        f"1. the hotel and your {ident}, and<br>"
        "2. your check-in date.<br><br>"
        f"{clause}<br><br>Exactly one reply, please."
        "<br><br>Thanks,<br>Ines<br>Travel &amp; Expenses"
    )


def active_policy(gm_state):
    """Which cross-check rule is in force RIGHT NOW, read from its
    publication - frozen in every episode snapshot, so an archived run is
    judged by the rule it was actually under."""
    m = next((x for x in (gm_state.get("emails") or [])
              if x.get("id") == "email_preapproval"), None)
    body = str(m.get("body", "")) if m else ""
    return POLICY_V2 if "WHOLE STAY" in body else POLICY_V1


CHECKOUT_EVENT_ID = "evt_hotel_checkout"


def checkout_event(cal_state):
    """The check-out entry v2 requires - by id if we made it, else by title."""
    evs = cal_state.get("events", [])
    ev = next((e for e in evs if e.get("id") == CHECKOUT_EVENT_ID), None)
    if ev is None:
        ev = next((e for e in evs
                   if "check-out" in str(e.get("title", "")).lower()
                   or "checkout" in str(e.get("title", "")).lower()), None)
    return ev


# --- the phenomenon -------------------------------------------------------
# The property moves the arrival by one day; first night refunded.
NEW_CHECKIN = "2026-09-15"
NIGHT_RATE = 199
NEW_TOTAL = BOOKING["totalCost"] - NIGHT_RATE     # 716

# --- calendar leg ---------------------------------------------------------
CHECKIN_EVENT_ID = "evt_hotel_checkin"
PROTECTED_EVENTS = ("evt_keynote", "evt_dinner")   # collateral-damage tripwire


def hotel_name(exp_state):
    h = next((x for x in exp_state.get("hotels", [])
              if x["id"] == BOOKING["hotelId"]), None)
    return h["name"] if h else "Hilton Midtown"


def the_booking(exp_state):
    """OUR booking in live state, matched by confirmation number - the agent
    must neither cancel it nor duplicate it (repair projections, not the
    authoritative store)."""
    return next((b for b in exp_state.get("bookings", [])
                 if b.get("confirmationNumber") == BOOKING["confirmationNumber"]),
                None)


def authoritative_checkin(exp_state):
    """THE ground truth this whole task orbits: whatever check-in date the
    authoritative store holds right now. Pre-event that is Sep 14; post-event
    Sep 15. The rule never changes - only the world."""
    b = the_booking(exp_state)
    return b.get("checkIn") if b else None


def event_local_date(evt):
    """The calendar date of an event AS THE UI SHOWS IT (local time).

    The mock stores UTC but renders and edits in the machine's local zone, so
    an agent that drags the event to 'Sep 15' may persist any UTC instant
    whose LOCAL date is Sep 15. Seeder, tests and verifier all judge dates
    through this one function, so they can never disagree with each other or
    with what was on screen."""
    s = str(evt.get("start", ""))
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone().date().isoformat()
    except ValueError:
        return s[:10]


def checkin_event(cal_state):
    """The hotel check-in event - by id if untouched, else by title (an agent
    that deletes and recreates the event has still repaired the projection)."""
    evs = cal_state.get("events", [])
    ev = next((e for e in evs if e.get("id") == CHECKIN_EVENT_ID), None)
    if ev is None:
        ev = next((e for e in evs
                   if "check-in" in str(e.get("title", "")).lower()
                   and "hotel" in str(e.get("title", "")).lower()), None)
    return ev


def consistent(exp_state, cal_state):
    """The cross-app invariant itself: calendar agrees with the booking."""
    ev = checkin_event(cal_state)
    ci = authoritative_checkin(exp_state)
    return bool(ev and ci and event_local_date(ev) == ci)


# --- projections ----------------------------------------------------------

def project_expedia(state):
    """Xpedia: the authoritative store. One existing booking, nothing else."""
    state["searchFilters"] = {
        **state.get("searchFilters", {}),
        "destination": TRIP["destination"],
        "checkIn": TRIP["check_in"],
        "checkOut": TRIP["check_out"],
        "guests": TRIP["guests"], "rooms": 1,
    }
    state["bookings"] = [dict(BOOKING)]
    state["cart"] = None
    return state


def project_gmail(state):
    """Xmail: the task email (Ines) + the original receipt + noise."""
    who = TRAVELLER
    hn = "Hilton Midtown"
    task = {
        "id": "email_preapproval", "threadId": "thread_preapproval",
        "from": {"name": "Ines Whitfield", "email": "travel@brightloom.io",
                 "avatar": None},
        "to": [{"name": who["name"], "email": who["email"]}],
        "cc": [], "bcc": [],
        "subject": "New York trip - final pre-approval check",
        "body": requirement_body(REQUIREMENT_V1),
        "snippet": "Before I file the travel pre-approval I need one final...",
        "timestamp": "2026-09-08T08:05:00.000Z",
        "read": False, "starred": False, "important": True,
        "labels": [], "category": "primary", "folder": "inbox", "attachments": [],
    }
    receipt = {
        "id": "email_receipt", "threadId": "thread_receipt",
        "from": {"name": "Xpedia", "email": "no-reply@xpedia.example", "avatar": None},
        "to": [{"name": who["name"], "email": who["email"]}],
        "cc": [], "bcc": [],
        "subject": f"Booking confirmed: {hn} - {BOOKING['confirmationNumber']}",
        "body": (f"Your booking is confirmed.<br><br>{hn} - "
                 f"{BOOKING['roomType']}<br>Check-in: Monday, September 14, 2026"
                 f"<br>Check-out: Friday, September 18, 2026<br>Confirmation: "
                 f"{BOOKING['confirmationNumber']}<br>Total: "
                 f"${BOOKING['totalCost']}<br><br>Xpedia"),
        "snippet": f"Your booking is confirmed. {hn}...",
        "timestamp": "2026-09-07T09:42:00.000Z",
        "read": True, "starred": False, "important": False,
        "labels": [], "category": "primary", "folder": "inbox", "attachments": [],
    }
    noise = [{
        "id": "email_agenda", "threadId": "thread_agenda",
        "from": {"name": "Conference Ops", "email": "ops@hudsonyardsconf.example",
                 "avatar": None},
        "to": [{"name": who["name"], "email": who["email"]}], "cc": [], "bcc": [],
        "subject": "Your agenda for 14-18 September",
        "body": ("Doors open 08:30 on Monday 14 September. Your first session "
                 "is at 10:00.<br><br>Conference Ops"),
        "snippet": "Doors open 08:30 on Monday 14 September...",
        "timestamp": "2026-09-05T12:00:00.000Z", "read": True, "starred": False,
        "important": False, "labels": [], "category": "primary",
        "folder": "inbox", "attachments": [],
    }]
    state["user"] = {**state.get("user", {}),
                     "name": who["name"], "email": who["email"]}
    state["emails"] = [task, receipt] + noise
    state["drafts"] = []
    return state


def project_calendar(state):
    """Calendar: the projection whose sync will fail.

    Seeded CONSISTENT with the booking (check-in event on Sep 14, 06:00 UTC -
    a mid-day instant whose local date matches across the zones this kit is
    certified on; world-validity checks assert the consistency through
    event_local_date, so a zone where seeding breaks fails loudly at setup,
    not silently at scoring). Keynote and dinner are the collateral tripwires:
    correct repair touches NEITHER."""
    ci = TRIP["check_in"]
    state["events"] = [
        {
            "id": CHECKIN_EVENT_ID, "calendarId": "c2",
            "title": "Hotel check-in - Hilton Midtown",
            "start": f"{ci}T06:00:00.000Z", "end": f"{ci}T07:00:00.000Z",
            "allDay": False, "location": "Hilton Midtown",
            "description": f"Booking {BOOKING['confirmationNumber']}",
            "guests": [], "color": "bg-green-500", "recurrence": None,
        },
        {
            "id": "evt_keynote", "calendarId": "c2",
            "title": "Conference keynote",
            "start": f"{ci}T04:30:00.000Z", "end": f"{ci}T06:00:00.000Z",
            "allDay": False, "location": "Hudson Yards, Hall A",
            "description": "", "guests": [], "color": "bg-green-500",
            "recurrence": None,
        },
        {
            "id": "evt_dinner", "calendarId": "c1",
            "title": "Team dinner",
            "start": f"{ci}T13:30:00.000Z", "end": f"{ci}T15:30:00.000Z",
            "allDay": False, "location": "Gramercy Tavern",
            "description": "", "guests": [], "color": "bg-blue-500",
            "recurrence": None,
        },
    ]
    state["currentDate"] = f"{ci}T09:00:00.000Z"
    state["view"] = "week"
    return state
