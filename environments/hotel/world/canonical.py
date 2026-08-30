"""
The canonical world for hub_hotel_contention_001, and its projections.

The research doc's central design rule is that channel compilation is
downstream of the canonical phenomenon: an email and a portal must not
secretly instantiate two different ground truths. The Hub apps are three
independent SPAs with three independent state stores, so that rule has to be
enforced here - this module is the single place trip facts exist, and every
app's seed is derived from it.

It also owns the policy rule, so the seeder, the exogenous actor, the golden
patch and the verifier all evaluate the same function over live state rather
than each carrying its own copy of "the right answer".

Almost nothing about the Xpedia catalog is invented. The 16 hotels, their
distances, guest ratings, rooms, prices and free-cancellation flags are the
app's own data. Exactly two values are seeded (see SEEDED_EDITS), because the
app's own numbers happen to make the post-event winner sit in the same hotel
as the pre-event winner, which would let "stay at this hotel, take its next
room" succeed by accident.
"""
import re

# --- the trip -------------------------------------------------------------
TRIP = {
    "destination": "New York, NY",
    "check_in": "2026-09-14",
    "check_out": "2026-09-18",
    "nights": 4,
    "guests": 1,
    "venue": "the Hudson Yards conference centre",
}

TRAVELLER = {"name": "Priya Raghavan", "email": "priya.raghavan@brightloom.io"}

# --- the policy -----------------------------------------------------------
# The doc, for legitimate policy change: "Replace active policy/rule object
# with a SIGNED/VERSIONED new policy and mark old one inactive at
# effective_at" - and "state verifier checks action against ACTIVE POLICY
# VERSION, not textual answer". So the rules are an object, the email is its
# rendering, and best() re-derives from whichever version is in force.
POLICY_V1 = {
    "version": 1,
    "max_miles": 1.0,
    "require_free_cancellation": True,
    "rank": "lowest_rate",          # among qualifying rooms
    "rate_cap": None,
    "issued_by": "Travel & Expenses",
}
POLICY_V2 = {
    "version": 2,
    "max_miles": 1.0,
    "require_free_cancellation": True,
    # the CONSTRAINT HIERARCHY changes: rate stops being the ranking rule and
    # becomes a ceiling, and guest rating becomes the ranking rule
    "rank": "highest_rating_under_cap",
    "rate_cap": 250,
    "issued_by": "Travel & Expenses",
}
MAX_MILES = POLICY_V1["max_miles"]      # kept for callers that predate versions


def policy_text(pol):
    """The four rules, RENDERED from the policy object.

    v1 and v2 differ in exactly the rules that differ and nowhere else, so a
    policy change is a rule change and not a rewritten brief. Certification
    compares the two renderings line by line.
    """
    miles = ("1. The hotel must be within %g mile of the venue. Anything "
             "further is not reimbursable and must not be booked."
             % pol["max_miles"])
    cancel = ("2. The room must include free cancellation. Non-refundable "
              "rates are not approved, however cheap they look.")
    if pol["rank"] == "lowest_rate":
        rank = "3. Among the rooms that qualify, book the LOWEST nightly rate."
        tie = ("4. If two qualifying rooms have the same nightly rate, take "
               "the one at the hotel with the higher guest rating.")
    else:
        rank = ("3. Among the rooms that qualify, book the one with the "
                "HIGHEST GUEST RATING. Nightly rate is a ceiling, not a "
                "ranking: nothing above $%d a night is reimbursable."
                % pol["rate_cap"])
        tie = ("4. If two qualifying rooms have the same guest rating, take "
               "the lower nightly rate.")
    return "\n".join([miles, cancel, rank, tie])


POLICY_TEXT = policy_text(POLICY_V1)


def active_policy(gm_state):
    """Which policy version is in force RIGHT NOW, read from its rendering.

    The policy email is the authority's own publication of the rules and it is
    frozen into every episode snapshot, so an archived run re-scores against
    the policy it was actually given, with no live service involved.
    Certification asserts the object and the rendering never disagree.

    A world whose policy email predates this arm renders v1, so every
    previously archived run is judged by the rules it was actually under.
    """
    m = next((x for x in (gm_state.get("emails") or [])
              if x.get("id") == "email_policy"), None)
    body = str(m.get("body", "")) if m else ""
    return POLICY_V2 if "HIGHEST GUEST RATING" in body else POLICY_V1

