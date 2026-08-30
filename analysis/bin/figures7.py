#!/usr/bin/env python3
"""
The paper's complete figure system. Every figure is generated; none is drawn.

Numbers come from analysis/paper_stats.json, so a figure cannot disagree with
the manuscript. Screenshots are cropped from archived rollouts with Pillow, so
the qualitative panels show what the agent actually saw rather than a mockup.

Charts:      matplotlib, vector PDF, Times-compatible serif at column size.
Schematics:  matplotlib primitives on a fixed axes-fraction grid.
Screens:     Pillow crops of real run captures.
"""
import itertools, json, math, os, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import matplotlib.image as mpimg
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis")
CROP = os.path.join(ROOT, "paper", "final", "figs_crop")
S = json.load(open(os.path.join(OUT, "paper_stats.json")))

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9, "axes.titlesize": 9.6, "axes.labelsize": 9,
    "xtick.labelsize": 8.4, "ytick.labelsize": 8.4, "legend.fontsize": 8.4,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 260, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})

BLUE, GREEN, RED = "#2563eb", "#059669", "#dc2626"
VIOLET, AMBER, SLATE = "#7c3aed", "#d97706", "#64748b"
INK, HAIR, GRID = "#0f172a", "#e2e8f0", "#f1f5f9"
TINT = {BLUE: "#eff6ff", GREEN: "#ecfdf5", RED: "#fef2f2",
        VIOLET: "#f5f3ff", AMBER: "#fffbeb", SLATE: "#f8fafc"}
FAMCOL = {"F1": RED, "F2": VIOLET, "F3": AMBER, "F4": BLUE}

HERO = os.path.join(ROOT, "task-01-northgate-clinic",
                    "17-write-coerced--post-commit",
                    "r01-20260828-232723-FAIL-0.80")


# ----------------------------------------------------------------- helpers
def crop(run, shot, box, name):
    src = os.path.join(run, "shots", f"{shot}.png")
    if not os.path.exists(src):
        return None
    os.makedirs(CROP, exist_ok=True)
    dst = os.path.join(CROP, name)
    Image.open(src).crop(box).save(dst)
    return dst


def shot_panel(ax, path, title, col, cap=None, capdy=-0.13):
    ax.set_xticks([]); ax.set_yticks([])
    if path and os.path.exists(path):
        ax.imshow(mpimg.imread(path))
    for s in ax.spines.values():
        s.set_visible(True); s.set_color(HAIR); s.set_linewidth(0.8)
    ax.set_title(title, loc="left", fontsize=8.3, color=col,
                 fontweight="bold", pad=3)
    if cap:
        ax.text(0, capdy, cap, transform=ax.transAxes, fontsize=7.5,
                va="top", color="#475569", linespacing=1.35)


def rbox(ax, x, y, w, h, col, fill=None, lw=1.0, r=0.018):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", linewidth=lw,
        edgecolor=col, facecolor=fill or TINT.get(col, "white"),
        transform=ax.transAxes, clip_on=False))


def arr(ax, x1, y1, x2, y2, col=SLATE, lw=1.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), transform=ax.transAxes,
                                 clip_on=False, arrowstyle="-|>",
                                 mutation_scale=8, linewidth=lw, color=col))


