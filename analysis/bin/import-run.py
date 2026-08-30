#!/usr/bin/env python3
"""
Import one finished rollout into the results archive.

    bin/import-run.py <task-slug> <arm-dir> <source-run-dir> [--tag pilot]

What it does, in order:

  1. RE-SCORES the run from its frozen artifacts with today's verifier, and
     diffs the result against the reward.json stored beside the run. A verifier
     that has moved on since the run was recorded is the normal case here; the
     drift is reported, never silently applied.
  2. Derives the archive folder name from the verdict:
         rNN-<YYYYMMDD-HHMMSS>-<PASS|FAIL>-<score>[-<tag>]
     NN is the next free index inside the arm directory.
  3. Copies the run (minus _atlas/ intermediate frames and ffmpeg.log).
  4. Renders atlas.mp4 if the run does not have one yet. This is a pure
     re-render from raw.mp4 + the frozen snapshot - it never re-runs the agent.
  5. Hardlinks the video into videos/ under a self-describing name. Same
     filesystem, so it costs no extra disk.
  6. Writes run-info.json into the archive folder: where it came from, what it
     scored, and whether re-scoring changed anything.

The source run directory is never modified, except that a missing atlas.mp4 is
rendered into it (additive - nothing is overwritten or removed).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADV = "${ENVOS_ROOT}/cuareplica/output/adversarial"

# Per-task wiring. The two environments predate any shared convention: they
# disagree on interpreter, on what the verifier reads, and on how the video is
# built. That is exactly what this table exists to absorb.
TASKS = {
    "task-01-northgate-clinic": {
        "env": f"{ADV}/northgate_replica_001",
        "py": "python3",
        "score": lambda env, run: [os.path.join(env, "reward.py"),
                                   "--world", os.path.join(run, "world.json")],
        "atlas": lambda env, run: [os.path.join(env, "agent_run", "make_atlas.py"), run],
        "short": "task01-clinic",
    },
    "task-03-xpedia-hotel-booking": {
        "env": f"{ADV}/hub_slot_email_002",
        "py": "python3",
        "score": lambda env, run: [os.path.join(env, "reward.py"),
                                   "--snapshot",
                                   os.path.join(run, "episode_snapshot.json")],
        "atlas": lambda env, run: [os.path.join(env, "agent_run", "make_atlas.py"), run],
        "short": "task03-hotel",
    },
    "task-02-xpedia-travel": {
        "env": f"{ADV}/hub_xapp_commit_003",
        "py": "${ENVOS_ROOT}/envos-kit/.kit/venv/bin/python",
        "score": lambda env, run: [os.path.join(env, "rewards", "reward.py"),
                                   "--snapshot",
                                   os.path.join(run, "episode_snapshot.json")],
        "atlas": lambda env, run: [os.path.join(env, "agent", "make_atlas.py"), run],
        "short": "task02-travel",
    },
}

SKIP = {"_atlas", "ffmpeg.log"}


def die(m):
    sys.exit(f"import-run: {m}")


def run_json(py, argv):
    p = subprocess.run([py] + argv, capture_output=True, text=True)
    if not p.stdout.strip():
        die(f"verifier produced no output ({' '.join(argv)}):\n{p.stderr[-500:]}")
    return json.loads(p.stdout)


def verdict_of(rew):
    """Both verifiers report the same two fields under different spellings."""
    ok = rew.get("terminal_success")
    if ok is None:
        ok = rew.get("pass")
    score = rew.get("dense_reward")
    if score is None:
        score = rew.get("reward")
    return ("PASS" if ok else "FAIL"), float(score)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("arm")
    ap.add_argument("source")
    ap.add_argument("--tag", default=None,
                    help="optional trailing tag, e.g. 'pilot'")
    a = ap.parse_args()

    if a.task not in TASKS:
        die(f"unknown task '{a.task}' - known: {', '.join(TASKS)}")
    cfg = TASKS[a.task]
    src = os.path.abspath(a.source.rstrip("/"))
    if not os.path.isdir(src):
        die(f"no such run directory: {src}")
    arm_dir = os.path.join(ROOT, a.task, a.arm)
    if not os.path.isdir(arm_dir):
        die(f"no such arm directory: {arm_dir}")

    stamp = re.match(r"(\d{8}-\d{6})", os.path.basename(src))
    if not stamp:
        die(f"run directory name does not start with a YYYYMMDD-HHMMSS stamp: "
            f"{os.path.basename(src)}")
    stamp = stamp.group(1)

    # --- 1. re-score, and diff against what was stored at the time ---------
    fresh = run_json(cfg["py"], cfg["score"](cfg["env"], src))
    v_new, s_new = verdict_of(fresh)
    stored_path = os.path.join(src, "reward.json")
    drift = None
    if os.path.exists(stored_path):
        stored = json.load(open(stored_path))
        v_old, s_old = verdict_of(stored)
        if (v_old, s_old) != (v_new, s_new):
            drift = f"stored {v_old} {s_old:.2f} -> re-scored {v_new} {s_new:.2f}"
            print(f"  [drift] {drift}")
        else:
            print(f"  [rescore] unchanged: {v_new} {s_new:.2f}")

    # --- 2. derive the archive name ---------------------------------------
    used = [d for d in os.listdir(arm_dir) if re.match(r"r\d\d-", d)]
    idx = len(used) + 1
    name = f"r{idx:02d}-{stamp}-{v_new}-{s_new:.2f}"
    if a.tag:
        name += f"-{a.tag}"
    dest = os.path.join(arm_dir, name)
    if os.path.exists(dest):
        die(f"destination already exists: {dest}")

    # --- 3. copy ----------------------------------------------------------
    os.makedirs(dest)
    for entry in sorted(os.listdir(src)):
        if entry in SKIP:
            continue
        s, d = os.path.join(src, entry), os.path.join(dest, entry)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    # The archive carries the re-scored verdict; the original is kept beside
    # it whenever the two disagree, so nothing is lost.
    if drift:
        shutil.copy2(stored_path, os.path.join(dest, "reward.as-recorded.json"))
    json.dump(fresh, open(os.path.join(dest, "reward.json"), "w"), indent=2)

    # --- 4. render the video HERE, from the archived copy ------------------
    # It must be rendered after the re-scored reward.json is in place, or the
    # panel would show the verdict the run was given at the time while the
    # folder name and reward.json show today's. Re-render on drift for the
    # same reason.
    atlas_dest = os.path.join(dest, "atlas.mp4")
    if drift or not os.path.exists(atlas_dest):
        why = "re-scored" if drift else "no video on this run"
        print(f"  [atlas] {why} - rendering from frozen artifacts "
              f"(the agent is NOT re-run)")
        if os.path.exists(atlas_dest):
            os.remove(atlas_dest)
        p = subprocess.run([cfg["py"]] + cfg["atlas"](cfg["env"], dest),
                           capture_output=True, text=True)
        if not os.path.exists(atlas_dest):
            die(f"atlas render failed:\n{p.stdout[-800:]}\n{p.stderr[-800:]}")
        print(f"  [atlas] rendered {os.path.getsize(atlas_dest) // 1024}K")
        # The renderer leaves ~10 MB of intermediate frames in dest/_atlas.
        # The copy step (SKIP) already excludes them from the source run, so
        # drop the ones the render just created here as well.
        shutil.rmtree(os.path.join(dest, "_atlas"), ignore_errors=True)
        log = os.path.join(dest, "ffmpeg.log")
        if os.path.exists(log):
            os.remove(log)

    # --- 5. hardlink the video under a self-describing name ---------------
    vid = f"{cfg['short']}__{a.arm}__r{idx:02d}__{v_new}-{s_new:.2f}.mp4"
    vpath = os.path.join(ROOT, "videos", vid)
    if os.path.exists(vpath):
        os.remove(vpath)
    try:
        os.link(atlas_dest, vpath)
    except OSError:
        shutil.copy2(os.path.join(dest, "atlas.mp4"), vpath)

    # --- 6. provenance ----------------------------------------------------
    inv = fresh.get("invariants") or {}
    json.dump({
        "task": a.task, "arm": a.arm, "run": name,
        "source_run_dir": src,
        "environment": cfg["env"],
        "arm_recorded": fresh.get("arm"),
        "verdict": v_new, "dense_reward": s_new,
        "failed_invariants": [k for k, ok in inv.items() if not ok],
        "diagnosis": fresh.get("diagnosis"),
        "rescore_drift": drift,
        "video": f"videos/{vid}",
    }, open(os.path.join(dest, "run-info.json"), "w"), indent=2)

    mb = sum(os.path.getsize(os.path.join(r, f))
             for r, _, fs in os.walk(dest) for f in fs) // (1024 * 1024)
    print(f"  [ok] {a.task}/{a.arm}/{name}  ({mb} MB)  -> videos/{vid}")


if __name__ == "__main__":
    main()
