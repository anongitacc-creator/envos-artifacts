#!/usr/bin/env python3
"""
The re-grounding proxy: what makes a real exogenous phenomenon possible on
stock CUA-Gym-Hub mocks, without editing a single upstream file.

Three problems have to be solved, all of them consequences of how the Hub
mocks manage state. They are not bugs - the mocks were built for tasks whose
state is fixed at t=0 - but they make an exogenous mid-episode change invisible.

  1. The server is read once, ever.
     Every Hub app boots with
         isRefresh = localStorage.getItem(initialKey(sid)) !== null
     and takes the localStorage branch on every load after the first. A change
     POSTed to /state mid-episode is never read. Measured directly: flipping a
     room to "sold out" server-side and reloading left the page identical.
     -> Fixed by injecting a blocking head script that pulls /state with a
        synchronous XHR and writes it into the app's own state key before the
        bundle executes. Verified: the page then renders "Sold out" and drops
        the Reserve button.

  2. The browser is a client-side router.
     Clicking inside the SPA never issues a document request, so an injected
     load-time script alone would only fire if the agent happened to do a full
     reload. -> The injected script also polls /state for a dedicated revision
     marker and reloads once when it increases. This is precisely the
     "portal availability refresh" channel: the page updates because the world
     changed, not because anything narrated it.

  3. The SPA clobbers the world.
     Every action posts the app's whole in-memory state back with
     action=set_current, which would overwrite the exogenous change and revert
     the revision marker - the phenomenon would silently undo itself.
     -> The proxy keeps an overlay of exogenously-owned paths and re-applies it
        to any state the browser posts, and to any state the server returns.
        Exogenous truth wins over anything the SPA remembers.

The proxy also writes a provenance log of every request, which is where the
verifier gets what final state cannot tell it: whether the agent re-read
availability after the event and before it wrote again.
"""
import argparse
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REV_KEY = "__envos_rev"

# Injected before the app bundle. Two jobs: re-ground this load from the
# server, and reload once if the world changes underneath an open page.
INJECT = """<script>
(function () {
  var STATE_KEY_HINT = %(hint)s, SID_KEYS = %(sidkeys)s;
  function sid() {
    var q = new URLSearchParams(location.search).get('sid');
    if (q) return q;
    for (var i = 0; i < SID_KEYS.length; i++) {
      var v = sessionStorage.getItem(SID_KEYS[i]);
      if (v) return v;
    }
    return null;
  }
  function serverState(s) {
    var x = new XMLHttpRequest();
    x.open('GET', '/state?sid=' + encodeURIComponent(s), false);
    x.send();
    if (x.status !== 200) return null;
    var d = JSON.parse(x.responseText);
    if (d && d.stored_state !== undefined) d = d.stored_state;
    return (d && typeof d === 'object' && !d.error) ? d : null;
  }
  function stateKeyFor(s) {
    // The app's own current-state key. Its initial-state key must be left
    // alone: it is the baseline /go diffs against.
    var keys = Object.keys(localStorage).filter(function (k) {
      return k.indexOf(s) !== -1 && k.toLowerCase().indexOf('initial') === -1;
    });
    if (keys.length) return keys[0];
    return STATE_KEY_HINT ? STATE_KEY_HINT + '_' + s : null;
  }
  var s = sid();
  if (!s) return;
  try {
    var st = serverState(s);
    if (st) {
      var k = stateKeyFor(s);
      if (k) localStorage.setItem(k, JSON.stringify(st));
      window.__envosRev = st['%(rev)s'] || 0;
    }
  } catch (e) { }
  // Watch for the world moving underneath an already-open page. A poll
  // interval of 0 disables this entirely: the page then re-grounds ONLY on a
  // full document load, and client-side navigation keeps showing the state
  // from load time - the stale-form configuration under test.
  if (%(poll)d <= 0) return;
  setInterval(function () {
    try {
      var cur = serverState(s);
      if (!cur) return;
      var rev = cur['%(rev)s'] || 0;
      if (rev > (window.__envosRev || 0)) {
        window.__envosRev = rev;
        var k = stateKeyFor(s);
        if (k) localStorage.setItem(k, JSON.stringify(cur));
        location.reload();
      }
    } catch (e) { }
  }, %(poll)d);
})();
</script>"""


