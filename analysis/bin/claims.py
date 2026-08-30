#!/usr/bin/env python3
"""
Which claims in this archive are actually supported, and which are not.

The atlas tabulates outcomes. It does not say which of them survive contact
with a reviewer. This grades every claim the archive makes into one of four
buckets, with the test, the power, and - where a claim is not yet supported -
the exact k that would fix it.

Grades
  CONCLUSIVE      a controlled contrast, clean control, two-sided Fisher p<0.05
  SUGGESTIVE      the pattern is there, the test is underpowered
  NULL-UNDERPOWERED
                  no difference observed, but k is far too small to claim
                  equivalence. Reportable ONLY as "we predicted X and failed to
                  reproduce it", never as "X has no effect"
  NOT USABLE      a confound makes the comparison uninterpretable

Why the distinction matters: at k=3 per arm the most extreme possible result -
every trial passing on one side, every trial failing on the other - gives
Fisher p = 0.10. An archive full of 3/3-vs-0/3 contrasts contains no
significant comparisons at all, however striking the fractions look.
"""
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis")


def _lf(n):
    return math.lgamma(n + 1)


def _h(a, b, c, d):
    n = a + b + c + d
    return math.exp(_lf(a+b) + _lf(c+d) + _lf(a+c) + _lf(b+d)
                    - _lf(n) - _lf(a) - _lf(b) - _lf(c) - _lf(d))


def fisher(a, b, c, d):
    obs = _h(a, b, c, d)
    tot, r1, r2, c1 = 0.0, a + b, c + d, a + c
    for x in range(0, min(r1, c1) + 1):
        y, z, w = r1 - x, c1 - x, r2 - (c1 - x)
        if y < 0 or z < 0 or w < 0:
            continue
        p = _h(x, y, z, w)
        if p <= obs * (1 + 1e-9):
            tot += p
    return min(1.0, tot)


def k_needed(alpha=0.05, cap=12):
    """Smallest per-arm k at which a perfect separation reaches significance."""
    for k in range(2, cap + 1):
        if fisher(k, 0, 0, k) < alpha:
            return k
    return None


def load():
    with open(os.path.join(OUT, "atlas.csv")) as f:
        return {(r["task"], r["arm"]): r for r in csv.DictReader(f)}


T1, T2, T3 = ("task-01-northgate-clinic", "task-02-xpedia-travel",
              "task-03-xpedia-hotel-booking")

# claim: (id, headline, treatment, comparator, control_arm_or_None, kind)
CLAIMS = [
    ("C1", "Moving one state change across the commitment boundary flips the "
           "outcome (silent write coercion, task-01)",
     (T1, "17-write-coerced--post-commit"),
     (T1, "15-write-coerced--pre-commit"),
     (T1, "16-write-coerced--cosmetic-control"), "contrast"),
    ("C2", "Removing the notification - not lowering its salience - is what "
           "breaks the requirement correction (task-01)",
     (T1, "07-requirement-revised--no-notice"),
     (T1, "05-delayed-requirement-correction"), None, "contrast"),
    ("C2b", "Burying the same correction costs latency, not verdicts",
     (T1, "06-delayed-requirement-correction--buried"),
     (T1, "05-delayed-requirement-correction"), None, "equivalence"),
    ("C3", "A wrong lower-authority summary displaces the source it "
           "summarises (task-03 policy reissue)",
     (T3, "04-policy-reissued--wrong-summary"),
     (T3, "00-baseline-clean"), None, "contrast"),
    ("C4", "Silent write coercion replicates on a second environment "
           "(task-03 room substitution)",
     (T3, "05-write-coerced--room-substituted"),
     (T3, "06-write-coerced--cosmetic-control"),
     (T3, "06-write-coerced--cosmetic-control"), "contrast"),
    ("C5", "Where the authority is published does NOT change the outcome "
           "(off-path matched pair) - our prediction, falsified",
     (T1, "14-policy-reissued--off-path-authority"),
     (T1, "10-policy-reissued--wrong-summary"), None, "equivalence"),
    ("C6", "Compounding phenomena the agent passes solo does not degrade it",
     (T1, "13-compound--merge-policy-and-api-migration"),
     (T1, "10-policy-reissued--wrong-summary"), None, "equivalence"),
    ("C7", "The agent handles a withdrawn tool capability (task-01)",
     (T1, "11-calendar-api-migrated"),
     (T1, "00-baseline-clean"), None, "descriptive"),
    ("C8", "The agent handles permission revocation (task-01)",
     (T1, "02-permission-revoked"),
     (T1, "00-baseline-clean"), None, "descriptive"),
]


