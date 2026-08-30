#!/usr/bin/env python3
"""
Compute every number the paper reports, once, into analysis/paper_stats.json.

The figures and the manuscript both read this file. That is the point: a
number cannot appear in a figure and disagree with the same number in a table,
because neither is transcribed by hand.

Two decisions are encoded here rather than in prose, because they change the
headline figures and a reader should be able to see them in the code:

  1. The unit of analysis is the *variant*, not the rollout. Rollouts of one
     variant share a model, a harness, a seed world and a perturbation
     operator, so treating them as independent Bernoulli draws overstates
     precision. The primary test is an exact permutation test over variants.

  2. Three rollouts of `03-slot-taken--permission-revoked` executed before a
     cross-episode mail leak was fixed, and their mailboxes carry 20/23/28
     messages against 3 in a clean episode. They are EXCLUDED from the primary
     analysis. The leak delivered advance notice of events, which would help
     rather than hinder the agent, so excluding them is the conservative
     choice for our own claim. The inclusive numbers are computed too and
     reported as a sensitivity check.
"""
import csv, glob, itertools, json, math, os, re, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis")
ADV = "${ENVOS_ROOT}/cuareplica/output/adversarial"

LEAKED = ("task-01-northgate-clinic", "03-slot-taken--permission-revoked")

FAMILIES = [
    ("F1", "Contested Resource",
     [("task-01-northgate-clinic", "01-slot-taken--email"),
      ("task-03-xpedia-hotel-booking", "01-slot-taken--email"),
      LEAKED,
      ("task-03-xpedia-hotel-booking", "02-slot-taken--void")]),
    ("F2", "Ghost Commit",
     [("task-01-northgate-clinic", "17-write-coerced--post-commit"),
      ("task-03-xpedia-hotel-booking", "05-write-coerced--room-substituted")]),
    ("F3", "Mandate Drift",
     [("task-01-northgate-clinic", "07-requirement-revised--no-notice"),
      ("task-01-northgate-clinic", "09-patient-records-merged--no-notice"),
      ("task-03-xpedia-hotel-booking", "04-policy-reissued--wrong-summary")]),
    ("F4", "Cold-Start Inconsistency",
     [("task-02-xpedia-travel", "02-partial-xapp-commit--coldstart")]),
]
CONTROLS = [("task-01-northgate-clinic", "00-baseline-clean"),
            ("task-02-xpedia-travel", "00-baseline-clean"),
            ("task-03-xpedia-hotel-booking", "00-baseline-clean"),
            ("task-01-northgate-clinic", "16-write-coerced--cosmetic-control"),
            ("task-03-xpedia-hotel-booking", "06-write-coerced--cosmetic-control")]

SUITES = {"task-01-northgate-clinic": ("northgate_replica_001", "tests"),
          "task-02-xpedia-travel": ("hub_xapp_commit_003", "certification"),
          "task-03-xpedia-hotel-booking": ("hub_slot_email_002", "tests")}
ENVLABEL = {"task-01-northgate-clinic": "Clinic",
            "task-02-xpedia-travel": "Travel",
            "task-03-xpedia-hotel-booking": "Hotel"}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _lf(n):
    return math.lgamma(n + 1)


def fisher(a, b, c, d):
    """Two-sided Fisher exact by summing tables no more probable than observed."""
    def h(a, b, c, d):
        n = a + b + c + d
        return math.exp(_lf(a+b)+_lf(c+d)+_lf(a+c)+_lf(b+d)
                        - _lf(n)-_lf(a)-_lf(b)-_lf(c)-_lf(d))
    obs = h(a, b, c, d)
    r1, r2, c1 = a + b, c + d, a + c
    tot = 0.0
    for x in range(0, min(r1, c1) + 1):
        y, z_, w = r1 - x, c1 - x, r2 - (c1 - x)
        if y < 0 or z_ < 0 or w < 0:
            continue
        p = h(x, y, z_, w)
        if p <= obs * (1 + 1e-9):
            tot += p
    return min(1.0, tot)


