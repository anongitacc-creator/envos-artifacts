#!/usr/bin/env python3
"""
Statistical analysis over the whole run archive.

Produces everything a reviewer at an agent-evaluation venue asks for and the
archive does not otherwise state: interval estimates rather than bare
fractions, an all-trials reliability figure, an effect size and an exact test
for the controlled contrasts, and per-arm taxonomy metadata pulled from the
atlas specs so the failure atlas is a table rather than prose.

No SciPy: Wilson intervals and Fisher's exact test are implemented here so the
numbers can be reproduced from a bare Python.

Outputs (analysis/):
  atlas.csv          one row per arm - the machine-readable failure atlas
  runs.csv           one row per run
  contrasts.md       the controlled comparisons, with tests
  summary.md         headline numbers
"""
import csv
import json
import math
import os
import sys
from collections import Counter, OrderedDict

# repo root: analysis/bin/analyse.py -> analysis/bin -> analysis -> <root>
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENVS = os.path.join(ROOT, "environments")
SNAPS = os.path.join(ROOT, "snapshots")
# task id <-> released environment directory (snapshots/<env>, environments/<env>)
ENVDIR = {
    "task-01-northgate-clinic": "clinic",
    "task-02-xpedia-travel": "travel",
    "task-03-xpedia-hotel-booking": "hotel",
}
TASK_OF = {v: k for k, v in ENVDIR.items()}
SPECS = {
    t: os.path.join(ENVS, d, "atlas.spec.json") for t, d in ENVDIR.items()
}
SIGNATURES = ("wrong_entity", "update_neglected", "obsolete_policy",
              "paraphrase_over_source", "deprecated_tool_retry",
              "malformed_migration", "tool_abandoned", "fabricated_tool_use",
              "blind_retry", "permission_defiance", "premature_abandonment",
              "authority_inversion", "stale_commit_not_repaired",
              "propagated_intent_not_state", "coercion_undetected",
              "coercion_repaired", "rebooked_after_coercion",
              "verified_once_then_acted")


# --- statistics -------------------------------------------------------------

def wilson(k, n, z=1.96):
    """Wilson score interval. Chosen over the normal approximation because at
    k=3..8 with proportions at 0 or 1 the normal interval is degenerate - it
    reports width zero for exactly the results this archive cares about."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pass_hat_k(passes, n):
    """pass^k: did EVERY trial succeed. The reliability figure tau-bench
    argues for - pass@k rises towards 1 with more trials and hides
    brittleness, pass^k falls towards 0 and exposes it."""
    return 1.0 if n and passes == n else 0.0


def _logfact(n, _c={}):
    if n not in _c:
        _c[n] = math.lgamma(n + 1)
    return _c[n]


def _hyper(a, b, c, d):
    n = a + b + c + d
    return math.exp(_logfact(a + b) + _logfact(c + d) + _logfact(a + c)
                    + _logfact(b + d) - _logfact(n) - _logfact(a)
                    - _logfact(b) - _logfact(c) - _logfact(d))


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact test on a 2x2 table. Exact rather than chi-square
    because every cell here is single digits."""
    obs = _hyper(a, b, c, d)
    tot = 0.0
    r1, r2 = a + b, c + d
    c1 = a + c
    for x in range(0, min(r1, c1) + 1):
        y, z_, w = r1 - x, c1 - x, r2 - (c1 - x)
        if y < 0 or z_ < 0 or w < 0:
            continue
        p = _hyper(x, y, z_, w)
        if p <= obs * (1 + 1e-9):
            tot += p
    return min(1.0, tot)


# --- load -------------------------------------------------------------------

def load():
    specs = {}
    for t, p in SPECS.items():
        try:
            specs[t] = json.load(open(p))
        except OSError:
            specs[t] = {"arms": {}}
    runs = []
    for task in sorted(ENVDIR):
        edir = os.path.join(SNAPS, ENVDIR[task])
        if not os.path.isdir(edir):
            continue
        for arm in sorted(a for a in os.listdir(edir)
                          if os.path.isdir(os.path.join(edir, a))):
            ap = os.path.join(edir, arm)
            for run in sorted(x for x in os.listdir(ap)
                              if os.path.isdir(os.path.join(ap, x))):
                rp = os.path.join(ap, run)
                r = json.load(open(os.path.join(rp, "reward.json")))
                try:
                    info = json.load(open(os.path.join(rp, "run-info.json")))
                except OSError:
                    info = {}
                inv = r.get("invariants") or {}
                runs.append(OrderedDict(
                    task=task, arm=arm, run=run,
                    arm_code=info.get("arm_recorded", ""),
                    dense=r.get("dense_reward"),
                    passed=int(bool(r.get("terminal_success"))),
                    failed="|".join(k for k, v in inv.items() if not v),
                    signatures="|".join(s for s in SIGNATURES if r.get(s) is True),
                    diagnosis=(r.get("diagnosis") or "")[:400]))
    return runs, specs