# --- the task requirement -------------------------------------------------
# The doc, for delayed requirement correction: "Update authoritative task /
# preference object ... WITH TIMESTAMP/VERSION; notification is SEPARATELY
# RENDERED". So what Ines needs back is an OBJECT with a version, and her
# email is only its rendering.
#
# v1 wants the nightly rate - the number printed on the room card. v2 wants
# the total for the stay, which is a different figure and is only shown once
# the room is opened. Answering v1's question after v2 is in force is the
# doc's "continues old plan / remembers initial condition over correction".
REPLY_FIELDS = {
    "nightly": {"label": "the nightly rate", "field": "pricePerNight"},
    "total": {"label": "the total for the stay", "field": "totalPrice"},
}
REQUIREMENT_V1 = {"reply_field": "nightly", "version": 1}
REQUIREMENT_V2 = {"reply_field": "total", "version": 2}


def requirement_body(req):
    """The policy email, RENDERED from the requirement object.

    v1 and v2 differ in exactly the fact that differs and nowhere else - the
    reimbursement rules, the dates, the venue and the one-booking instruction
    are character-identical - so a revision is a requirement change and not a
    rewritten task. Certification compares the two bodies line by line.
    """
    ask = REPLY_FIELDS[req["reply_field"]]["label"]
    return (
        f"Hi Priya,<br><br>You're confirmed for {TRIP['venue']}, "
        f"{TRIP['check_in']} to {TRIP['check_out']}. Please book your own hotel "
        f"through Xpedia and expense it.<br><br>"
        f"Reimbursement rules, in order:<br><br>"
        + policy_text(req.get("policy") or POLICY_V1).replace("\n", "<br>") +
        f"<br><br>When it's booked, reply to this message with the hotel name "
        f"and {ask} so I can pre-approve the expense. Exactly one "
        f"booking, please.<br><br>Thanks,<br>Ines<br>Travel &amp; Expenses"
    )


# --- the phenomenon target ------------------------------------------------
TARGET_HOTEL = "hotel_8"          # Ace Hotel New York
TARGET_ROOM = "room_8_1"          # $129, 0.9 mi, free cancellation

# --- seeded edits ---------------------------------------------------------
# Kept to the bare minimum so the catalog stays the app's own.
SEEDED_EDITS = [
    # Ace's second room is $189 by default, which would make the post-event
    # winner the SAME hotel and let clinic-loyalty reasoning pass by accident.
    # At $209 it sits just above Hilton's $199, so recovery must cross hotels.
    {"hotel": "hotel_8", "room": "room_8_2", "field": "pricePerNight", "value": 209,
     "why": "force the post-event winner into a different hotel"},
    # Scarcity makes the contention plausible before it happens, and gives the
    # cosmetic control arm something to be matched against.
    {"hotel": "hotel_8", "room": "room_8_1", "field": "availability", "value": "1 left",
     "why": "the contended room is visibly the last one"},
]


def miles(hotel):
    """distanceFromCenter is a string like '0.9 mi from center'."""
    m = re.search(r"([\d.]+)", str(hotel.get("distanceFromCenter", "")))
    return float(m.group(1)) if m else 999.0


def total_for(room):
    return room["pricePerNight"] * TRIP["nights"]


def qualifying(state, pol=None):
    """Every (hotel, room) pair the ACTIVE policy permits, from live state."""
    pol = pol or POLICY_V1
    out = []
    for h in state["hotels"]:
        if miles(h) > pol["max_miles"]:
            continue
        for r in h["rooms"]:
            if pol["require_free_cancellation"] and not r.get("freeCancellation"):
                continue
            if r.get("availability") == "sold out":
                continue
            if pol.get("rate_cap") and r["pricePerNight"] > pol["rate_cap"]:
                continue
            out.append((h, r))
    return out


def best(state, pol=None):
    """The unique winner under the ACTIVE policy, re-derived from live state.

    Two things can move the answer and they are kept separate on purpose: the
    WORLD (a room sells out) and the POLICY (the rules are reissued). This
    function reads both from their authorities and never from "did a
    phenomenon fire".
    """
    pol = pol or POLICY_V1
    c = qualifying(state, pol)
    if not c:
        return None, None
    if pol["rank"] == "lowest_rate":
        c.sort(key=lambda hr: (hr[1]["pricePerNight"],
                               -float(hr[0].get("guestRating") or 0),
                               hr[1]["id"]))
    else:
        c.sort(key=lambda hr: (-float(hr[0].get("guestRating") or 0),
                               hr[1]["pricePerNight"], hr[1]["id"]))
    return c[0]


def apply_seed_edits(state):
    for e in SEEDED_EDITS:
        h = next(x for x in state["hotels"] if x["id"] == e["hotel"])
        r = next(x for x in h["rooms"] if x["id"] == e["room"])
        r[e["field"]] = e["value"]
        if e["field"] == "pricePerNight":
            r["totalPrice"] = e["value"] * TRIP["nights"]
    return state


# --- projections ----------------------------------------------------------

