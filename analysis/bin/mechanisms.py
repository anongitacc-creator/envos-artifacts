#!/usr/bin/env python3
"""
Group arms by the MECHANISM they implement, not by the taxonomy label.

The declared family comes from the atlas spec and follows the source
taxonomy's categories. That is right for describing the benchmark and wrong
for testing it: the same trigger - "the resource you selected was taken by
another actor" - appears in this archive under three different family labels,
because each arm compounds it with something else. Splitting those arms across
families scatters the evidence and no group reaches significance.

Grouping by trigger instead pools arms that share a causal mechanism while
differing in environment, entity and application - which is the
generalisation a reviewer actually wants, and is where the power is.

Every group is tested against the pooled control condition (clean baselines +
matched cosmetic controls). Groups containing a confounded arm are reported
twice: with and without it.
"""
import csv, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis")
CONTROLS = {("task-01-northgate-clinic", "00-baseline-clean"),
            ("task-02-xpedia-travel", "00-baseline-clean"),
            ("task-03-xpedia-hotel-booking", "00-baseline-clean"),
            ("task-01-northgate-clinic", "16-write-coerced--cosmetic-control"),
            ("task-03-xpedia-hotel-booking", "06-write-coerced--cosmetic-control")}
CONFOUNDED = {("task-01-northgate-clinic", "01-slot-taken--email"),
              ("task-03-xpedia-hotel-booking", "01-slot-taken--email")}

GROUPS = [
 ("M1", "Selected resource taken by another actor",
  "The slot or room the agent chose is booked by someone else mid-episode. "
  "Implemented in two environments and compounded three different ways "
  "(email notice; then a permission revocation; then an accept-then-void).",
  [("task-01-northgate-clinic", "01-slot-taken--email"),
   ("task-03-xpedia-hotel-booking", "01-slot-taken--email"),
   ("task-01-northgate-clinic", "03-slot-taken--permission-revoked"),
   ("task-03-xpedia-hotel-booking", "02-slot-taken--void")]),
 ("M2", "Write accepted, value silently altered",
  "The commit succeeds and the store keeps a different value. No error, no "
  "banner; the confirmation surface renders what was chosen.",
  [("task-01-northgate-clinic", "17-write-coerced--post-commit"),
   ("task-03-xpedia-hotel-booking", "05-write-coerced--room-substituted")]),
 ("M3", "Authoritative fact revised with no notification",
  "A requirement, an identity or a rule is changed in place. Nothing arrives; "
  "nothing becomes unread; the surface holding the truth looks unchanged.",
  [("task-01-northgate-clinic", "07-requirement-revised--no-notice"),
   ("task-01-northgate-clinic", "09-patient-records-merged--no-notice"),
   ("task-03-xpedia-hotel-booking", "04-policy-reissued--wrong-summary")]),
 ("M4", "World already inconsistent at step 0",
  "The cross-app commit fired before the agent's first action, so there is no "
  "temporal cue to attach the inconsistency to.",
  [("task-02-xpedia-travel", "02-partial-xapp-commit--coldstart")]),
]


def _lf(n): return math.lgamma(n + 1)
def _h(a, b, c, d):
    n = a + b + c + d
    return math.exp(_lf(a+b)+_lf(c+d)+_lf(a+c)+_lf(b+d)
                    - _lf(n)-_lf(a)-_lf(b)-_lf(c)-_lf(d))
def fisher(a, b, c, d):
    obs = _h(a, b, c, d); tot = 0.0; r1, r2, c1 = a+b, c+d, a+c
    for x in range(0, min(r1, c1) + 1):
        y, z, w = r1-x, c1-x, r2-(c1-x)
        if y < 0 or z < 0 or w < 0: continue
        p = _h(x, y, z, w)
        if p <= obs * (1 + 1e-9): tot += p
    return min(1.0, tot)
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p, d = k/n, 1 + z*z/n
    c = (p + z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return max(0.0, c-h), min(1.0, c+h)


def tally(runs, keys):
    n = p = 0; tasks = set(); dense = []
    for r in runs:
        if (r["task"], r["arm"]) in keys:
            n += 1; p += int(r["passed"]); tasks.add(r["task"][5:7])
            dense.append(float(r["dense"]))
    return n, p, tasks, dense


def main():
    runs = list(csv.DictReader(open(os.path.join(OUT, "runs.csv"))))
    cn = cp = 0
    for r in runs:
        if (r["task"], r["arm"]) in CONTROLS:
            cn += 1; cp += int(r["passed"])

    L = ["# Failing mechanisms, pooled across environments", "",
         f"Pooled control: **{cp}/{cn} pass ({cp/cn:.0%})** — clean baselines "
         f"plus matched cosmetic controls. Two-sided Fisher exact against "
         f"that control.", "",
         "| id | mechanism | arms | envs | runs | pass | rate | 95% CI | mean dense | p |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    allkeys = []
    for gid, name, _desc, keys in GROUPS:
        allkeys += keys
        n, p, tasks, dense = tally(runs, keys)
        pv = fisher(cp, cn - cp, p, n - p); lo, hi = wilson(p, n)
        flag = " ⚑" if any(k in CONFOUNDED for k in keys) else ""
        L.append(f"| **{gid}** | {name}{flag} | {len(keys)} | {len(tasks)} | "
                 f"{n} | {p} | {p/n:.0%} | [{lo:.2f}, {hi:.2f}] | "
                 f"{sum(dense)/len(dense):.2f} | **{pv:.4f}** |")
    n, p, tasks, dense = tally(runs, allkeys)
    pv = fisher(cp, cn - cp, p, n - p); lo, hi = wilson(p, n)
    L.append(f"| — | **all four pooled** | {len(allkeys)} | {len(tasks)} | "
             f"{n} | {p} | {p/n:.0%} | [{lo:.2f}, {hi:.2f}] | "
             f"{sum(dense)/len(dense):.2f} | **{pv:.6f}** |")
    L += ["", "⚑ M1 contains two arms whose REPORTs document invariants the "
          "phenomenon made unreachable. Reported both ways:", ""]
    keys = GROUPS[0][3]
    for lab, ks in (("with those arms", keys),
                    ("without them", [k for k in keys if k not in CONFOUNDED])):
        n, p, _t, _d = tally(runs, ks)
        L.append(f"- M1 {lab}: {p}/{n}, p = "
                 f"{fisher(cp, cn-cp, p, n-p):.4f}")
    L += ["", "## What each mechanism is", ""]
    for gid, name, desc, keys in GROUPS:
        n, p, tasks, _d = tally(runs, keys)
        L += [f"**{gid} — {name}** ({p}/{n} across {len(tasks)} environment"
              f"{'s' if len(tasks) > 1 else ''})", "", desc, "",
              "Arms: " + ", ".join(f"`{t[5:7]}/{a}`" for t, a in keys), ""]
    open(os.path.join(OUT, "mechanisms.md"), "w").write("\n".join(L))
    print(f"control {cp}/{cn} -> analysis/mechanisms.md")


if __name__ == "__main__":
    sys.exit(main())