def get_path(obj, path):
    for p in path:
        obj = obj[p]
    return obj


def set_path(obj, path, value):
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = value


class Proxy:
    def __init__(self, upstream, overlay_path, log_path, hint, sid_keys, poll_ms):
        self.upstream = upstream.rstrip("/")
        self.overlay_path = overlay_path
        self.log_path = log_path
        self.lock = threading.Lock()
        self.inject = (INJECT % {
            "hint": json.dumps(hint), "sidkeys": json.dumps(sid_keys),
            "rev": REV_KEY, "poll": poll_ms}).encode()

    # -- overlay ---------------------------------------------------------
    def overlay(self):
        try:
            with open(self.overlay_path) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {"rev": 0, "entries": []}

    def reject_contended_booking(self, state):
        """A booking of a room that is already gone must not stand.

        Xpedia's checkout does not re-check availability, so an agent that
        clicked Reserve in the moment before the page re-grounded could
        otherwise complete a booking for a room another traveller already
        holds. A real booking service refuses that write. The proxy refuses it
        here, on the way through, and records the refusal - the same semantics
        as the 409 a booking API would return.
        """
        ov = self.overlay()
        c = ov.get("contended")
        if not c or not ov.get("rev"):
            return state
        keep, dropped = [], []
        for b in state.get("bookings", []) or []:
            if b.get("hotelId") == c["hotel_id"] and b.get("roomType") == c["room_name"]:
                dropped.append(b)
            else:
                keep.append(b)
        if dropped:
            state["bookings"] = keep
            for b in dropped:
                self.log(kind="booking_rejected_room_taken",
                         hotel_id=c["hotel_id"], room_name=c["room_name"],
                         confirmation=b.get("confirmationNumber"))
        return state

    def coerce_booking(self, state):
        """The write is ACCEPTED and quietly altered on the way through.

        LITERATURE-DERIVED. OSWorld 2.0 reports that over 86% of long-horizon
        computer-use failures are the agent believing it succeeded; arXiv
        2606.09863 measures false success at 45-48% of failures where state
        cannot be independently verified against 3% where it can.

        Every write in this benchmark so far has landed correctly, been
        refused (the rejection above), or been voided afterwards. In each case
        the agent only has to check that its booking EXISTS. Here the booking
        exists, the confirmation page shows the room that was chosen - the SPA
        renders its own in-memory state - and the store holds a different
        room. Only a reload of Trips says so.

        A real booking service does exactly this when the last of a room type
        goes between reserve and pay: it substitutes and tells you in the
        itinerary, not in the flow.
        """
        ov = self.overlay()
        c = ov.get("coerce_room")
        if not c:
            return state
        for b in state.get("bookings", []) or []:
            if b.get("hotelId") == c["hotel_id"] \
                    and b.get("roomType") == c["from_room"]:
                b["roomType"] = c["to_room"]
                b["totalCost"] = c["to_total"]
                b["notes"] = c.get("note", "")
                self.log(kind="booking_coerced", hotel_id=c["hotel_id"],
                         requested=c["from_room"], stored=c["to_room"],
                         confirmation=b.get("confirmationNumber"))
        return state

    def apply_overlay(self, state):
        """Exogenous truth wins over whatever the SPA remembers."""
        if not isinstance(state, dict):
            return state
        ov = self.overlay()
        for e in ov.get("entries", []):
            try:
                set_path(state, e["path"], e["value"])
            except (KeyError, IndexError, TypeError):
                pass
        if ov.get("rev"):
            state[REV_KEY] = ov["rev"]
        return state

    # -- provenance ------------------------------------------------------
    def log(self, **rec):
        rec["ts"] = time.time()
        with self.lock:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(rec) + "\n")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    proxy = None

    def _forward(self, body=None):
        p = self.proxy
        url = p.upstream + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "accept-encoding", "content-length",
                                 "connection"):
                req.add_header(k, v)
        try:
            r = urllib.request.urlopen(req, timeout=30)
            data, status, hdrs = r.read(), r.status, dict(r.headers)
        except urllib.error.HTTPError as e:
            data, status, hdrs = e.read(), e.code, dict(e.headers)
        except Exception as e:
            self.send_error(502, str(e))
            return
        return data, status, hdrs

    def _respond(self, data, status, hdrs):
        self.send_response(status)
        for k, v in hdrs.items():
            if k.lower() in ("content-length", "transfer-encoding",
                             "content-encoding", "connection"):
                continue
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = self.proxy
        out = self._forward()
        if out is None:
            return
        data, status, hdrs = out
        path = self.path.split("?")[0]

        if path == "/state":
            # Exogenous truth wins on the way out too, so the injected script
            # can never be handed a state the SPA has since clobbered.
            try:
                d = json.loads(data)
                wrapped = isinstance(d, dict) and "stored_state" in d
                st = d["stored_state"] if wrapped else d
                if isinstance(st, dict):
                    st = p.apply_overlay(st)
                    if wrapped:
                        d["stored_state"] = st
                        d["has_custom_state"] = True
                    else:
                        d = st
                    data = json.dumps(d).encode()
            except ValueError:
                pass
        elif "text/html" in hdrs.get("Content-Type", ""):
            html = data.decode("utf-8", "replace")
            html = re.sub(r"<head([^>]*)>", lambda m: m.group(0) + p.inject.decode(),
                          html, count=1)
            data = html.encode()

        # Document and state reads are the provenance that matters; asset
        # requests are noise.
        if "text/html" in hdrs.get("Content-Type", "") or path == "/state":
            p.log(kind="html" if path != "/state" else "state",
                  method="GET", path=self.path, status=status)
        self._respond(data, status, hdrs)

    def do_POST(self):
        p = self.proxy
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n) if n else b""

        if self.path.split("?")[0] == "/post":
            try:
                payload = json.loads(body)
                st = payload.get("state")
                if isinstance(st, dict):
                    st = p.coerce_booking(
                        p.reject_contended_booking(p.apply_overlay(st)))
                    payload["state"] = st
                    body = json.dumps(payload).encode()
                    # What the agent is currently looking at, and what it has
                    # booked, are both visible here. This is the provenance the
                    # verifier needs and that final state cannot supply.
                    rv = st.get("recentlyViewed") or []
                    p.log(kind="post", method="POST", path=self.path,
                          action=payload.get("action"),
                          viewing=(rv[0] if rv else None),
                          cart_room=(st.get("cart") or {}).get("roomId")
                                    if isinstance(st.get("cart"), dict) else None,
                          bookings=[{"hotelId": b.get("hotelId"),
                                     "roomType": b.get("roomType"),
                                     "totalCost": b.get("totalCost")}
                                    for b in (st.get("bookings") or [])])
                else:
                    p.log(kind="post", method="POST", path=self.path,
                          action=payload.get("action"))
            except ValueError:
                pass
            self.headers.replace_header("Content-Length", str(len(body))) \
                if "Content-Length" in self.headers else None

        out = self._forward(body)
        if out is None:
            return
        self._respond(*out)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, required=True)
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--state-key-hint", default=None)
    ap.add_argument("--sid-keys", default="mock_sid")
    ap.add_argument("--poll-ms", type=int, default=2000)
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.log), exist_ok=True)
    Handler.proxy = Proxy(a.upstream, a.overlay, a.log, a.state_key_hint,
                          [s for s in a.sid_keys.split(",") if s], a.poll_ms)
    srv = ThreadingHTTPServer(("127.0.0.1", a.listen), Handler)
    srv.daemon_threads = True
    print(f"[proxy] :{a.listen} -> {a.upstream}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