def permutation(pert_rates, ctrl_rates):
    """Exact one-sided permutation test over variants.

    H0: the perturbed/control label carries no information about a variant's
    pass rate. We enumerate every way of splitting the pooled variants into
    groups of the observed sizes; p is the fraction whose control-minus-
    perturbed difference is at least the observed one. With these group sizes
    the smallest attainable p is 1/C(n, n_ctrl), so we return that floor too.
    """
    allv = list(pert_rates) + list(ctrl_rates)
    nc = len(ctrl_rates)
    obs = (sum(ctrl_rates) / len(ctrl_rates)
           - sum(pert_rates) / len(pert_rates))
    ge = tot = 0
    for comb in itertools.combinations(range(len(allv)), nc):
        cs = [allv[i] for i in comb]
        ps = [allv[i] for i in range(len(allv)) if i not in comb]
        d = sum(cs) / len(cs) - sum(ps) / len(ps)
        tot += 1
        if d >= obs - 1e-12:
            ge += 1
    return {"observed_diff": obs, "n_ge": ge, "n_perm": tot,
            "p": ge / tot, "p_floor": 1.0 / tot,
            "at_floor": ge == 1}


def main():
    runs = list(csv.DictReader(open(os.path.join(OUT, "runs.csv"))))
    agg = {}
    for r in runs:
        k = (r["task"], r["arm"])
        a = agg.setdefault(k, {"n": 0, "passes": 0, "dense": []})
        a["n"] += 1
        a["passes"] += int(r["passed"])
        a["dense"].append(float(r["dense"]))

    S = {"n_rollouts_total": len(runs)}

    # ---- per-variant table -------------------------------------------------
    variants = []
    for fid, fname, arms in FAMILIES:
        for t, arm in arms:
            a = agg.get((t, arm))
            if not a:
                continue
            lo, hi = wilson(a["passes"], a["n"])
            variants.append({
                "family": fid, "family_name": fname,
                "env": ENVLABEL[t], "task": t, "arm": arm,
                "n": a["n"], "passes": a["passes"],
                "rate": a["passes"] / a["n"], "wilson": [lo, hi],
                "mean_dense": statistics.mean(a["dense"]),
                "excluded_leak": (t, arm) == LEAKED})
    ctrl_variants = []
    for t, arm in CONTROLS:
        a = agg.get((t, arm))
        if not a:
            continue
        lo, hi = wilson(a["passes"], a["n"])
        ctrl_variants.append({
            "env": ENVLABEL[t], "task": t, "arm": arm,
            "n": a["n"], "passes": a["passes"],
            "rate": a["passes"] / a["n"], "wilson": [lo, hi],
            "mean_dense": statistics.mean(a["dense"])})
    S["variants"] = variants
    S["control_variants"] = ctrl_variants

    # ---- primary (leak-excluded) and sensitivity (inclusive) ---------------
    for tag, drop in (("primary", True), ("inclusive", False)):
        vs = [v for v in variants if not (drop and v["excluded_leak"])]
        n = sum(v["n"] for v in vs)
        k = sum(v["passes"] for v in vs)
        cn = sum(c["n"] for c in ctrl_variants)
        ck = sum(c["passes"] for c in ctrl_variants)
        fam = {}
        for fid, fname, _ in FAMILIES:
            f = [v for v in vs if v["family"] == fid]
            fn = sum(v["n"] for v in f)
            fk = sum(v["passes"] for v in f)
            lo, hi = wilson(fk, fn)
            fam[fid] = {"name": fname, "n": fn, "passes": fk,
                        "rate": fk / fn if fn else 0.0, "wilson": [lo, hi],
                        "n_variants": len(f),
                        "n_envs": len({v["env"] for v in f}),
                        "fisher_vs_control": fisher(fk, fn - fk, ck, cn - ck)}
        perm = permutation([v["rate"] for v in vs],
                           [c["rate"] for c in ctrl_variants])
        S[tag] = {
            "n_variants": len(vs), "n_rollouts": n, "passes": k,
            "rate": k / n, "wilson": list(wilson(k, n)),
            "control": {"n_variants": len(ctrl_variants), "n_rollouts": cn,
                        "passes": ck, "rate": ck / cn,
                        "wilson": list(wilson(ck, cn))},
            "families": fam,
            "fisher_pooled": fisher(k, n - k, ck, cn - ck),
            "mean_variant_rate": statistics.mean(v["rate"] for v in vs),
            "mean_control_variant_rate":
                statistics.mean(c["rate"] for c in ctrl_variants),
            "permutation": perm}


    # ---- the full corpus, including perturbed variants the agent handled ---
    # Reported because the four families are a post-hoc selection: they are the
    # perturbations this agent failed. Omitting the ones it handled would be
    # selection on the outcome, so the whole denominator is carried here.
    fam_keys = {(t_, a) for _f, _n, arms in FAMILIES for (t_, a) in arms}
    ctrl_keys = set(CONTROLS)
    handled = []
    for (t_, arm), a in sorted(agg.items()):
        if (t_, arm) in fam_keys or (t_, arm) in ctrl_keys:
            continue
        lo, hi = wilson(a["passes"], a["n"])
        handled.append({"env": ENVLABEL[t_], "task": t_, "arm": arm,
                        "n": a["n"], "passes": a["passes"],
                        "rate": a["passes"] / a["n"], "wilson": [lo, hi]})
    hn = sum(h["n"] for h in handled); hk = sum(h["passes"] for h in handled)
    S["handled_perturbed"] = {
        "n_variants": len(handled), "n_rollouts": hn, "passes": hk,
        "rate": hk / hn if hn else 0.0, "variants": handled}
    S["corpus"] = {
        "n_variants": len(handled) + len(variants) + len(ctrl_variants),
        "n_rollouts": sum(a["n"] for a in agg.values()),
        "control": {"n_variants": len(ctrl_variants),
                    "n_rollouts": sum(c["n"] for c in ctrl_variants)},
        "perturbed": {"n_variants": len(handled) + len(variants),
                      "n_rollouts": hn + sum(v["n"] for v in variants)}}


    # ---- the UNSELECTED comparison: all perturbed variants vs controls -----
    # This is the honest inferential test. The four families were identified
    # by looking at which perturbations the agent failed, so comparing them
    # against controls is circular. Comparing *every* perturbation against
    # controls is not, and is reported as the primary inferential result even
    # though it does not reach significance.
    allp = ([v for v in variants if not v["excluded_leak"]]
            + S["handled_perturbed"]["variants"])
    an = sum(v["n"] for v in allp); ak = sum(v["passes"] for v in allp)
    cn2 = sum(c["n"] for c in ctrl_variants)
    ck2 = sum(c["passes"] for c in ctrl_variants)
    S["unselected"] = {
        "n_variants": len(allp), "n_rollouts": an, "passes": ak,
        "rate": ak / an,
        "mean_variant_rate": statistics.mean(v["rate"] for v in allp),
        "mean_control_variant_rate":
            statistics.mean(c["rate"] for c in ctrl_variants),
        "fisher": fisher(ak, an - ak, ck2, cn2 - ck2),
        "permutation": permutation([v["rate"] for v in allp],
                                   [c["rate"] for c in ctrl_variants])}

    # ---- the irreversibility experiment -----------------------------------
    B = [("16-write-coerced--cosmetic-control", "Cosmetic control", "same event, same value"),
         ("15-write-coerced--pre-commit", "Pre-commitment", "fires at review"),
         ("17-write-coerced--post-commit", "Post-commitment", "fires at submit")]
    bd = []
    for arm, label, sub in B:
        a = agg.get(("task-01-northgate-clinic", arm))
        if not a:
            continue
        lo, hi = wilson(a["passes"], a["n"])
        bd.append({"arm": arm, "label": label, "sub": sub, "n": a["n"],
                   "passes": a["passes"], "rate": a["passes"] / a["n"],
                   "wilson": [lo, hi]})
    pre = next(x for x in bd if x["arm"].startswith("15"))
    post = next(x for x in bd if x["arm"].startswith("17"))
    S["boundary"] = {
        "rows": bd,
        "fisher_pre_vs_post": fisher(pre["passes"], pre["n"] - pre["passes"],
                                     post["passes"], post["n"] - post["passes"])}

    # ---- certification size, measured not asserted -------------------------
    suites = {}
    total_checks = total_suites = 0
    for task, (env, sub) in SUITES.items():
        files = sorted(glob.glob(os.path.join(ADV, env, sub, "*.py")))
        per = {}
        for f in files:
            src = open(f).read()
            n = len(re.findall(r"(?<!def )\bcheck\(", src))
            if n:
                per[os.path.basename(f)] = n
        suites[ENVLABEL[task]] = {"env_dir": env, "suites": per,
                                  "n_suites": len(per),
                                  "n_checks": sum(per.values())}
        total_checks += sum(per.values())
        total_suites += len(per)
    S["certification"] = {"by_env": suites, "total_checks": total_checks,
                          "total_suites": total_suites}

    # ---- cost --------------------------------------------------------------
    durs, per_env, acts = [], {}, []
    for r in runs:
        d = os.path.join(ROOT, r["task"], r["arm"], r["run"])
        s, e = os.path.join(d, "start.epoch"), os.path.join(d, "end.epoch")
        if os.path.exists(s) and os.path.exists(e):
            try:
                v = float(open(e).read()) - float(open(s).read())
                if 0 < v < 7200:
                    durs.append(v)
                    per_env.setdefault(ENVLABEL[r["task"]], []).append(v)
            except Exception:
                pass
        rj = os.path.join(d, "reward.json")
        if os.path.exists(rj):
            try:
                a = (json.load(open(rj)).get("metrics") or {}).get("agent_actions")
                if a:
                    acts.append(a)
            except Exception:
                pass
    S["cost"] = {
        "n_timed": len(durs),
        "median_min": statistics.median(durs) / 60 if durs else None,
        "total_hours": sum(durs) / 3600 if durs else None,
        "by_env": {k: {"n": len(v), "median_min": statistics.median(v) / 60}
                   for k, v in sorted(per_env.items())},
        "actions": {"n": len(acts),
                    "median": statistics.median(acts) if acts else None,
                    "min": min(acts) if acts else None,
                    "max": max(acts) if acts else None}}

    # ---- the one failing control ------------------------------------------
    for r in runs:
        if (r["task"], r["arm"]) in CONTROLS and int(r["passed"]) == 0:
            S["control_failure"] = {
                "env": ENVLABEL[r["task"]], "arm": r["arm"], "run": r["run"],
                "dense": float(r["dense"]), "failed": r["failed"],
                "diagnosis": r["diagnosis"]}

    with open(os.path.join(OUT, "paper_stats.json"), "w") as f:
        json.dump(S, f, indent=2)

    p = S["primary"]
    print(f"rollouts {S['n_rollouts_total']} | primary variants "
          f"{p['n_variants']} ({p['passes']}/{p['n_rollouts']}) vs control "
          f"{p['control']['passes']}/{p['control']['n_rollouts']}")
    print(f"permutation p = {p['permutation']['p']:.4f} "
          f"(floor {p['permutation']['p_floor']:.4f}, "
          f"at floor: {p['permutation']['at_floor']})")
    print(f"inclusive permutation p = "
          f"{S['inclusive']['permutation']['p']:.4f}")
    print(f"certification {S['certification']['total_checks']} checks / "
          f"{S['certification']['total_suites']} suites")
    print(f"cost {S['cost']['total_hours']:.1f} h, median "
          f"{S['cost']['median_min']:.1f} min")


if __name__ == "__main__":
    sys.exit(main())