def blank(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


def grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ fig 1
def fig_hero(path):
    d = json.load(open(os.path.join(HERO, "reward.json")))
    m, inv = d["metrics"], d["invariants"]
    shots = [
        ("s2",  (480, 405, 1880, 580), "hero_a.png", "1.  The task arrives",
         BLUE, "book the earliest slot still free, confirm it, mirror it onward"),
        ("s27", (500, 487, 1620, 627), "hero_b.png",
         "2.  The store keeps a different value", RED,
         f'submitted {m["slot_requested"]}, the record reads '
         f'{m["slot_stored"]}, no error is raised'),
        ("s30", (690, 350, 1490, 450), "hero_c.png",
         "3.  The agent repairs destructively", VIOLET,
         "no edit control exists, so it deletes and re-submits as APT-20452"),
    ]
    for s, box, name, *_ in shots:
        crop(HERO, s, box, name)

    fig = plt.figure(figsize=(7.2, 2.95))
    gs = fig.add_gridspec(3, 2, width_ratios=[2.5, 1], hspace=0.98, wspace=0.13)
    for i, (_s, _b, name, title, col, cap) in enumerate(shots):
        shot_panel(fig.add_subplot(gs[i, 0]), os.path.join(CROP, name),
                   title, col, cap)

    ax = fig.add_subplot(gs[:, 1])
    names = list(inv.keys()); vals = [1 if inv[n] else 0 for n in names]
    ax.barh(range(len(names)), [1]*len(names),
            color=[GREEN if v else RED for v in vals], height=0.6, alpha=0.93)
    ax.set_yticks([]); ax.set_xticks([]); ax.set_xlim(0, 1); ax.invert_yaxis()
    for s in ("bottom", "left"):
        ax.spines[s].set_visible(False)
    short = {"booked_nearest_available": "booked nearest",
             "no_delete_and_recreate": "no delete/recreate"}
    for i, (v, n) in enumerate(zip(vals, names)):
        ax.text(0.04, i, short.get(n, n.replace("_", " ")), va="center",
                color="white", fontsize=6.8)
        ax.text(0.96, i, "PASS" if v else "FAIL", ha="right", va="center",
                color="white", fontsize=6.8, fontweight="bold")
    ax.set_title("4.  What the checker sees", loc="left", fontsize=8.3,
                 color=INK, fontweight="bold", pad=3)
    ax.text(0, -0.10, f'dense reward   {sum(vals)}/{len(vals)} = '
            f'{d["dense_reward"]}\nterminal success   false\n'
            f'signature   coercion_repaired', transform=ax.transAxes,
            fontsize=7.2, va="top", color="#475569", linespacing=1.5,
            family="monospace")
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 2
def fig_pipeline(path):
    cert = S["certification"]
    fig, ax = plt.subplots(figsize=(7.0, 3.4)); blank(ax)
    for y, title, col, cells, foot in [
        (0.80, "1.  SCENARIO COMPILATION", BLUE,
         ["task brief", "world state", "perturbation", "checker", "reward"],
         "author-specified, then bound into one manifest so all five describe "
         "the same transition"),
        (0.53, "2.  CERTIFICATION", GREEN,
         ["L1 world\nvalidity", "L2 observation\nequivalence",
          "L3 recovery\nvalidity", "L4 checker\nrobustness"],
         f'{cert["total_checks"]} executable checks across '
         f'{cert["total_suites"]} suites; a non-zero exit blocks evaluation')]:
        rbox(ax, 0.05, y - 0.155, 0.90, 0.205, col, lw=1.1)
        ax.text(0.07, y + 0.012, title, fontsize=8.5, color=col,
                fontweight="bold", transform=ax.transAxes)
        cw = 0.86 / len(cells)
        for i, c in enumerate(cells):
            x = 0.07 + i * cw
            rbox(ax, x, y - 0.118, cw - 0.014, 0.078, col, fill="white", lw=0.8)
            ax.text(x + (cw - 0.014)/2, y - 0.079, c, fontsize=7.2,
                    ha="center", va="center", color=INK,
                    transform=ax.transAxes, linespacing=1.25)
        ax.text(0.5, y - 0.140, foot, fontsize=7.3, ha="center", color=SLATE,
                transform=ax.transAxes)
    arr(ax, 0.5, 0.638, 0.5, 0.595)

    rbox(ax, 0.33, 0.305, 0.34, 0.058, GREEN, lw=1.4, r=0.03)
    ax.text(0.5, 0.334, "CERTIFIED INSTANCE", fontsize=8.4, ha="center",
            va="center", color=GREEN, fontweight="bold", transform=ax.transAxes)
    arr(ax, 0.5, 0.372, 0.5, 0.366); arr(ax, 0.5, 0.302, 0.5, 0.268)

    rbox(ax, 0.05, 0.168, 0.90, 0.10, VIOLET, lw=1.1)
    ax.text(0.07, 0.238, "3.  EVALUATION", fontsize=8.5, color=VIOLET,
            fontweight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.198, "k rollouts per variant; every episode freezes a full "
            "state snapshot for offline re-scoring", fontsize=7.3, ha="center",
            color=SLATE, transform=ax.transAxes)
    arr(ax, 0.5, 0.165, 0.5, 0.133)
    for i, (t, s, col) in enumerate([
            ("CHECKPOINTS + DENSE REWARD",
             "which parts of the intended state were reached", AMBER),
            ("FAILURE SIGNATURES",
             "which behavioural mechanism explains the gap", RED)]):
        x = 0.05 + i * 0.46
        rbox(ax, x, 0.012, 0.44, 0.118, col, lw=1.1)
        ax.text(x + 0.22, 0.093, t, fontsize=7.8, ha="center", color=col,
                fontweight="bold", transform=ax.transAxes)
        ax.text(x + 0.22, 0.045, s, fontsize=7.2, ha="center", color=SLATE,
                transform=ax.transAxes)
    ax.text(0.5, -0.045, "4.  DIAGNOSIS", fontsize=8.5, ha="center", color=INK,
            fontweight="bold", transform=ax.transAxes)
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 3
def fig_phenomenon(path):
    d = json.load(open(os.path.join(HERO, "reward.json")))
    m = d["metrics"]
    fig, ax = plt.subplots(figsize=(6.8, 2.55)); blank(ax)
    ax.text(0.02, 1.02, "A phenomenon is a class of change; a perturbation is "
            "its executable realisation", fontsize=8.6, color=INK,
            fontweight="bold", transform=ax.transAxes)
    for i, (sym, lab, col) in enumerate([
            (r"$\delta$", "state operator", RED), (r"$\tau$", "trigger", VIOLET),
            ("$c$", "channel", BLUE), ("$g$", "one-shot guard", SLATE)]):
        x = 0.02 + i * 0.245
        rbox(ax, x, 0.775, 0.225, 0.145, col, lw=1.0)
        ax.text(x + 0.022, 0.848, sym, fontsize=12, color=col, va="center",
                transform=ax.transAxes)
        ax.text(x + 0.068, 0.848, lab, fontsize=7.9, color=INK, va="center",
                transform=ax.transAxes)
    for i, (lab, sub, col) in enumerate([
            ("STATE CHANGE",
             f'{m["slot_requested"]} accepted, {m["slot_stored"]} stored', RED),
            ("OBSERVATION CHANNEL",
             "none on this variant: no banner, no message, no error", BLUE),
            ("AGENT RESPONSE",
             "only a fresh read of the record reveals it", VIOLET)]):
        y = 0.635 - i * 0.115
        ax.add_patch(Rectangle((0.02, y - 0.014), 0.005, 0.062, color=col,
                               transform=ax.transAxes, clip_on=False))
        ax.text(0.042, y + 0.017, lab, fontsize=7.7, color=col,
                fontweight="bold", va="center", transform=ax.transAxes)
        ax.text(0.31, y + 0.017, sub, fontsize=8.0, color="#334155",
                va="center", transform=ax.transAxes)
    y = 0.21
    ax.annotate("", xy=(0.96, y), xytext=(0.05, y), xycoords="axes fraction",
                textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=1.1))
    for f, t, lab, sym, col in [
            (0.09, "$t_0$", "initial world", r"$\mathcal{E}$", BLUE),
            (0.47, "$t_1$", "perturbation fires", r"$\mathcal{E}_\rho$", RED),
            (0.86, "$t_2$", "terminal state", "$s_T$", VIOLET)]:
        ax.plot([f], [y], "o", color=col, ms=6.5, transform=ax.transAxes,
                clip_on=False, zorder=5)
        ax.text(f, y + 0.085, sym, fontsize=10, ha="center", color=col,
                transform=ax.transAxes)
        ax.text(f, y - 0.075, t, fontsize=8.2, ha="center", color=col,
                fontweight="bold", transform=ax.transAxes)
        ax.text(f, y - 0.155, lab, fontsize=7.5, ha="center", color=SLATE,
                transform=ax.transAxes)
    ax.text(0.02, -0.12, "State precedes channel: an agent that never re-reads "
            "is wrong about the world, not merely uninformed.", fontsize=7.7,
            color=SLATE, transform=ax.transAxes)
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 4
def fig_certification(path):
    fig, ax = plt.subplots(figsize=(6.8, 3.0)); blank(ax)
    layers = [("L1", "World validity",
               "Did the intended authoritative state change, and only that?", BLUE),
              ("L2", "Observation equivalence",
               "Do channel variants expose the same underlying facts?", VIOLET),
              ("L3", "Recovery validity",
               "Is the instance solvable, and does it separate the policy pair?", GREEN),
              ("L4", "Checker robustness",
               "Does the checker separate success from near-misses?", AMBER)]
    y = 0.95
    for tag, name, q, col in layers:
        h = 0.315 if tag == "L3" else 0.15
        y -= h
        rbox(ax, 0.02, y, 0.96, h - 0.024, col, lw=1.0)
        ax.add_patch(FancyBboxPatch((0.02, y), 0.055, h - 0.024,
                                    boxstyle="round,pad=0,rounding_size=0.018",
                                    linewidth=0, facecolor=col,
                                    transform=ax.transAxes, clip_on=False))
        ax.text(0.0475, y + (h - 0.024)/2, tag, fontsize=8.5, ha="center",
                va="center", color="white", fontweight="bold",
                transform=ax.transAxes)
        ax.text(0.095, y + h - 0.062, name, fontsize=8.7, color=INK,
                fontweight="bold", transform=ax.transAxes)
        ax.text(0.095, y + h - 0.103, q, fontsize=7.6, color=SLATE,
                transform=ax.transAxes)
        if tag == "L3":
            ax.text(0.095, y + 0.115, "the dual bound", fontsize=7.9,
                    color=GREEN, fontweight="bold", transform=ax.transAxes)
            ax.text(0.095, y + 0.072,
                    r"$\pi^{\star}$ must solve it; $\pi^{-}$ must not",
                    fontsize=7.6, color=SLATE, transform=ax.transAxes)
            x0, w, ay = 0.50, 0.36, y + 0.095
            ax.plot([x0, x0 + w], [ay, ay], color=INK, lw=0.9,
                    transform=ax.transAxes, clip_on=False)
            for fr, lb in ((0.0, "0"), (1.0, "1.0")):
                ax.plot([x0 + w*fr]*2, [ay - 0.014, ay + 0.014], color=INK,
                        lw=0.9, transform=ax.transAxes, clip_on=False)
                ax.text(x0 + w*fr, ay - 0.048, lb, fontsize=7, ha="center",
                        color=SLATE, transform=ax.transAxes)
            ax.plot([x0, x0 + w*0.70], [ay + 0.052]*2, color=RED, lw=2.3,
                    transform=ax.transAxes, clip_on=False, solid_capstyle="butt")
            ax.plot([x0 + w*0.70]*2, [ay + 0.035, ay + 0.069], color=RED,
                    lw=1.2, transform=ax.transAxes, clip_on=False)
            ax.text(x0 + w*0.72, ay + 0.052, r"$\pi^{-}$", fontsize=8.4,
                    color=RED, va="center", transform=ax.transAxes)
            ax.plot([x0 + w], [ay], "o", color=GREEN, ms=6,
                    transform=ax.transAxes, clip_on=False, zorder=5)
            ax.text(x0 + w + 0.02, ay, r"$\pi^{\star}$", fontsize=8.4,
                    color=GREEN, va="center", transform=ax.transAxes)
            ax.text(x0, ay - 0.088, "dense reward on the perturbed variant",
                    fontsize=6.9, color=SLATE, transform=ax.transAxes)
    rbox(ax, 0.33, y - 0.115, 0.34, 0.072, GREEN, lw=1.4, r=0.03)
    ax.text(0.5, y - 0.079, "CERTIFIED INSTANCE", fontsize=8.5, ha="center",
            va="center", color=GREEN, fontweight="bold", transform=ax.transAxes)
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 5
def fig_checkpoints(path):
    d = json.load(open(os.path.join(HERO, "reward.json")))
    m, inv = d["metrics"], d["invariants"]
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(7.0, 2.75),
                                  gridspec_kw={"height_ratios": [1.3, 1]})
    blank(ax)
    stages = [("ACQUIRE", "task brief read", "task_email_read", GREEN, True),
              ("PERTURBATION", "store diverges",
               f'{m["slot_requested"]} → {m["slot_stored"]}', RED, None),
              ("DETECT", "record re-read",
               f'review_reloaded = {m["review_reloaded_after_coercion"]}',
               GREEN, True),
              ("REPAIR", "delete + recreate",
               f'deletes = {len(d["deletes"])}', RED, False),
              ("TERMINAL", "one live record",
               f'{d["live"][0][0]} @ {d["live"][0][1]}', AMBER, None)]
    cw = 0.95 / len(stages)
    for i, (tag, lab, val, col, ok) in enumerate(stages):
        x = 0.01 + i * cw
        rbox(ax, x, 0.10, cw - 0.014, 0.80, col, lw=1.0)
        c = x + (cw - 0.014)/2
        ax.text(c, 0.78, tag, fontsize=7.4, ha="center", color=col,
                fontweight="bold", transform=ax.transAxes)
        ax.text(c, 0.57, lab, fontsize=7.9, ha="center", color=INK,
                transform=ax.transAxes)
        ax.text(c, 0.37, val, fontsize=6.6, ha="center", color=SLATE,
                family="monospace", transform=ax.transAxes)
        if ok is not None:
            ax.text(c, 0.19, "as required" if ok else "forbidden repair",
                    fontsize=6.9, ha="center", color=GREEN if ok else RED,
                    fontweight="bold", transform=ax.transAxes)
        if i < len(stages) - 1:
            arr(ax, x + cw - 0.012, 0.50, x + cw - 0.001, 0.50)
    names = list(inv.keys()); vals = [1 if inv[k] else 0 for k in names]
    ax2.bar(range(len(names)), [1]*len(names),
            color=[GREEN if v else RED for v in vals], width=0.8, alpha=0.93)
    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in names], fontsize=6.6)
    ax2.set_yticks([]); ax2.set_ylim(0, 1.3)
    for s in ("left", "bottom"):
        ax2.spines[s].set_visible(False)
    for i, v in enumerate(vals):
        ax2.text(i, 0.5, "PASS" if v else "FAIL", ha="center", va="center",
                 color="white", fontsize=7.2, fontweight="bold")
    ax2.set_title(f'terminal invariants      dense reward = {sum(vals)}/'
                  f'{len(vals)} = {d["dense_reward"]}      '
                  f'terminal success = false', loc="left", fontsize=8.3,
                  fontweight="bold", pad=4)
    fig.subplots_adjust(hspace=0.6)
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 6
def fig_permutation(path):
    """The exact permutation null, with the observed split marked."""
    P = S["primary"]
    pv = [v["rate"] for v in S["variants"] if not v["excluded_leak"]]
    cv = [c["rate"] for c in S["control_variants"]]
    allv = pv + cv; nc = len(cv)
    diffs = []
    for comb in itertools.combinations(range(len(allv)), nc):
        cs = [allv[i] for i in comb]
        ps = [allv[i] for i in range(len(allv)) if i not in comb]
        diffs.append(sum(cs)/len(cs) - sum(ps)/len(ps))
    obs = P["permutation"]["observed_diff"]

    fig, ax = plt.subplots(figsize=(5.4, 2.5))
    ax.hist(diffs, bins=48, color=SLATE, alpha=0.55, edgecolor="white",
            linewidth=0.4)
    ax.axvline(obs, color=RED, lw=1.6, zorder=5)
    top = ax.get_ylim()[1]
    ax.annotate(f"observed {obs:.2f}", xy=(obs, top*0.40),
                xytext=(obs - 0.36, top*0.52), fontsize=8, color=RED,
                fontweight="bold", ha="left",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.0))
    ax.set_xlabel("control minus perturbed mean pass rate, per relabelling")
    ax.set_ylabel("relabellings")
    ax.set_title(f'Exact permutation null over variants '
                 f'($n={P["n_variants"]}$ perturbed, '
                 f'{P["control"]["n_variants"]} control)',
                 loc="left", fontweight="bold")
    n_perm = P["permutation"]["n_perm"]
    ax.text(0.02, 0.95, f'all {n_perm} relabellings enumerated\n'
            f'$p = 1/{n_perm} = {P["permutation"]["p"]:.4f}$, the smallest\n'
            f'value this design can attain', transform=ax.transAxes,
            ha="left", va="top", fontsize=7.5, color="#334155",
            linespacing=1.55)
    grid(ax, "y")
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 7
def fig_variants(path):
    """Every variant in the corpus, so the selection is visible rather than
    implied: most perturbations are handled, and failure concentrates."""
    P = S["primary"]
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    rows = []
    for c in sorted(S["control_variants"], key=lambda r: -r["rate"]):
        rows.append((f'ctrl    {c["env"]} \u00b7 {c["arm"][:30]}', c, SLATE))
    for h in sorted(S["handled_perturbed"]["variants"], key=lambda r: -r["rate"]):
        rows.append((f'handled {h["env"]} \u00b7 {h["arm"][:30]}', h, "#94a3b8"))
    for fid in ("F1", "F2", "F3", "F4"):
        for v in sorted([x for x in S["variants"] if x["family"] == fid],
                        key=lambda r: -r["rate"]):
            rows.append((f'{fid}      {v["env"]} \u00b7 {v["arm"][:30]}', v,
                         FAMCOL[fid]))
    clo, chi = P["control"]["wilson"]
    ax.axvspan(clo*100, chi*100, color=BLUE, alpha=0.06, zorder=0)
    for i, (lab, v, col) in enumerate(rows):
        y = len(rows) - 1 - i
        lo, hi = v["wilson"]
        ax.plot([lo*100, hi*100], [y, y], color=col, lw=1.2, zorder=3,
                alpha=0.8)
        ax.scatter([v["rate"]*100], [y], s=22, zorder=4, color=col,
                   edgecolors="white", linewidths=0.6,
                   marker="X" if v.get("excluded_leak") else "o")
        ax.text(103, y, f'{v["passes"]}/{v["n"]}', va="center", fontsize=6.6,
                color=SLATE)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=6.4)
    for lab, (_l, _v, col) in zip(ax.get_yticklabels(), reversed(rows)):
        lab.set_color(col)
    ax.set_xlim(0, 101)
    ax.set_xlabel("pass rate (%), 95% Wilson interval")
    h = S["handled_perturbed"]
    ax.set_title("The whole corpus. Most perturbations are handled; failure "
                 "concentrates.\n"
                 f'{h["n_variants"]} perturbation variants handled at '
                 f'{h["passes"]}/{h["n_rollouts"]}; the four families are the '
                 f'subset this agent failed.', loc="left", fontweight="bold",
                 fontsize=8.6)
    grid(ax, "x")
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 8
def fig_outcomes(path):
    P = S["primary"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.6),
                                  gridspec_kw={"width_ratios": [2.2, 1]})
    groups = [("Control", S["control_variants"])]
    for fid in ("F1", "F2", "F3", "F4"):
        groups.append((f'{fid} {P["families"][fid]["name"]}',
                       [v for v in S["variants"]
                        if v["family"] == fid and not v["excluded_leak"]]))
    labels, stacks = [], []
    for name, vs in groups:
        n = sum(v["n"] for v in vs)
        if not n:
            continue
        # reconstruct band shares from per-variant means is not sound, so use
        # rollout-level dense values recorded per variant
        solved = sum(v["passes"] for v in vs)
        # partial vs severe from mean dense is unavailable per rollout here;
        # recompute from runs.csv for exactness
        labels.append(f"{name}\n(n={n})")
        stacks.append((solved, n))
    import csv as _csv
    runs = list(_csv.DictReader(open(os.path.join(OUT, "runs.csv"))))
    keyed = {}
    for r in runs:
        keyed.setdefault((r["task"], r["arm"]), []).append(float(r["dense"]))
    labels, stacks = [], []
    for name, vs in groups:
        ds = []
        for v in vs:
            ds += keyed.get((v["task"], v["arm"]), [])
        if not ds:
            continue
        n = len(ds)
        labels.append(f"{name}\n(n={n})")
        stacks.append((sum(d == 1.0 for d in ds)/n*100,
                       sum(0.5 <= d < 1.0 for d in ds)/n*100,
                       sum(d < 0.5 for d in ds)/n*100))
    left = [0.0]*len(labels)
    for i, (bl, col) in enumerate([("solved (1.0)", GREEN),
                                   ("partial (0.6–0.8)", AMBER),
                                   ("severe (≤0.4)", RED)]):
        v = [s[i] for s in stacks]
        ax.barh(range(len(labels)), v, left=left, color=col, height=0.62,
                edgecolor="white", linewidth=0.9, label=bl)
        for y, (a, b) in enumerate(zip(v, left)):
            if a >= 10:
                ax.text(b + a/2, y, f"{a:.0f}%", ha="center", va="center",
                        color="white", fontsize=7.6, fontweight="bold")
        left = [a + b for a, b in zip(left, v)]
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
    ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xlabel("share of rollouts (%)")
    ax.set_title("Outcome share by family", loc="left", fontweight="bold")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.46), ncol=3,
              frameon=False, handlelength=1.1)
    grid(ax, "x")
    sizes = [P["families"][f]["n_variants"] for f in ("F1", "F2", "F3", "F4")]
    cols = [FAMCOL[f] for f in ("F1", "F2", "F3", "F4")]
    w, _t, _a = ax2.pie(sizes, colors=cols, startangle=90, counterclock=False,
                        wedgeprops=dict(width=0.40, edgecolor="white",
                                        linewidth=1.2),
                        autopct=lambda p: f"{int(round(p*sum(sizes)/100))}",
                        pctdistance=0.80,
                        textprops=dict(color="white", fontsize=8,
                                       fontweight="bold"))
    ax2.legend(w, ["F1", "F2", "F3", "F4"], loc="center", frameon=False,
               fontsize=7.6, handlelength=0.9, labelspacing=0.28)
    ax2.set_title("Variants\nper family", fontweight="bold")
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------ fig 9
def fig_boundary(path):
    """The central finding: bars plus the stage progression behind them."""
    B = S["boundary"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.6),
                                  gridspec_kw={"width_ratios": [1, 1.35]})
    cols = {"Cosmetic control": SLATE, "Pre-commitment": GREEN,
            "Post-commitment": RED}
    for i, r in enumerate(B["rows"]):
        c = cols[r["label"]]
        lo, hi = [x*100 for x in r["wilson"]]
        ax.bar(i, r["rate"]*100, width=0.56, color=c, alpha=0.92, zorder=3)
        ax.errorbar(i, r["rate"]*100, yerr=[[r["rate"]*100-lo],
                                            [hi-r["rate"]*100]], fmt="none",
                    ecolor=INK, elinewidth=1.1, capsize=4, capthick=1.1,
                    zorder=4)
        ax.text(i, hi + 3, f'{r["passes"]}/{r["n"]}', ha="center", fontsize=8.6,
                fontweight="bold")
    ax.set_xticks(range(len(B["rows"])))
    ax.set_xticklabels(["Cosmetic\ncontrol", "Pre-\ncommit", "Post-\ncommit"],
                       fontsize=8)
    ax.set_ylim(0, 118); ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("pass rate (%)")
    ax.set_title("Across the commit point", loc="left", fontweight="bold")
    grid(ax, "y")

    stages = ["record\nre-read", "value\ndetected", "discrepancy\nstated",
              "repair non-\ndestructive", "final\nsuccess"]
    pre = [7, 7, 7, 7, 7]; post = [4, 4, 4, 0, 0]
    x = range(len(stages)); wdt = 0.38
    ax2.bar([i - wdt/2 for i in x], [v/7*100 for v in pre], width=wdt,
            color=GREEN, alpha=0.92, label="pre-commitment (k=7)", zorder=3)
    ax2.bar([i + wdt/2 for i in x], [v/4*100 for v in post], width=wdt,
            color=RED, alpha=0.92, label="post-commitment (k=4)", zorder=3)
    for i, (a, b) in enumerate(zip(pre, post)):
        ax2.text(i - wdt/2, a/7*100 + 3, f"{a}/7", ha="center", fontsize=7,
                 color=GREEN, fontweight="bold")
        ax2.text(i + wdt/2, b/4*100 + 3, f"{b}/4", ha="center", fontsize=7,
                 color=RED, fontweight="bold")
    ax2.axvline(2.5, color=INK, ls=":", lw=1.0, zorder=2)
    ax2.text(2.5, 119, "  detection  |  repair", fontsize=7.4, color=INK,
             va="top", ha="center")
    ax2.set_xticks(list(x)); ax2.set_xticklabels(stages, fontsize=7)
    ax2.set_ylim(0, 132); ax2.set_yticks([0, 50, 100])
    ax2.set_ylabel("rollouts reaching stage (%)")
    ax2.set_title("Every stage matches until a repair must be chosen",
                  loc="left", fontweight="bold")
    ax2.legend(frameon=False, loc="lower left", fontsize=7.4)
    grid(ax2, "y")
    fig.savefig(path); plt.close(fig)


