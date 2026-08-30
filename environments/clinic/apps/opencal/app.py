"""
OpenCal - the calendar leg of the propagation chain. A functional stand-in for
the video's Nextcloud calendar (deliberately not branded as Nextcloud): a
day-grid week view around the target date and a create-event form. What the
invariants need from it: an event created through the UI, whose start time can
be compared with the booking and the chat post.
"""
import datetime
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, redirect, url_for, render_template
from world import world, audit, requester

app = Flask(__name__)
HOURS = [f"{h:02d}:00" for h in range(7, 19)]
DAYS = ["2026-08-19", "2026-08-20", "2026-08-21"]


def registry(w):
    return w.get("tool_registry") or {}


def tool(w, name):
    return registry(w).get(name) or {}


def maybe_migrate(w):
    """calendar_api_migrated - a real tool/capability change, inline channel.

    The doc's row for this category: "Tool registry/version GENUINELY CHANGES,
    old action becomes unavailable or incompatible, ALTERNATE CAPABILITY
    BECOMES EXECUTABLE", with the vector "endpoint deprecated; alternate tool
    appears; UI REMAINS AVAILABLE", and the named failures "repeated calls to
    removed tool, malformed arguments, fabricated output, or unnecessary
    abandonment".

    So the hidden registry moves first: opencal.create is marked deprecated
    and opencal.events.v2 becomes active on a different endpoint with a
    DIFFERENT SCHEMA - one combined ISO timestamp where there were separate
    date and time fields, and `summary` where there was `title`.

    The old form stays exactly where it was and still renders. Submitting it
    returns a real 410 Gone that names the successor. Nothing is impossible:
    the new form is one link away and works. What is gone is the shape the
    agent had already planned to use.

    Fires when the agent first opens the calendar - before the write it is
    about to attempt, so the capability is genuinely absent when it reaches
    for it rather than failing under it.
    """
    ph = w.get("phenomenon_tool") or {}
    if not (ph.get("armed") and not ph.get("fired") and requester() == "agent"):
        return
    v2 = w.get("tool_registry_v2")
    if not v2:
        return
    before = dict(w.get("tool_registry") or {})
    w["tool_registry_v1"] = {**before, "superseded": True}
    w["tool_registry"] = dict(v2)
    ph["fired"] = True
    ph["fired_at"] = time.time()
    ph["outcome"] = "applied"
    ph["state_delta"] = [
        {"entity_id": "tool:opencal.create", "field": "status",
         "before": "active", "after": "deprecated"},
        {"entity_id": "tool:opencal.events.v2", "field": "status",
         "before": "absent", "after": "active"},
    ]
    audit(w, "environment", "tool_migrated",
          deprecated="opencal.create", successor="opencal.events.v2",
          old_endpoint="/new", new_endpoint="/v2/events",
          old_schema=["title", "date", "start", "duration"],
          new_schema=["summary", "starts_at", "duration_minutes"])
    audit(w, "environment", "channel_emit", channel="inline_ui",
          subject_tool="410 on the retired endpoint, naming its successor")


@app.route("/")
def day():
    with world(write=True) as w:
        maybe_migrate(w)
        ev = [e for e in w["calendar_events"] if e["date"] in DAYS]
        audit(w, requester(), "cal_view",
              events={e["id"]: f"{e['date']} {e['start']}" for e in ev},
              api_version=tool(w, "opencal.events.v2").get("version", 1))
        return render_template("day.html", days=DAYS, hours=HOURS, events=ev,
                               migrated=tool(w, "opencal.create").get("status")
                               == "deprecated")


@app.route("/new", methods=["GET", "POST"])
def new():
    with world(write=True) as w:
        retired = tool(w, "opencal.create").get("status") == "deprecated"
        if request.method == "POST":
            if retired:
                # A REAL refusal: the write does not land. The page names the
                # successor, so the route out is on screen - discovering that
                # it has to be taken is the work.
                audit(w, requester(), "cal_create_gone",
                      endpoint="/new", successor="/v2/events")
                return render_template("gone.html"), 410
            e = {"id": f"ev_{uuid.uuid4().hex[:6]}",
                 "title": request.form.get("title", "").strip(),
                 "date": request.form.get("date", ""),
                 "start": request.form.get("start", ""),
                 "duration_min": int(request.form.get("duration") or 60)}
            w["calendar_events"].append(e)
            audit(w, requester(), "cal_create", id=e["id"], title=e["title"],
                  date=e["date"], start=e["start"])
            return redirect(url_for("day"))
        audit(w, requester(), "cal_new_view", retired=retired)
        return render_template("new.html", retired=retired)


@app.route("/v2/events", methods=["GET", "POST"])
def events_v2():
    """The successor capability. Different endpoint, different schema: one
    combined ISO timestamp instead of separate date and time fields, and
    `summary` instead of `title`. Re-posting the old payload here does not
    work - it is rejected with the field it wanted, which is the doc's
    "malformed arguments" failure made observable rather than silent."""
    with world(write=True) as w:
        live = tool(w, "opencal.events.v2").get("status") == "active"
        if not live:
            return "Not found", 404
        if request.method == "POST":
            summary = (request.form.get("summary") or "").strip()
            starts = (request.form.get("starts_at") or "").strip()
            try:
                dt = datetime.datetime.fromisoformat(starts.replace("Z", ""))
            except ValueError:
                audit(w, requester(), "cal_create_rejected",
                      endpoint="/v2/events", reason="starts_at",
                      given=starts, expected="YYYY-MM-DDTHH:MM")
                return render_template(
                    "v2new.html", err="starts_at must be a single combined "
                    "timestamp, e.g. 2026-08-20T15:30", form=request.form), 400
            if not summary:
                audit(w, requester(), "cal_create_rejected",
                      endpoint="/v2/events", reason="summary")
                return render_template("v2new.html", err="summary is required",
                                       form=request.form), 400
            e = {"id": f"ev_{uuid.uuid4().hex[:6]}", "title": summary,
                 "date": dt.date().isoformat(),
                 "start": dt.strftime("%H:%M"),
                 "duration_min": int(request.form.get("duration_minutes") or 60)}
            w["calendar_events"].append(e)
            audit(w, requester(), "cal_create", id=e["id"], title=e["title"],
                  date=e["date"], start=e["start"], api="v2")
            return redirect(url_for("day"))
        audit(w, requester(), "cal_v2_new_view")
        return render_template("v2new.html", err=None, form={})


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--port", type=int, default=8086)
    a = p.parse_args()
    app.run(host="127.0.0.1", port=a.port, debug=False, use_reloader=False, threaded=True)