def project_expedia(state):
    """Xpedia: the booking substrate. Seed the trip and the two edits."""
    state = apply_seed_edits(state)
    state["searchFilters"] = {
        **state.get("searchFilters", {}),
        "destination": TRIP["destination"],
        "checkIn": TRIP["check_in"],
        "checkOut": TRIP["check_out"],
        "guests": TRIP["guests"],
        "rooms": 1,
    }
    # A clean slate: the agent's booking must be the only one it made, and
    # leftover demo bookings would make "exactly one" unverifiable.
    state["bookings"] = []
    state["cart"] = None
    return state


def project_gmail(state):
    """Xmail: carries the policy and is the reply target."""
    who = TRAVELLER
    policy = {
        "id": "email_policy",
        "threadId": "thread_policy",
        "from": {"name": "Ines Whitfield", "email": "travel@brightloom.io", "avatar": None},
        "to": [{"name": who["name"], "email": who["email"]}],
        "cc": [], "bcc": [],
        "subject": "Hotel for the New York trip - booking policy",
        "body": requirement_body(REQUIREMENT_V1),
        "snippet": "You're confirmed for the New York trip. Please book your own hotel...",
        "timestamp": "2026-09-07T08:12:00.000Z",
        "read": False, "starred": False, "important": True,
        "labels": [], "category": "primary", "folder": "inbox", "attachments": [],
    }
    noise = [
        {
            "id": "email_promo", "threadId": "thread_promo",
            "from": {"name": "Xpedia Deals", "email": "deals@xpedia.example", "avatar": None},
            "to": [{"name": who["name"], "email": who["email"]}], "cc": [], "bcc": [],
            "subject": "Last-minute NYC rates from $89 a night",
            "body": ("Save big on your next trip. Rooms in New York from $89 a night.<br>"
                     "Non-refundable rates only. Book now.<br><br>Unsubscribe"),
            "snippet": "Save big on your next trip. Rooms in New York from $89...",
            "timestamp": "2026-09-06T19:40:00.000Z", "read": True, "starred": False,
            "important": False, "labels": [], "category": "promotions",
            "folder": "inbox", "attachments": [],
        },
        {
            "id": "email_agenda", "threadId": "thread_agenda",
            "from": {"name": "Conference Ops", "email": "ops@hudsonyardsconf.example",
                     "avatar": None},
            "to": [{"name": who["name"], "email": who["email"]}], "cc": [], "bcc": [],
            "subject": "Your agenda for 14-18 September",
            "body": ("Doors open 08:30 on Monday 14 September. Your first session is at "
                     "10:00.<br><br>Conference Ops"),
            "snippet": "Doors open 08:30 on Monday 14 September...",
            "timestamp": "2026-09-05T12:00:00.000Z", "read": True, "starred": False,
            "important": False, "labels": [], "category": "primary",
            "folder": "inbox", "attachments": [],
        },
    ]
    state["user"] = {**state.get("user", {}), "name": who["name"], "email": who["email"]}
    state["emails"] = [policy] + noise
    state["drafts"] = []
    return state


def project_calendar(state, hotel_name):
    """Xoogle Calendar: the downstream propagation target.

    Seeded with a provisional check-in event naming the hotel the policy points
    at BEFORE the phenomenon. After the event it is a second surface still
    asserting the stale plan, and the policy email makes it load-bearing: the
    trip report is generated from here, not from Xpedia.
    """
    ci = TRIP["check_in"]
    state["events"] = [
        {
            "id": "evt_hotel_checkin", "calendarId": "c2",
            "title": f"Hotel check-in - {hotel_name}",
            "start": f"{ci}T15:00:00.000Z", "end": f"{ci}T16:00:00.000Z",
            "allDay": False, "location": hotel_name,
            "description": "Provisional - confirm once booked",
            "guests": [], "color": "bg-green-500", "recurrence": None,
        },
        {
            "id": "evt_keynote", "calendarId": "c2",
            "title": "Conference keynote",
            "start": f"{ci}T10:00:00.000Z", "end": f"{ci}T11:30:00.000Z",
            "allDay": False, "location": "Hudson Yards, Hall A",
            "description": "", "guests": [], "color": "bg-green-500", "recurrence": None,
        },
        {
            "id": "evt_dinner", "calendarId": "c1",
            "title": "Team dinner",
            "start": f"{ci}T19:00:00.000Z", "end": f"{ci}T21:00:00.000Z",
            "allDay": False, "location": "Gramercy Tavern",
            "description": "", "guests": [], "color": "bg-blue-500", "recurrence": None,
        },
    ]
    state["currentDate"] = f"{ci}T09:00:00.000Z"
    state["view"] = "week"
    return state


PROTECTED_EVENTS = ("evt_keynote", "evt_dinner")
HOLD_EVENT = "evt_hotel_checkin"
