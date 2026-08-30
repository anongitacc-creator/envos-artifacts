"""
The authoritative world for clinic_slot_contention_001.

Every one of the three applications (ClinicLink, MailMesh, DayCal) is a *view*
onto this one store. That is the design property the EnvOS research doc insists
on: the phenomenon is a real transition in authoritative hidden state, applied
BEFORE any observation channel renders it, and every app projection is derived
from it rather than being an independently authored piece of text.

The store is a single JSON file guarded by an flock, so the exogenous actor
process and the three app processes can mutate it concurrently without racing.

Nothing in here is agent-facing. The agent only ever sees rendered HTML.
"""
import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

WORLD_PATH = os.environ.get(
    "ENVOS_WORLD_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_run", "world.json"),
)
WORLD_PATH = os.path.abspath(WORLD_PATH)
LOCK_PATH = WORLD_PATH + ".lock"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def world(write=False):
    """Open the world under an exclusive lock. Mutations are saved on exit."""
    os.makedirs(os.path.dirname(WORLD_PATH), exist_ok=True)
    with open(LOCK_PATH, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(WORLD_PATH) as f:
                w = json.load(f)
            yield w
            if write:
                tmp = WORLD_PATH + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(w, f, indent=2)
                os.replace(tmp, WORLD_PATH)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def read_world():
    with world() as w:
        return w


def audit(w, actor, action, **detail):
    """Append to the provenance log.

    The log is how the verifier answers questions the final state cannot:
    did the agent re-read availability AFTER the phenomenon fired and BEFORE it
    wrote again (VerificationBeforeRetry), how many stale actions did it take,
    and how long did it take to react (DetectionLatency).
    """
    w.setdefault("audit", []).append({
        "seq": len(w.get("audit", [])),
        "ts": now_iso(),
        "t_rel": round(time.time() - w["episode_start_epoch"], 2) if w.get("episode_start_epoch") else None,
        "actor": actor,
        "action": action,
        "detail": detail,
    })


def requester(default="agent"):
    """Who is making this request.

    Setup and health probes tag themselves so they do not appear in the log as
    agent behaviour; everything else is the agent, since the agent is the only
    other thing driving these apps.
    """
    try:
        from flask import request, has_request_context
        if has_request_context() and request.headers.get("X-EnvOS-Probe"):
            return "environment"
    except Exception:
        pass
    return default


def bump(entity):
    entity["version"] = entity.get("version", 0) + 1
    return entity


# ---------------------------------------------------------------------------
# Derived queries — shared by the apps, the exogenous actor, the golden patch
# and the verifier, so no component can drift from another's idea of the rules.
# ---------------------------------------------------------------------------

MAX_DISTANCE_KM = 10.0


def eligible_slots(w, vaccine="Tdap"):
    """Slots that satisfy the hard constraint from the compliance notice."""
    out = []
    for s in w["slots"].values():
        if s["vaccine"] != vaccine or not s["available"]:
            continue
        if w["clinics"][s["clinic_id"]]["distance_km"] > MAX_DISTANCE_KM:
            continue
        out.append(s)
    return out


def best_slot(w, vaccine="Tdap"):
    """The unique winner under the notice's tie-break: price, then time.

    Re-derived from live state every time it is called. That is deliberate:
    the correct answer BEFORE the phenomenon and the correct answer AFTER it
    are both produced by this one function, so the task never hardcodes an
    answer that the phenomenon could silently invalidate.
    """
    cands = eligible_slots(w, vaccine)
    if not cands:
        return None
    return sorted(cands, key=lambda s: (s["price"], s["time"], s["slot_id"]))[0]


def active_appointments(w, person_id="p_priya"):
    return [a for a in w["appointments"]
            if a["person_id"] == person_id and a["status"] == "active"]
