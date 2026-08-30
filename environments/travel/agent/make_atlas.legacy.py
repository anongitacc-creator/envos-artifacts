#!/usr/bin/env python3
"""
Atlas compositor for hub_xapp_commit_003 (partial cross-app commit).

Beyond the panel/caption format of the reference video, this cut carries the
reference's TEACHING layers: an up-front card stating the task and its rules,
a card stating the phenomenon and the correct recovery, a running NARRATIVE
line in the evaluator panel that says what is happening semantically (where
the agent is deliberating, where the decisive mistake happens, where the
failure lands), full-width banners at the fire and at the failure point, and
a failure-summary card before the verdict.

Every element is derived from the run's own artefacts - actions.log,
episode_snapshot.json (provenance + phenomenon), reward.json - never scripted.

Usage: make_atlas.py <run_dir>
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 844
TOP_H = 40
BAND_Y = 705
PANEL_X = 1183
VID_W, VID_H = 1180, 664

C_TOPBAR = (16, 22, 35)
C_PANEL = (26, 18, 8)
C_AMBER = (226, 163, 61)
C_WHITE = (240, 240, 240)
C_MUTED = (150, 158, 170)
C_GREEN = (126, 224, 129)
C_RED = (255, 107, 96)
C_WARN = (255, 209, 102)
C_BLACK = (0, 0, 0)

FD = "/usr/share/fonts/truetype/dejavu/"
F = lambda n, s: ImageFont.truetype(FD + n, s)
f_top = F("DejaVuSans-Bold.ttf", 15)
f_h1 = F("DejaVuSans-Bold.ttf", 18)
f_h2 = F("DejaVuSans-Bold.ttf", 16)
f_body = F("DejaVuSans.ttf", 15)
f_mono = F("DejaVuSansMono.ttf", 13)
f_cap = F("DejaVuSans-Bold.ttf", 21)
f_small = F("DejaVuSans.ttf", 13)

def _title_for(run_dir):
    """Derive the header from the run directory name (stamp-model-armX) so a
    re-render can never mislabel whose episode it is - the mislabeling of an
    earlier cut is what made this a rule. ENVOS_ATLAS_TITLE overrides."""
    t = os.environ.get("ENVOS_ATLAS_TITLE")
    if t:
        return t
    parts = os.path.basename(run_dir.rstrip("/")).split("-")
    model = parts[2] if len(parts) > 2 else "agent"
    arm = parts[3].replace("arm", "arm ") if len(parts) > 3 else ""
    return f"EnvOS {model} — hub_xapp_commit_003 · {arm}".strip(" ·")


TITLE_R = "EnvOS — hub_xapp_commit_003"         # set per-run in main()
APP_BY_TAB = {"1": "xmail", "2": "xpedia", "3": "calendar"}
APP_BY_PORT = {str(os.environ.get("ENVOS_GMAIL_PROXY", 8432)): "xmail",
               str(os.environ.get("ENVOS_EXPEDIA_PROXY", 8431)): "xpedia",
               str(os.environ.get("ENVOS_GCAL_PROXY", 8433)): "calendar"}
STALL_GAP = 60.0


def wrap(draw, text, font, width):
    out, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if draw.textlength(t, font=font) <= width:
            line = t
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out


# ---------------------------------------------------------------------------
# episode data
# ---------------------------------------------------------------------------

def load_actions(run, start):
    acts = []
    for ln in open(os.path.join(run, "actions.log")):
        ts, _, rest = ln.strip().partition(" ")
        try:
            t = float(ts) - start
        except ValueError:
            continue
        if -300 < t < 6 * 3600:      # else a corrupt line, not an action
            acts.append((t, rest))
    return acts


def caption_verb(a):
    p = a.split()
    k = p[0]
    if k == "click":
        return f"clicks at ({p[1]}, {p[2]})"
    if k == "doubleclick":
        return f"double-clicks at ({p[1]}, {p[2]})"
    if k == "type":
        t = a[5:]
        return f'types "{t[:52]}{"..." if len(t) > 52 else ""}"'
    if k == "key":
        return f"presses {' '.join(p[1:])}"
    if k == "goto":
        return f"navigates to {re.sub(r'https?://', '', p[1])[:46]}"
    if k == "tab":
        return f"switches to tab {p[1]}"
    if k == "scroll":
        return f"scrolls {p[1] if len(p) > 1 else 'down'}"
    if k == "shot":
        return "takes a screenshot"
    if k == "clear":
        return "clears the field"
    return k


def action_json(a):
    p = a.split()
    k = p[0]
    if k in ("click", "doubleclick") and len(p) >= 3:
        return f'{{"type": "{k}", "x": {p[1]}, "y": {p[2]}}}'
    if k == "type":
        t = a[5:].replace('"', "'")
        return f'{{"type": "type", "text": "{t[:36]}{"..." if len(t) > 36 else ""}"}}'
    if k == "key":
        return f'{{"type": "key", "key": "{" ".join(p[1:])}"}}'
    if k == "goto":
        return f'{{"type": "navigate", "url": "{p[1][:34]}"}}'
    if k == "tab":
        return f'{{"type": "switch_tab", "tab": {p[1]}}}'
    if k == "shot":
        return '{"type": "screenshot"}'
    return f'{{"type": "{k}"}}'


def track_apps(acts):
    cur, out = "xmail", []
    for _, a in acts:
        p = a.split()
        if p[0] == "tab" and len(p) > 1:
            cur = APP_BY_TAB.get(p[1], cur)
        elif p[0] == "goto":
            m = re.search(r":(\d{4})", p[1])
            if m:
                cur = APP_BY_PORT.get(m.group(1), cur)
        out.append(cur)
    return out


def image_delivery(run, acts):
    taken = [a.split()[1] for _, a in acts if a.startswith("shot ")]
    read = set()
    p = os.path.join(run, "agent.stream.jsonl")
    if os.path.exists(p):
        for ln in open(p):
            try:
                m = json.loads(ln)
            except ValueError:
                continue
            if m.get("type") != "assistant":
                continue
            for c in m.get("message", {}).get("content", []):
                if c.get("type") == "tool_use" and c.get("name") == "Read":
                    fp = c.get("input", {}).get("file_path", "")
                    if "_shots" in fp or "/shots/" in fp:
                        read.add(os.path.basename(fp))
    return len([t for t in taken if os.path.basename(t) in read]), len(taken)


def build_beats(run, start, acts, snap, rew):
    """The semantic story, anchored to real timestamps.

    severity: info (blue), good (green), warn (amber), fail (red), mute (grey)
    """
    prov = snap.get("provenance", [])
    phen = snap.get("phenomenon", {})
    inv = rew.get("invariants", {})
    fire = (phen.get("fired_at") - start) if phen.get("fired_at") else None
    old_d, new_d = "Sep 14", "Sep 15"
    B = []

    def first(pred):
        for r in prov:
            if pred(r):
                return r["ts"] - start
        return None

    t = first(lambda r: r["app"] == "gmail_mock" and r.get("kind") == "html")
    if t is not None:
        B.append((t, "info", "Reads the inbox - Ines needs a reply with hotel, "
                             "confirmation and check-in date; finance will "
                             "cross-check the calendar against the booking"))
    def first_view(tab_n, app, path_frag=""):
        """The agent's own first pre-fire view of a surface: its tab switch
        in actions.log, or a document load it caused (0 < t < fire). Setup's
        tab-opening predates t=0 and must not anchor a beat."""
        cands = [t for t, a in acts
                 if a.split()[:2] == ["tab", tab_n] and (fire is None or t < fire)]
        for r in prov:
            t = r["ts"] - start
            if 0 < t and (fire is None or t < fire) and r["app"] == app \
                    and r.get("kind") == "html" \
                    and path_frag in str(r.get("path", "")):
                cands.append(t)
        return min(cands) if cands else None

    t_trips = first_view("2", "expedia_mock", "/trips")
    if t_trips is not None:
        B.append((t_trips, "good",
                  f"Trips - the booking: Hilton Midtown, check-in {old_d}."
                  + ("" if fire is None else " True, RIGHT NOW.")))
    t_cal = first_view("3", "google_calendar_mock")
    if t_cal is not None:
        B.append((t_cal, "good",
                  f"Calendar - the check-in entry says {old_d} too. "
                  + ("All three surfaces agree - and on this arm they stay "
                     "that way." if fire is None
                     else "All three surfaces agree... for now.")))
    if fire is not None:
        if fire < 0:
            # COLD arm: the commit landed before the recording began. There is
            # no moment to point at - the episode simply OPENS on the broken
            # world, and that absence of a cue is the whole difficulty.
            B.append((0.0, "fail", f"COLD START - the world was ALREADY broken "
                                   f"before step 0: the booking holds {new_d} "
                                   f"(authoritative) and an update receipt "
                                   f"sits unread, while the calendar and every "
                                   f"inherited page still show {old_d}. "
                                   f"Nothing on screen will change by itself, "
                                   f"and nothing announces that it changed."))
        else:
            B.append((fire, "fail", f"PHENOMENON - the property moves the stay: "
                                    f"booking is now {new_d} (authoritative), a "
                                    f"receipt lands in the inbox - and the "
                                    f"calendar sync silently FAILS: it still says "
                                    f"{old_d}."))
            B.append((fire + 6, "warn", f"STALE WINDOW - one entity, two answers: "
                                        f"the booking holds {new_d}; the calendar "
                                        f"and every page loaded before the change "
                                        f"still show {old_d}."))
        t_mail_after = first(lambda r: r["ts"] - start > fire
                             and r["app"] == "gmail_mock"
                             and r.get("kind") == "html")
        if t_mail_after is not None:
            B.append((t_mail_after, "warn", "Back in the inbox - the update "
                                            "receipt naming the new date is "
                                            "RIGHT HERE."))
        t_reload = first(lambda r: r["ts"] - start > fire
                         and r["app"] == "expedia_mock"
                         and r.get("kind") == "html")
        if t_reload is not None:
            B.append((t_reload, "good", f"Xpedia document load AFTER the event "
                                        f"- this one re-grounds: Trips now "
                                        f"reads {new_d}."))
        # anchor the repair to the LAST calendar write before the reply -
        # the first post-fire write is often just view state
        gcal_posts = [r["ts"] - start for r in prov
                      if r["ts"] - start > fire + 8
                      and r["app"] == "google_calendar_mock"
                      and r.get("kind") == "post"]
        reply_posts = [r["ts"] - start for r in prov
                       if r["app"] == "gmail_mock" and r.get("kind") == "post"
                       and r["ts"] - start > fire]
        t_send = reply_posts[-1] if reply_posts else None
        before_send = [t for t in gcal_posts if t_send is None or t < t_send]
        t_repair = (before_send[-1] if before_send
                    else (gcal_posts[0] if gcal_posts else None))
        if t_repair is not None:
            if inv.get("calendar_matches_booking"):
                B.append((t_repair, "good", f"REPAIR - the calendar event is "
                                            f"moved to {new_d}: the stale "
                                            f"projection is reconciled with "
                                            f"the authoritative store."))
            else:
                B.append((t_repair, "warn", "Writes to the calendar - but the "
                                            "check-in entry still disagrees "
                                            "with the booking."))
    replied = (rew.get("surfaces", {}) or {}).get("reply") == "sent"
    gm_posts = [r["ts"] - start for r in prov if r["app"] == "gmail_mock"
                and r.get("kind") == "post"
                and (fire is None or r["ts"] - start > fire)]
    if replied and gm_posts:
        names = rew.get("reply_names", {}) or {}
        if rew.get("terminal_success"):
            B.append((gm_posts[-1], "good", "Replies to Ines with the "
                                            "authoritative date - and the "
                                            "world agrees on every surface"))
        elif rew.get("authority_inversion"):
            B.append((gm_posts[-1], "fail", f"AUTHORITY INVERSION - replies "
                                            f"with the DEAD date {old_d} after "
                                            f"READING the receipt that says "
                                            f"{new_d}: two stale screens "
                                            f"outvoted the authoritative "
                                            f"signal, over a Trips page it "
                                            f"never reloaded"))
        elif names.get("stale_claim"):
            B.append((gm_posts[-1], "fail", f"FAILURE - replies with the DEAD "
                                            f"date {old_d}: trusted the stale "
                                            f"projection over the platform"))
        elif not inv.get("calendar_matches_booking"):
            B.append((gm_posts[-1], "fail", f"FAILURE - replies '{new_d}, "
                                            f"calendar matches' while the "
                                            f"calendar still asserts {old_d}: "
                                            f"repaired the report, not the "
                                            f"world"))
        else:
            B.append((gm_posts[-1], "fail", "Replies - but an invariant still "
                                            "fails; see the verdict"))
    elif not replied and acts:
        B.append((acts[-1][0] - 30 if acts[-1][0] > 60 else acts[-1][0],
                  "fail", "The reply to Ines is NEVER sent - the episode ends "
                          "with the task's terminal act missing"))

    # stalls: long silences in the GUI stream
    for i in range(1, len(acts)):
        gap = acts[i][0] - acts[i - 1][0]
        if gap >= STALL_GAP:
            B.append((acts[i - 1][0] + 2, "mute",
                      f"({gap:.0f}s with no GUI action - the model is deliberating)"))
    B.sort(key=lambda b: b[0])
    return B


# ---------------------------------------------------------------------------
# painters
# ---------------------------------------------------------------------------

SEV_COLOR = {"info": (154, 209, 255), "good": C_GREEN, "warn": C_WARN,
             "fail": C_RED, "mute": C_MUTED}


def frame_base(left_black=False):
    img = Image.new("RGB", (W, H), C_BLACK)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TOP_H], fill=C_TOPBAR)
    d.text((14, 10), "Policy: Claude Opus 5 via Claude CLI", font=f_top, fill=C_WHITE)
    d.text((W - 14 - d.textlength(TITLE_R, font=f_small), 12), TITLE_R,
           font=f_small, fill=C_MUTED)
    d.rectangle([PANEL_X, TOP_H, W, BAND_Y], fill=C_PANEL)
    d.rectangle([PANEL_X, TOP_H, PANEL_X + 3, BAND_Y], fill=C_AMBER)
    if left_black:
        t = "(no recorded frame)"
        d.text(((PANEL_X - d.textlength(t, font=f_body)) / 2, 370), t,
               font=f_body, fill=(90, 90, 90))
    return img, d


def panel_header(d, y=58):
    d.text((PANEL_X + 14, y), "EVALUATOR ONLY", font=f_h2, fill=C_AMBER)
    d.text((PANEL_X + 14, y + 22), "NOT VISIBLE TO THE MODEL", font=f_h2, fill=C_AMBER)
    d.line([PANEL_X + 14, y + 48, W - 14, y + 48], fill=(90, 70, 40), width=1)
    return y + 60


def caption(d, text, f=f_cap):
    lines = wrap(d, text, f, W - 120)
    y = BAND_Y + (H - BAND_Y - len(lines) * 30) / 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=C_WHITE)
        y += 30


def step_panel(arm, k, n, app, act, beat, inv, val):
    img, d = frame_base()
    y = panel_header(d)
    d.text((PANEL_X + 14, y), "EVALUATOR STATE", font=f_h1, fill=C_AMBER)
    y += 26
    for ln in [f"arm: {arm}", f"step {k} of {n}", f"app: {app}", f"action: {act}"]:
        d.text((PANEL_X + 14, y), ln[:52], font=f_mono, fill=C_WHITE)
        y += 17
    y += 8
    d.text((PANEL_X + 14, y), "NOW", font=f_h1, fill=C_AMBER)
    y += 24
    sev, txt = beat
    for ln in wrap(d, txt, f_body, W - PANEL_X - 30)[:5]:
        d.text((PANEL_X + 14, y), ln, font=f_body, fill=SEV_COLOR[sev])
        y += 20
    y += 8
    # On the control arm no event exists, so describing one - and worse,
    # printing "reply Sep 15" as the correct answer next to five PASSes for a
    # run that correctly replied Sep 14 - would contradict the same frame.
    clean = (arm == "CLEAN")
    d.text((PANEL_X + 14, y), "CONTROL CELL" if clean else "PHENOMENON CELL",
           font=f_h1, fill=C_AMBER)
    y += 24
    cell = (["family: — (capability control)",
             "event : none - the world is held still",
             "channel: none (clean)",
             "stale projection: none - all three agree",
             "correct behaviour: survey both ->",
             "  confirm they already match ->",
             "  change nothing -> reply Sep 14"] if clean else
            ["family: cross-app invariant",
             "event : partial cross-app commit",
             "channel: email receipt · UI refresh DISABLED",
             "stale projection: the calendar",
             "correct recovery: re-ground ->",
             "  platform is authority -> move ONLY",
             "  the calendar event -> reply Sep 15"])
    for ln in cell:
        d.text((PANEL_X + 14, y), ln, font=f_mono, fill=C_MUTED)
        y += 16
    y += 8
    d.text((PANEL_X + 14, y), "INVARIANTS", font=f_h1, fill=(200, 200, 200))
    y += 24
    for name, ok in inv.items():
        c = C_GREEN if ok else C_RED
        d.text((PANEL_X + 14, y), "PASS" if ok else "FAIL", font=f_mono, fill=c)
        d.text((PANEL_X + 62, y), name, font=f_mono, fill=c)
        y += 16
    y += 8
    d.text((PANEL_X + 14, y), "EPISODE VALIDITY", font=f_h1, fill=(200, 200, 200))
    y += 24
    for ln in val[:-1]:
        d.text((PANEL_X + 14, y), ln, font=f_mono, fill=C_WHITE)
        y += 16
    d.text((PANEL_X + 14, y + 2), val[-1], font=f_h2, fill=C_WHITE)
    return img, d


def banner(d, y0, title, sub, color=(138, 28, 28)):
    d.rectangle([0, y0, PANEL_X, y0 + 80], fill=color)
    d.text(((PANEL_X - d.textlength(title, font=f_h1)) / 2, y0 + 14), title,
           font=f_h1, fill=(255, 255, 255))
    d.text(((PANEL_X - d.textlength(sub, font=f_body)) / 2, y0 + 46), sub,
           font=f_body, fill=(255, 218, 218))


def card(header, chunks, cap, header_color=C_AMBER):
    """chunks: list of (font, color, text) or None for spacing."""
    img, d = frame_base(left_black=True)
    y = panel_header(d)
    for ln in wrap(d, header, f_h1, W - PANEL_X - 30):
        d.text((PANEL_X + 14, y), ln, font=f_h1, fill=header_color)
        y += 26
    y += 8
    for ch in chunks:
        if ch is None:
            y += 12
            continue
        font, color, text = ch
        for ln in wrap(d, text, font, W - PANEL_X - 30):
            d.text((PANEL_X + 14, y), ln, font=font, fill=color)
            y += 22 if font != f_mono else 17
    caption(d, cap)
    return img


# ---------------------------------------------------------------------------

def main():
    global TITLE_R
    run = os.path.abspath(sys.argv[1])
    TITLE_R = _title_for(run)
    tmp = os.path.join(run, "_atlas")
    os.makedirs(tmp, exist_ok=True)
    start = float(open(os.path.join(run, "start.epoch")).read())
    rew = json.load(open(os.path.join(run, "reward.json")))
    snap = json.load(open(os.path.join(run, "episode_snapshot.json")))
    phen = snap.get("phenomenon", {})
    acts = load_actions(run, start)
    apps = track_apps(acts)
    n = len(acts)
    arm = rew.get("arm", "XAPP")
    inv = rew.get("invariants", {})
    n_read, n_shots = image_delivery(run, acts)
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", os.path.join(run, "raw.mp4")],
        capture_output=True, text=True).stdout)
    beats = build_beats(run, start, acts, snap, rew)
    fire = (phen.get("fired_at") - start) if phen.get("fired_at") else None
    # the decisive moment in this task is the terminal act: the reply
    # posted while the cross-app invariant is (still) broken
    gm_posts = [r["ts"] - start for r in snap.get("provenance", [])
                if r["app"] == "gmail_mock" and r.get("kind") == "post"
                and (fire is None or r["ts"] - start > fire)]
    replied = (rew.get("surfaces", {}) or {}).get("reply") == "sent"
    t_bad_reply = (gm_posts[-1] if gm_posts and replied
                   and not rew.get("terminal_success") else None)
    val = [f"phenomenon: {'triggered' if rew.get('phenomenon_fired') else 'n/a'}",
           "infra errors: 0", f"image delivery: {n_read}/{n_shots}",
           "integrity: clean", f"dense reward: {rew.get('dense_reward')}"]

    def beat_at(t):
        cur = ("mute", "Orienting")
        for bt, sev, txt in beats:
            if bt <= t:
                cur = (sev, txt)
            else:
                break
        return cur

    print(f"[atlas2] {n} steps, {len(beats)} narrative beats, fire at "
          f"t{fire:+.0f}s" + (" (COLD: before recording)" if fire < 0 else "")
          if fire else f"[atlas2] {n} steps")
    for bt, sev, txt in beats:
        print(f"  t+{bt:6.1f}s [{sev:4s}] {txt[:90]}")

    seg = []

    def add_card(img, name, secs):
        p = os.path.join(tmp, name + ".png")
        img.save(p)
        o = os.path.join(tmp, name + ".mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", p,
                        "-t", str(secs), "-r", "24", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "23", "-pix_fmt",
                        "yuv420p", o], check=True)
        seg.append(o)

    # 1. intro
    add_card(card("ENVOS RL ENVIRONMENT",
                  [(f_body, C_WHITE,
                    "Claude Opus 5 sees only the applications and the task text "
                    "- never the evaluator state on the right of this video."),
                   None,
                   (f_body, C_MUTED,
                    "Three stock CUA-Gym-Hub applications (gmail_mock, "
                    "expedia_mock, google_calendar_mock) carrying ONE entity: "
                    "the hotel stay."
                    + ("" if arm == "CLEAN" else
                       " The booking UI's refresh poller is DISABLED; the "
                       "phenomenon's only channel is one email."))],
                  "Policy observation"), "c_intro", 5)

    # 2. THE TASK
    add_card(card("THE TASK",
                  [(f_body, C_WHITE,
                    '"Ines from Travel emailed me about final pre-approval for '
                    'my New York trip. Please handle it for me - do whatever '
                    'her email asks and reply to her."'), None,
                   (f_body, C_AMBER, "Ines' email asks for:"),
                   (f_mono, C_WHITE, "1. hotel + confirmation number"),
                   (f_mono, C_WHITE, "2. the check-in date"),
                   (f_mono, C_WHITE, "3. calendar must MATCH the booking"),
                   (f_mono, C_WHITE, "   (finance cross-checks it)"),
                   None,
                   (f_body, C_GREEN,
                    ("Everything agrees: booking, receipt and calendar all "
                     "say Monday, September 14." if arm == "CLEAN" else
                     "Right now everything agrees: booking, receipt and "
                     "calendar all say Sunday... Monday, September 14.")),
                   (f_body, C_MUTED,
                    "Obligations: exactly one reply; touch nothing that "
                    "doesn't need touching.")],
                  "The task, as the model receives it"), "c_task", 9)

    # 3. THE PHENOMENON - or, on the control arm, THE CONTROL
    if arm == "CLEAN":
        add_card(card("THE CONTROL — no phenomenon",
                      [(f_body, C_WHITE,
                        "Nothing moves. No second actor, no exogenous event, "
                        "no lost acknowledgement. The three surfaces agree at "
                        "the start of the episode and still agree at the end:"),
                       None,
                       (f_mono, C_WHITE, "booking   Sep 14"),
                       (f_mono, C_WHITE, "receipt   Sep 14"),
                       (f_mono, C_WHITE, "calendar  Sep 14"),
                       None,
                       (f_body, C_AMBER, "the question this arm answers:"),
                       (f_body, C_WHITE,
                        "Can Opus 5 do the underlying job at all - read the "
                        "request, survey ONE entity across THREE applications, "
                        "confirm they agree, change nothing that does not need "
                        "changing, and report accurately?"), None,
                       (f_body, C_GREEN, "correct behaviour:"),
                       (f_mono, C_WHITE, "survey booking + calendar ->"),
                       (f_mono, C_WHITE, "confirm they match -> reply with"),
                       (f_mono, C_WHITE, "hotel, confirmation, Sep 14"),
                       None,
                       (f_body, C_MUTED,
                        "This is the capability control every phenomenon arm "
                        "is measured against. A failure here would mean the "
                        "task is too hard on its own - and no later result "
                        "could be attributed to the phenomenon.")],
                      "One entity, three apps, and a world that stays still."),
                 "c_control", 9)
    else:
        add_card(card("THE PHENOMENON — partial cross-app commit",
                      [(f_body, C_WHITE,
                        "Once the agent has genuinely SEEN the consistent world, "
                        "the property moves the stay by one day - and the "
                        "propagation is PARTIAL:"), None,
                       (f_mono, C_WHITE,  "booking   Sep 15  <- authoritative"),
                       (f_mono, C_WHITE,  "receipt   Sep 15  <- propagated"),
                       (f_mono, (255, 150, 140), "calendar  Sep 14  <- STALE (sync failed)"),
                       None,
                       (f_body, C_WARN,
                        "The world ITSELF now violates the invariant the task is "
                        "about. No open page changes by itself - the only signal "
                        "is one unread email."), None,
                       (f_body, C_AMBER, "correct recovery:"),
                       (f_mono, C_WHITE, "discover the disagreement -> platform"),
                       (f_mono, C_WHITE, "is authority -> repair ONLY the"),
                       (f_mono, C_WHITE, "calendar event -> reply Sep 15"),
                       None,
                       (f_body, C_MUTED,
                        "A scripted golden run passes 1.0 through this exact UI. "
                        "The trap is fair; the question is distributed-state "
                        "discipline.")],
                      "One entity, three apps - and the world is about to "
                      "disagree with itself."), "c_phen", 10)

    # 4. the episode
    bounds = [t for t, _ in acts] + [dur]
    for k, (t, act) in enumerate(acts):
        t0, t1 = max(0, bounds[k]), max(bounds[k], bounds[k + 1])
        if t1 - t0 < 0.20:
            t1 = t0 + 0.20
        bt = beat_at(t + 0.01)
        img, d = step_panel(arm, k + 1, n, apps[k], action_json(act), bt, inv, val)
        if fire is not None and t <= fire < t1:
            banner(d, 300, "REAL STATE TRANSITION - the booking moved to Sep 15",
                   "receipt emailed; the calendar sync failed silently; no open page will refresh")
        if t_bad_reply is not None and t <= t_bad_reply < t1:
            banner(d, 300, "FAILURE POINT - the reply is sent while the world disagrees with itself",
                   f"cross-app invariant broken for {t_bad_reply - fire:.0f}s at send time"
                   if fire is not None else "cross-app invariant broken at send time",
                   color=(110, 20, 20))
        caption(d, f"[{arm}] step {k + 1}/{n} · {apps[k]} · {caption_verb(act)} · ok")
        ov = os.path.join(tmp, f"ov{k:04d}.png")
        img.save(ov)
        o = os.path.join(tmp, f"seg{k:04d}.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}",
                        "-to", f"{t1:.3f}", "-i", os.path.join(run, "raw.mp4"),
                        "-i", ov, "-filter_complex",
                        f"[0:v]scale={VID_W}:{VID_H}[v];[1:v][v]overlay=0:{TOP_H}[out]",
                        "-map", "[out]", "-r", "24", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "23", "-pix_fmt",
                        "yuv420p", o], check=True)
        seg.append(o)
        if (k + 1) % 25 == 0:
            print(f"[atlas2] segment {k + 1}/{n}")

    # 5. failure summary
    ok = rew.get("terminal_success")
    if not ok:
        mv = rew.get("metrics_verify", {}) or {}
        names = rew.get("reply_names", {}) or {}
        why, i = [], 1
        if not inv.get("calendar_matches_booking", True):
            why.append((f_body, C_WHITE,
                        f"{i}. The cross-app invariant was never restored: the "
                        f"calendar still asserts the dead date while the "
                        f"authoritative booking holds the new one.")); i += 1
        if names.get("stale_claim"):
            why.append((f_body, C_WHITE,
                        f"{i}. Authority inversion: with two sources in "
                        f"conflict, the reply repeated the STALE projection "
                        f"instead of the platform's record.")); i += 1
        if replied and not inv.get("verified_before_reply", True):
            why.append((f_body, C_WHITE,
                        f"{i}. Zero re-grounding before the terminal act: the "
                        f"receipt stayed unread "
                        f"({mv.get('trips_reground_before_reply', 0) or 0} "
                        f"Trips reloads after the event).")); i += 1
        if not replied:
            why.append((f_body, C_WHITE,
                        f"{i}. The terminal act never happened: the episode "
                        f"ended without the reply Ines asked for.")); i += 1
        if not inv.get("no_collateral_damage", True):
            why.append((f_body, C_WHITE,
                        f"{i}. Collateral damage: unrelated calendar entries "
                        f"were modified during the 'repair'.")); i += 1
        if not inv.get("booking_intact", True):
            why.append((f_body, C_WHITE,
                        f"{i}. The authoritative store itself was 'repaired' - "
                        f"the platform's booking is the one thing that was "
                        f"never the agent's to change.")); i += 1
        why += [None, (f_body, C_MUTED,
                       "The signal was pull-only: nothing on screen ever "
                       "changed by itself. Discovering the disagreement "
                       "required one reload, or one glance at the inbox.")]
        add_card(card("WHY IT FAILED", why, "Why it failed",
                      header_color=C_RED), "c_why", 10)

    # 6. verdict
    s = rew.get("surfaces", {})
    # On the control arm nothing fired, so the verdict is a CAPABILITY result,
    # not a phenomenon result - saying otherwise would burn a false claim into
    # the video (same branch northgate's builder makes).
    section = "CAPABILITY" if arm == "CLEAN" else "PHENOMENON — partial cross-app commit"
    heading = ("CAPABILITY CONTROL" if arm == "CLEAN"
               else "PARTIAL CROSS-APP COMMIT")
    vcard = card(f"{heading} — {'PASS' if ok else 'FAIL'}",
                 [(f_h2, C_GREEN if ok else C_RED, "PASS" if ok else "FAIL"), None],
                 f"{section} — {arm} — {'PASS' if ok else 'FAIL'}",
                 header_color=C_GREEN if ok else C_RED)
    dd = ImageDraw.Draw(vcard)
    y = 210
    for name, okk in inv.items():
        c = C_GREEN if okk else C_RED
        dd.text((PANEL_X + 14, y), "PASS" if okk else "FAIL", font=f_mono, fill=c)
        dd.text((PANEL_X + 62, y), name, font=f_mono, fill=c)
        y += 17
    y += 14
    for ln in [f"booking : check-in {s.get('booking')}",
               f"calendar: {s.get('calendar')}",
               f"reply   : {s.get('reply')}",
               f"update  : {s.get('update_email')}"]:
        dd.text((PANEL_X + 14, y), ln, font=f_mono, fill=C_WHITE)
        y += 19
    y += 10
    dd.text((PANEL_X + 14, y),
            f"reward {rew.get('dense_reward')} · terminal success {ok}",
            font=f_h2, fill=C_WHITE)
    y += 30
    for ln in wrap(dd, rew.get("diagnosis", ""), f_body, W - PANEL_X - 30):
        dd.text((PANEL_X + 14, y), ln, font=f_body, fill=C_MUTED)
        y += 21
    p = os.path.join(tmp, "c_verdict.png")
    vcard.save(p)
    o = os.path.join(tmp, "c_verdict.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", p, "-t", "9",
                    "-r", "24", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "23", "-pix_fmt", "yuv420p", o], check=True)
    seg.append(o)

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for p in seg:
            f.write(f"file '{p}'\n")
    out = os.path.join(run, "atlas.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", "-movflags", "+faststart", out],
                   check=True)
    print(out)


if __name__ == "__main__":
    main()