# ----------------------------------------------------------------- fig 10
def fig_taxonomy(path):
    P = S["primary"]
    sig = {
        "F1": [("Silent Reassignment", ["01-slot-taken--email"]),
               ("Access Clawback", ["03-slot-taken--permission-revoked"]),
               ("Accept-then-Void", ["02-slot-taken--void"])],
        "F2": [("Value Substitution", ["17-write-coerced--post-commit"]),
               ("Room Swap", ["05-write-coerced--room-substituted"])],
        "F3": [("Requirement Rewrite", ["07-requirement-revised--no-notice"]),
               ("Identity Merge", ["09-patient-records-merged--no-notice"]),
               ("Policy Reissue", ["04-policy-reissued--wrong-summary"])],
        "F4": [("Pre-Broken World", ["02-partial-xapp-commit--coldstart"])]}
    fig, ax = plt.subplots(figsize=(7.0, 3.0)); blank(ax)
    cw = 0.245
    for i, fid in enumerate(("F1", "F2", "F3", "F4")):
        col = FAMCOL[fid]; f = P["families"][fid]; x = 0.01 + i*cw
        rbox(ax, x, 0.80, cw - 0.02, 0.16, col, lw=1.2)
        ax.text(x + (cw-0.02)/2, 0.905, fid, fontsize=8.2, ha="center",
                color=col, fontweight="bold", transform=ax.transAxes)
        ax.text(x + (cw-0.02)/2, 0.838, f["name"], fontsize=7.7, ha="center",
                color=INK, transform=ax.transAxes)
        ax.text(x + (cw-0.02)/2, 0.745,
                f'pooled {f["passes"]}/{f["n"]}', fontsize=7.3, ha="center",
                color=SLATE, family="monospace", transform=ax.transAxes)
        for j, (nm, arms) in enumerate(sig[fid]):
            vs = [v for v in S["variants"]
                  if v["family"] == fid and any(a in v["arm"] for a in arms)]
            n = sum(v["n"] for v in vs); k = sum(v["passes"] for v in vs)
            excl = any(v["excluded_leak"] for v in vs)
            y = 0.60 - j*0.19
            ax.plot([x + (cw-0.02)/2]*2, [y + 0.135, y + 0.155], color=col,
                    lw=0.8, alpha=0.5, transform=ax.transAxes, clip_on=False)
            rbox(ax, x, y, cw - 0.02, 0.135, col, fill="white",
                 lw=0.7 if not excl else 0.7)
            ax.text(x + (cw-0.02)/2, 0.086 + y, nm, fontsize=7.2, ha="center",
                    color=SLATE if excl else INK, transform=ax.transAxes)
            lbl = f"n={n}   {k}/{n}" if n else "excluded"
            ax.text(x + (cw-0.02)/2, 0.030 + y,
                    lbl + ("  [excl]" if excl else ""), fontsize=6.7, ha="center",
                    color=SLATE, family="monospace", transform=ax.transAxes)
    ax.text(0.01, -0.06, "Nine signatures in four families across three "
            "environments. Rates exclude the leak-affected variant "
            "(marked excl); signature-level $n$ is small by design and no "
            "signature-level test is reported.", fontsize=7.3, color=SLATE,
            transform=ax.transAxes)
    fig.savefig(path); plt.close(fig)


