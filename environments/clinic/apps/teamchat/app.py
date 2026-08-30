"""
TeamChat - the chat leg of the propagation chain; functional stand-in for the
video's Mattermost Ops channel (not branded as Mattermost). Seeded with the
channel's prior traffic, including the two earlier vaccination announcements
that establish the reporting convention, and one unrelated standing request as
a distractor.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, redirect, url_for, render_template
from world import world, audit, requester

app = Flask(__name__)


@app.route("/")
def channel():
    with world(write=True) as w:
        audit(w, requester(), "chat_view",
              messages=len(w["chat"]["messages"]))
        return render_template("channel.html", chat=w["chat"])


@app.route("/post", methods=["POST"])
def post():
    text = request.form.get("text", "").strip()
    with world(write=True) as w:
        if text:
            w["chat"]["messages"].append({
                "id": f"c{len(w['chat']['messages']) + 1}",
                "author": "clinic.scheduler",
                "when": time.strftime("%b %d, %I:%M %p"),
                "text": text})
            audit(w, requester(), "chat_post", chars=len(text), text=text[:200])
        return redirect(url_for("channel"))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--port", type=int, default=8087)
    a = p.parse_args()
    app.run(host="127.0.0.1", port=a.port, debug=False, use_reloader=False, threaded=True)
