#!/usr/bin/env python3
"""
The test the thesis actually needs: does phenomenon injection degrade a
frontier agent, pooled across arms?

Arm-by-arm contrasts at k=3 are hopeless (a perfect separation gives p=0.10).
But the claim in the EnvOS proposal is not about any single arm - it is about
INJECTION AS A METHOD. That claim pools, and pooling is where the power is:
~10 control runs against ~78 injected runs is a comparison with real n.

Three tests, weakest assumption first:
  1. binary pass/fail, control vs injected            - Fisher exact
  2. dense reward (0..1, 6 levels), control vs injected - Mann-Whitney U,
     normal approximation with tie correction. Uses the graded signal the
     benchmark already produces instead of throwing it away at the threshold.
  3. per-family breakdown, so the pooled number is never quoted without the
     heterogeneity behind it.

Also reports the YIELD of the taxonomy: of the phenomena built from it, what
fraction actually break the agent. That is the number the proposal is really
asking for.
"""
import csv
import math
import os
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "analysis")

# Arms that are NOT an injected phenomenon: the clean capability controls and
# the matched cosmetic controls (same event, same audit, same value).
CONTROL_ARMS = {
    ("task-01-northgate-clinic", "00-baseline-clean"),
    ("task-02-xpedia-travel", "00-baseline-clean"),
    ("task-03-xpedia-hotel-booking", "00-baseline-clean"),
    ("task-01-northgate-clinic", "16-write-coerced--cosmetic-control"),
    ("task-03-xpedia-hotel-booking", "06-write-coerced--cosmetic-control"),
}
# Arms whose own REPORT says they partly score the environment (invariants the
# phenomenon made unreachable). Excluded from the headline, reported apart.
CONFOUNDED = {
    ("task-01-northgate-clinic", "01-slot-taken--email"),
    ("task-03-xpedia-hotel-booking", "01-slot-taken--email"),
}


def _lf(n):
    return math.lgamma(n + 1)


def _h(a, b, c, d):
    n = a + b + c + d
    return math.exp(_lf(a+b)+_lf(c+d)+_lf(a+c)+_lf(b+d)
                    - _lf(n)-_lf(a)-_lf(b)-_lf(c)-_lf(d))


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