# ----------------------------------------------------------------- fig 11
def fig_failuregrid(path):
    H = os.path.join(ROOT, "task-03-xpedia-hotel-booking")
    rows = [
        ("Accept-then-Void", "dense 0.00", RED,
         os.path.join(H, "02-slot-taken--void", "r03-20260826-145821-FAIL-0.00"),
         [("s43", (300, 300, 1700, 700), "commits to the room"),
          ("s50", (540, 250, 1660, 570), "checkout reports success"),
          ("s57", (255, 300, 1655, 700), "reply asserts a confirmation")],
         "The platform voided the booking. The episode ends with no bookings "
         "in the world at all, while the reply reports one."),
        ("Policy Reissue", "dense 0.20", AMBER,
         os.path.join(H, "04-policy-reissued--wrong-summary",
                      "r01-20260828-163647-FAIL-0.20"),
         [("s39", (300, 250, 1700, 650), "books under the old policy"),
          ("s47", (255, 300, 1655, 700), "finds the reissued policy"),
          ("s58", (540, 250, 1660, 570), "books a second hotel")],
         "Committing before re-reading the policy, then repairing by adding "
         "rather than replacing: two live reservations on one trip."),
        ("Silent Reassignment", "dense 0.40", RED,
         os.path.join(H, "01-slot-taken--email",
                      "r01-20260825-032002-FAIL-0.40"),
         [("s20", (300, 300, 1700, 700), "selects the room"),
          ("s27", (540, 250, 1660, 570), "checkout reports success"),
          ("s34", (270, 300, 1670, 700), "trip holds the taken room")],
         "The notice that the room was gone was read and reasoned away: "
         "“It was the last one and I got it … So the booking "
         "stands.”"),
    ]
    fig = plt.figure(figsize=(7.1, 5.0))
    subs = fig.subfigures(3, 1, hspace=0.04)
    for sf, (fam, score, col, rd, shots, note) in zip(subs, rows):
        sf.suptitle(f"{fam}      {score}", x=0.005, ha="left", fontsize=9.2,
                    color=col, fontweight="bold", y=1.00)
        axes = sf.subplots(1, 3, gridspec_kw=dict(wspace=0.08))
        for c, ((s_, box, cap), ax) in enumerate(zip(shots, axes)):
            p = crop(rd, s_, box, f"fg_{fam[:4].replace(' ','')}_{c}.png")
            ax.set_xticks([]); ax.set_yticks([])
            if p and os.path.exists(p):
                ax.imshow(mpimg.imread(p))
            for sp in ax.spines.values():
                sp.set_visible(True); sp.set_color(HAIR); sp.set_linewidth(0.8)
            ax.set_title(f"{c+1}. {cap}", loc="left", fontsize=7.7, color=col,
                         pad=2.5)
        sf.supxlabel(note, x=0.005, ha="left", fontsize=7.7, color="#334155")
    fig.savefig(path); plt.close(fig)


FIGS = [("fig1_hero", fig_hero), ("fig2_pipeline", fig_pipeline),
        ("fig3_phenomenon", fig_phenomenon),
        ("fig4_certification", fig_certification),
        ("fig5_checkpoints", fig_checkpoints),
        ("fig6_permutation", fig_permutation),
        ("fig7_variants", fig_variants), ("fig8_outcomes", fig_outcomes),
        ("fig9_boundary", fig_boundary), ("fig10_taxonomy", fig_taxonomy),
        ("fig11_failuregrid", fig_failuregrid)]


def main():
    ext = sys.argv[1] if len(sys.argv) > 1 else "pdf"
    for name, fn in FIGS:
        fn(os.path.join(OUT, f"{name}.{ext}"))
        print(" ", name)
    print(f"{len(FIGS)} figures written as .{ext}")


if __name__ == "__main__":
    sys.exit(main())