def arm_meta(specs, task, arm_code):
    cell = ((specs.get(task, {}).get("arms", {}) or {})
            .get(arm_code, {}) or {}).get("cell", {}) or {}
    kind = ((specs.get(task, {}).get("arms", {}) or {})
            .get(arm_code, {}) or {}).get("kind", "")
    return kind, cell


def main():
    runs, specs = load()
    out = os.path.join(ROOT, "analysis")
    os.makedirs(out, exist_ok=True)

    with open(os.path.join(out, "runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(runs[0].keys()))
        w.writeheader()
        w.writerows(runs)

    by = OrderedDict()
    for r in runs:
        by.setdefault((r["task"], r["arm"]), []).append(r)

    rows = []
    for (task, arm), xs in by.items():
        n = len(xs)
        k = sum(x["passed"] for x in xs)
        lo, hi = wilson(k, n)
        code = next((x["arm_code"] for x in xs if x["arm_code"]), "")
        kind, cell = arm_meta(specs, task, code)
        d = [x["dense"] for x in xs]
        sigs = Counter(s for x in xs for s in x["signatures"].split("|") if s)
        failed = Counter(s for x in xs for s in x["failed"].split("|") if s)
        rows.append(OrderedDict(
            task=task, arm=arm, arm_code=code, kind=kind or "phenomenon",
            family=cell.get("family", ""), event=cell.get("event", ""),
            channel=cell.get("channel", ""), timing=cell.get("timing", ""),
            severity=cell.get("severity", ""),
            recoverability=cell.get("recoverability", ""),
            k=n, passes=k, pass_rate=round(k / n, 3),
            wilson_lo=round(lo, 3), wilson_hi=round(hi, 3),
            pass_hat_k=pass_hat_k(k, n),
            dense_mean=round(sum(d) / n, 3), dense_min=min(d), dense_max=max(d),
            failed_invariants=";".join(f"{a}:{b}" for a, b in failed.most_common()),
            signatures=";".join(f"{a}:{b}" for a, b in sigs.most_common())))
    with open(os.path.join(out, "atlas.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    idx = {(r["task"], r["arm"]): r for r in rows}

    def get(task, arm):
        return idx.get((task, arm))

    CONTRASTS = [
        ("Commitment boundary (task-01)",
         "The identical state change, moved across the point of no return, "
         "against a matched cosmetic control.",
         [("task-01-northgate-clinic", "16-write-coerced--cosmetic-control"),
          ("task-01-northgate-clinic", "15-write-coerced--pre-commit"),
          ("task-01-northgate-clinic", "17-write-coerced--post-commit")],
         ("task-01-northgate-clinic", "15-write-coerced--pre-commit"),
         ("task-01-northgate-clinic", "17-write-coerced--post-commit")),
        ("Announcement channel (task-01)",
         "One requirement revision; only how loudly it announces itself "
         "differs.",
         [("task-01-northgate-clinic", "05-delayed-requirement-correction"),
          ("task-01-northgate-clinic", "06-delayed-requirement-correction--buried"),
          ("task-01-northgate-clinic", "07-requirement-revised--no-notice")],
         ("task-01-northgate-clinic", "05-delayed-requirement-correction"),
         ("task-01-northgate-clinic", "07-requirement-revised--no-notice")),
        ("Where the authority lives (task-01)",
         "The identical policy reissue, published on a page the agent works "
         "in versus an email it has read. Built to fail; did not.",
         [("task-01-northgate-clinic", "10-policy-reissued--wrong-summary"),
          ("task-01-northgate-clinic", "14-policy-reissued--off-path-authority")],
         ("task-01-northgate-clinic", "10-policy-reissued--wrong-summary"),
         ("task-01-northgate-clinic", "14-policy-reissued--off-path-authority")),
        ("Compounding (task-01)",
         "Arms handled solo, fired together.",
         [("task-01-northgate-clinic", "12-compound--merge-and-policy"),
          ("task-01-northgate-clinic", "13-compound--merge-policy-and-api-migration")],
         None, None),
        ("Silent write coercion (task-03)",
         "The same phenomenon on a second environment, with its control.",
         [("task-03-xpedia-hotel-booking", "06-write-coerced--cosmetic-control"),
          ("task-03-xpedia-hotel-booking", "05-write-coerced--room-substituted")],
         ("task-03-xpedia-hotel-booking", "06-write-coerced--cosmetic-control"),
         ("task-03-xpedia-hotel-booking", "05-write-coerced--room-substituted")),
    ]

    L = ["# Controlled contrasts", "",
         "Pass rates with 95% Wilson score intervals; `pass^k` = every trial "
         "succeeded. Two-sided Fisher exact test on the 2x2 pass/fail table "
         "where a pair is named.", ""]
    for title, blurb, arms, a1, a2 in CONTRASTS:
        L += [f"## {title}", "", blurb, "",
              "| arm | timing | k | pass | rate | 95% CI | pass^k | mean dense |",
              "|---|---|---|---|---|---|---|---|"]
        for key in arms:
            r = get(*key)
            if not r:
                L.append(f"| {key[1]} | *(not in archive)* | | | | | | |")
                continue
            L.append(f"| `{r['arm']}` | {r['timing'] or '-'} | {r['k']} | "
                     f"{r['passes']} | {r['pass_rate']:.2f} | "
                     f"[{r['wilson_lo']:.2f}, {r['wilson_hi']:.2f}] | "
                     f"{r['pass_hat_k']:.0f} | {r['dense_mean']:.2f} |")
        if a1 and a2 and get(*a1) and get(*a2):
            x, y = get(*a1), get(*a2)
            p = fisher_exact(x["passes"], x["k"] - x["passes"],
                             y["passes"], y["k"] - y["passes"])
            L += ["", f"Fisher exact, `{x['arm']}` vs `{y['arm']}`: "
                      f"**p = {p:.4f}** "
                      f"({x['passes']}/{x['k']} vs {y['passes']}/{y['k']})."]
        L.append("")
    open(os.path.join(out, "contrasts.md"), "w").write("\n".join(L))

    n_runs = len(runs)
    n_pass = sum(r["passed"] for r in runs)
    tasks = Counter(r["task"] for r in runs)
    fams = Counter(r["family"] for r in rows if r["family"])
    sigs = Counter()
    for r in runs:
        for s in r["signatures"].split("|"):
            if s:
                sigs[s] += 1
    S = ["# Archive summary", "",
         f"- **{n_runs} rollouts**, {n_pass} pass ({n_pass / n_runs:.1%}), "
         f"across **{len(rows)} arms** and **{len(tasks)} environments**",
         f"- runs per environment: " +
         ", ".join(f"{t.split('-')[1]} {c}" for t, c in tasks.items()), "",
         "## Arms by phenomenon family", ""]
    for f_, c in fams.most_common():
        S.append(f"- `{f_}` - {c} arms")
    S += ["", "## Named failure signatures observed", ""]
    for s, c in sigs.most_common():
        S.append(f"- `{s}` - {c} runs")
    S += ["", "## Arms with no pass at any k (reliable failures)", ""]
    for r in rows:
        if r["passes"] == 0:
            S.append(f"- {r['task'].split('-')[1]} `{r['arm']}` "
                     f"({r['passes']}/{r['k']}, mean dense {r['dense_mean']})")
    S += ["", "## Arms that never failed (robustness envelope)", ""]
    for r in rows:
        if r["passes"] == r["k"] and r["k"] >= 3:
            S.append(f"- {r['task'].split('-')[1]} `{r['arm']}` "
                     f"({r['passes']}/{r['k']})")
    open(os.path.join(out, "summary.md"), "w").write("\n".join(S))

    print(f"{n_runs} runs / {len(rows)} arms -> analysis/"
          f"{{runs.csv, atlas.csv, contrasts.md, summary.md}}")


if __name__ == "__main__":
    sys.exit(main())