def grade(c, atlas):
    cid, head, tk, ck, ctrl, kind = c
    t, cm = atlas.get(tk), atlas.get(ck)
    if not t or not cm:
        return dict(id=cid, head=head, grade="NOT USABLE",
                    why="an arm in this comparison is not in the archive",
                    detail="", fix="")
    tp, tn = int(t["passes"]), int(t["k"])
    cp, cn = int(cm["passes"]), int(cm["k"])
    p = fisher(cp, cn - cp, tp, tn - tp)
    detail = (f"{cm['arm']} {cp}/{cn} vs {t['arm']} {tp}/{tn} · "
              f"Fisher p={p:.4f}")

    # a comparator with k=1 is not a control, it is an anecdote
    if cn < 3:
        return dict(id=cid, head=head, grade="NOT USABLE",
                    why=f"the comparator has k={cn}; a single run cannot "
                        f"establish that the task is normally passed",
                    detail=detail,
                    fix=f"run {cm['arm']} to k>=5")

    # a control that itself failed breaks attribution
    if ctrl:
        cc = atlas.get(ctrl)
        if cc and int(cc["passes"]) < int(cc["k"]):
            return dict(id=cid, head=head, grade="NOT USABLE",
                        why=f"the matched control failed "
                            f"({cc['passes']}/{cc['k']}); with control and "
                            f"treatment both failing the phenomenon cannot be "
                            f"credited with the failure",
                        detail=detail,
                        fix=f"establish the clean baseline for "
                            f"{cc['task'].split('-')[1]} at k>=5, then re-run "
                            f"the control")

    if kind in ("equivalence", "descriptive"):
        # no difference observed. Equivalence needs power we do not have.
        n_eq = 100
        return dict(id=cid, head=head, grade="NULL-UNDERPOWERED",
                    why="no difference observed, but k is far too small to "
                        "support an equivalence claim; report as 'predicted "
                        "and failed to reproduce', not as 'no effect'",
                    detail=detail,
                    fix=f"an equivalence claim within +-20pp needs ~n={n_eq} "
                        f"per arm - out of scope; keep as a falsification")

    if p < 0.05:
        return dict(id=cid, head=head, grade="CONCLUSIVE",
                    why="controlled contrast, clean control, significant",
                    detail=detail, fix="")
    return dict(id=cid, head=head, grade="SUGGESTIVE",
                why=f"the pattern is complete separation but k is too small: "
                    f"p={p:.3f}",
                detail=detail,
                fix=f"k>={k_needed()} per arm makes a perfect separation "
                    f"significant (p={fisher(k_needed(),0,0,k_needed()):.4f})")


def main():
    atlas = load()
    rows = [grade(c, atlas) for c in CLAIMS]
    order = {"CONCLUSIVE": 0, "SUGGESTIVE": 1, "NULL-UNDERPOWERED": 2,
             "NOT USABLE": 3}
    rows.sort(key=lambda r: order[r["grade"]])

    L = ["# What is submittable, and what actually concludes something", "",
         "Generated by `bin/claims.py`. Every claim the archive makes, graded "
         "by whether the evidence supports it.", "",
         "## Power, first", "",
         "At k=3 per arm the **most extreme possible outcome** - every trial "
         "passing on one side, every trial failing on the other - gives a "
         "two-sided Fisher p of **0.10**. It is not significant. A benchmark "
         "of 3/3-versus-0/3 contrasts contains no significant comparisons, "
         "however clean the fractions look.", "",
         "| k per arm | p for a perfect separation |", "|---|---|"]
    for k in (3, 4, 5, 6, 8, 10):
        L.append(f"| {k} | {fisher(k,0,0,k):.5f}{' **<0.05**' if fisher(k,0,0,k)<0.05 else ''} |")
    L += ["", f"**Minimum viable k = {k_needed()}.**", "", "## Verdict by claim", ""]
    for g in ("CONCLUSIVE", "SUGGESTIVE", "NULL-UNDERPOWERED", "NOT USABLE"):
        sel = [r for r in rows if r["grade"] == g]
        if not sel:
            continue
        L += [f"### {g} ({len(sel)})", ""]
        for r in sel:
            L += [f"**{r['id']} — {r['head']}**", "",
                  f"- evidence: {r['detail']}",
                  f"- {r['why']}"]
            if r["fix"]:
                L.append(f"- to fix: {r['fix']}")
            L.append("")
    counts = {g: len([r for r in rows if r["grade"] == g]) for g in order}
    L += ["## Bottom line", "",
          f"- **{counts['CONCLUSIVE']} claim(s) presently conclusive.**",
          f"- {counts['SUGGESTIVE']} suggestive - complete separation, "
          f"underpowered, fixable by raising k.",
          f"- {counts['NULL-UNDERPOWERED']} null results that are honest "
          f"falsifications of our own predictions but cannot be stated as "
          f"'no effect'.",
          f"- {counts['NOT USABLE']} not usable until a comparator or control "
          f"is repaired.", ""]
    open(os.path.join(OUT, "claims.md"), "w").write("\n".join(L))
    for r in rows:
        print(f"{r['grade']:18s} {r['id']:4s} {r['detail']}")
    print(f"\n-> analysis/claims.md   ({counts})")


if __name__ == "__main__":
    sys.exit(main())