def mannwhitney(a, b):
    """Two-sided U with a normal approximation and tie correction. Returns
    (U, z, p, rank-biserial effect size)."""
    n1, n2 = len(a), len(b)
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i, ties = [0.0] * len(allv), 0, 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j + 2) / 2.0
        t = j - i + 1
        ties += t ** 3 - t
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    r1 = sum(r for r, (_, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    n = n1 + n2
    mu = n1 * n2 / 2.0
    sd = math.sqrt(n1 * n2 / 12.0 * ((n + 1) - ties / (n * (n - 1))))
    if sd == 0:
        return u1, 0.0, 1.0, 0.0
    z = (u1 - mu) / sd
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    rbc = 2 * u1 / (n1 * n2) - 1          # rank-biserial correlation
    return u1, z, min(1.0, p), rbc


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def main():
    with open(os.path.join(OUT, "runs.csv")) as f:
        runs = list(csv.DictReader(f))
    with open(os.path.join(OUT, "atlas.csv")) as f:
        atlas = {(r["task"], r["arm"]): r for r in csv.DictReader(f)}

    ctrl, phen, conf = [], [], []
    for r in runs:
        key = (r["task"], r["arm"])
        (ctrl if key in CONTROL_ARMS else
         conf if key in CONFOUNDED else phen).append(r)

    def split(xs):
        p = sum(int(x["passed"]) for x in xs)
        return p, len(xs) - p, len(xs), [float(x["dense"]) for x in xs]

    cp, cf, cn, cd = split(ctrl)
    pp, pf, pn, pd = split(phen)
    p_fish = fisher(cp, cf, pp, pf)
    u, z, p_mw, rbc = mannwhitney(cd, pd)
    clo, chi = wilson(cp, cn)
    plo, phi = wilson(pp, pn)

    L = ["# Does injection break the agent? The pooled test", "",
         "Arm-by-arm contrasts at k=3 cannot reach significance - a perfect "
         "separation gives Fisher p=0.10. But the claim under test is about "
         "**injection as a method**, and that claim pools. Two arms excluded "
         "and reported separately: those whose own REPORT states that the "
         "phenomenon made an invariant unreachable, so they partly score the "
         "environment.", "",
         "## 1. Task success", "",
         "| condition | runs | pass | rate | 95% CI |", "|---|---|---|---|---|",
         f"| **control** (clean + matched cosmetic) | {cn} | {cp} | "
         f"{cp/cn:.2f} | [{clo:.2f}, {chi:.2f}] |",
         f"| **injected phenomenon** | {pn} | {pp} | {pp/pn:.2f} | "
         f"[{plo:.2f}, {phi:.2f}] |", "",
         f"Two-sided Fisher exact: **p = {p_fish:.5f}**  "
         f"(absolute drop {100*(cp/cn - pp/pn):.0f} percentage points).", "",
         "## 2. Dense reward", "",
         "The benchmark scores `passes/5`, so thresholding to pass/fail throws "
         "away four fifths of the signal. Mann-Whitney U on the graded score "
         "keeps it.", "",
         f"| condition | n | mean | median |", "|---|---|---|---|",
         f"| control | {len(cd)} | {sum(cd)/len(cd):.3f} | "
         f"{sorted(cd)[len(cd)//2]:.2f} |",
         f"| injected | {len(pd)} | {sum(pd)/len(pd):.3f} | "
         f"{sorted(pd)[len(pd)//2]:.2f} |", "",
         f"U = {u:.0f}, z = {z:.2f}, **p = {p_mw:.5f}**, "
         f"rank-biserial r = {rbc:.2f}.", ""]

    if conf:
        kp, kf, kn, kd = split(conf)
        L += ["## Excluded (arms that partly score the environment)", "",
              f"{kn} runs across {len(CONFOUNDED)} arms, {kp} pass. Their "
              f"REPORTs document invariants the phenomenon made unreachable; "
              f"including them would inflate the effect.", ""]

    L += ["## 3. Where the effect lives - by phenomenon family", "",
          "The pooled number must never be quoted without this. Injection is "
          "not uniformly harmful; the families differ sharply, and that "
          "difference is the actual finding.", "",
          "| family | arms | runs | pass rate |", "|---|---|---|---|"]
    fam = OrderedDict()
    for r in phen:
        f_ = atlas.get((r["task"], r["arm"]), {}).get("family", "?") or "?"
        fam.setdefault(f_, []).append(r)
    for f_, xs in sorted(fam.items(), key=lambda kv: sum(
            int(x["passed"]) for x in kv[1]) / len(kv[1])):
        a = len({(x["task"], x["arm"]) for x in xs})
        p_ = sum(int(x["passed"]) for x in xs)
        L.append(f"| `{f_}` | {a} | {len(xs)} | {p_}/{len(xs)} "
                 f"({p_/len(xs):.0%}) |")

    arms = {}
    for r in phen:
        arms.setdefault((r["task"], r["arm"]), []).append(int(r["passed"]))
    dead = [k for k, v in arms.items() if sum(v) == 0]
    mixed = [k for k, v in arms.items() if 0 < sum(v) < len(v)]
    solid = [k for k, v in arms.items() if sum(v) == len(v)]
    L += ["", "## 4. Yield of the taxonomy", "",
          "Of the phenomena built from the proposal's categories, how many "
          "actually break the agent:", "",
          f"- **{len(dead)} of {len(arms)} arms fail at every trial** "
          f"({len(dead)/len(arms):.0%})",
          f"- {len(mixed)} are unreliable (some trials fail) "
          f"({len(mixed)/len(arms):.0%})",
          f"- {len(solid)} are handled at every trial "
          f"({len(solid)/len(arms):.0%})", "",
          f"So **{(len(dead)+len(mixed))/len(arms):.0%} of injected phenomena "
          f"degrade the agent at least sometimes**, against a control "
          f"condition at {cp}/{cn}.", "",
          "### Arms that never pass", ""]
    for t, a in sorted(dead):
        r = atlas.get((t, a), {})
        L.append(f"- `{t.split('-')[1]}/{a}` - {r.get('family','?')} · "
                 f"{r.get('passes')}/{r.get('k')} · mean dense "
                 f"{r.get('dense_mean')}")
    L += ["", "### Arms that are unreliable", ""]
    for t, a in sorted(mixed):
        r = atlas.get((t, a), {})
        L.append(f"- `{t.split('-')[1]}/{a}` - {r.get('passes')}/{r.get('k')}")
    L += ["", "## Caveat that must ship with these numbers", "",
          "The arms are **not a random sample of possible phenomena**. They "
          "were built from a fixed taxonomy, and several were iterated after "
          "an early version passed. The pooled figure is therefore a statement "
          "about *the yield of this taxonomy under deliberate search*, not "
          "about phenomena in general - which is what the proposal asks for, "
          "and is how it should be worded.", ""]
    open(os.path.join(OUT, "pooled.md"), "w").write("\n".join(L))

    print(f"control  {cp}/{cn} ({cp/cn:.0%})   injected {pp}/{pn} ({pp/pn:.0%})")
    print(f"Fisher p = {p_fish:.6f}")
    print(f"Mann-Whitney on dense reward: z={z:.2f}, p={p_mw:.6f}, r={rbc:.2f}")
    print(f"yield: {len(dead)} always-fail, {len(mixed)} unreliable, "
          f"{len(solid)} handled  (of {len(arms)} arms)")
    print("-> analysis/pooled.md")


if __name__ == "__main__":
    sys.exit(main())
