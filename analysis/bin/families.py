#!/usr/bin/env python3
"""
Family-level pooling: the unit of evidence a workshop reviewer can accept.

Individual arms sit at k=1..7, where even a perfect separation is often not
significant. But a PHENOMENON FAMILY replicated across independent
environments pools legitimately - the arms share a mechanism and differ in
substrate, which is exactly the generalisation a reviewer wants. Pooling also
rescues families whose individual arms are confounded: an arm whose invariants
the phenomenon made unreachable cannot carry a rate on its own, but its
presence in a family that fails across three independent implementations is
still informative, provided the confound is stated.

Each family is tested against the pooled CONTROL condition (clean baselines +
matched cosmetic controls, n=12, 11 pass).
"""
import csv, math, os, sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis")
CONTROLS = {("task-01-northgate-clinic", "00-baseline-clean"),
            ("task-02-xpedia-travel", "00-baseline-clean"),
            ("task-03-xpedia-hotel-booking", "00-baseline-clean"),
            ("task-01-northgate-clinic", "16-write-coerced--cosmetic-control"),
            ("task-03-xpedia-hotel-booking", "06-write-coerced--cosmetic-control")}
# arms whose REPORT documents invariants the phenomenon made unreachable
CONFOUNDED = {("task-01-northgate-clinic", "01-slot-taken--email"),
              ("task-03-xpedia-hotel-booking", "01-slot-taken--email")}
# families as the paper groups them (an arm may be a compound of two)
def fam_of(r):
    f = r["family"]
    if "+" in f:
        return "compound (multiple families)"
    return f or "?"

def _lf(n): return math.lgamma(n+1)
def _h(a,b,c,d):
    n=a+b+c+d
    return math.exp(_lf(a+b)+_lf(c+d)+_lf(a+c)+_lf(b+d)-_lf(n)-_lf(a)-_lf(b)-_lf(c)-_lf(d))
def fisher(a,b,c,d):
    obs=_h(a,b,c,d); tot=0.0; r1,r2,c1=a+b,c+d,a+c
    for x in range(0,min(r1,c1)+1):
        y,z,w=r1-x,c1-x,r2-(c1-x)
        if y<0 or z<0 or w<0: continue
        p=_h(x,y,z,w)
        if p<=obs*(1+1e-9): tot+=p
    return min(1.0,tot)
def wilson(k,n,z=1.96):
    if n==0: return (0.0,1.0)
    p,d=k/n,1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0.0,c-h),min(1.0,c+h)

def main():
    rows=list(csv.DictReader(open(os.path.join(OUT,"atlas.csv"))))
    runs=list(csv.DictReader(open(os.path.join(OUT,"runs.csv"))))
    arm_of={(r["task"],r["arm"]):r for r in rows}

    cp=cn=0
    for r in runs:
        if (r["task"],r["arm"]) in CONTROLS:
            cn+=1; cp+=int(r["passed"])

    fams=OrderedDict()
    for r in runs:
        key=(r["task"],r["arm"])
        if key in CONTROLS: continue
        a=arm_of.get(key,{})
        f=fam_of(a)
        d=fams.setdefault(f,{"n":0,"p":0,"arms":set(),"tasks":set(),
                             "conf":set(),"dense":[]})
        d["n"]+=1; d["p"]+=int(r["passed"]); d["arms"].add(key[1])
        d["tasks"].add(key[0][5:7]); d["dense"].append(float(r["dense"]))
        if key in CONFOUNDED: d["conf"].add(key[1])

    out=[]
    for f,d in fams.items():
        p_=fisher(cp,cn-cp,d["p"],d["n"]-d["p"])
        lo,hi=wilson(d["p"],d["n"])
        out.append(dict(family=f,arms=len(d["arms"]),tasks=len(d["tasks"]),
                        task_list=",".join(sorted(d["tasks"])),
                        n=d["n"],passes=d["p"],rate=d["p"]/d["n"],
                        lo=lo,hi=hi,p=p_,
                        dense=sum(d["dense"])/len(d["dense"]),
                        confounded=len(d["conf"])))
    out.sort(key=lambda x:(x["rate"],-x["n"]))

    L=["# Phenomenon families vs the pooled control","",
       f"Pooled control condition: **{cp}/{cn} pass** "
       f"(clean baselines + matched cosmetic controls). Each family is the "
       f"pooled outcome of every arm implementing that mechanism, across "
       f"however many independent environments it was built in. Two-sided "
       f"Fisher exact against the control.","",
       "| family | arms | envs | runs | pass | rate | 95% CI | mean dense | p vs control |",
       "|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        star=" ⚑" if r["confounded"] else ""
        sig="**" if r["p"]<0.05 else ""
        L.append(f"| `{r['family']}`{star} | {r['arms']} | {r['tasks']} "
                 f"({r['task_list']}) | {r['n']} | {r['passes']} | "
                 f"{r['rate']:.0%} | [{r['lo']:.2f}, {r['hi']:.2f}] | "
                 f"{r['dense']:.2f} | {sig}{r['p']:.4f}{sig} |")
    L+=["","⚑ = contains an arm whose REPORT documents invariants the "
        "phenomenon made unreachable; the family is still informative but the "
        "confound must be stated wherever the number is used.",""]
    L+=["## Families that significantly degrade the agent",""]
    any_=False
    for r in out:
        if r["p"]<0.05:
            any_=True
            L.append(f"- **`{r['family']}`** — {r['passes']}/{r['n']} across "
                     f"{r['arms']} arms in {r['tasks']} environment(s), "
                     f"p = {r['p']:.4f}")
    if not any_: L.append("- *(none)*")
    open(os.path.join(OUT,"families.md"),"w").write("\n".join(L))
    print(f"control {cp}/{cn}\n")
    print(f"{'family':38s} {'arms':>4s} {'env':>3s} {'n':>3s} {'pass':>4s} {'rate':>5s} {'p':>8s}")
    for r in out:
        print(f"{r['family'][:38]:38s} {r['arms']:>4d} {r['tasks']:>3d} "
              f"{r['n']:>3d} {r['passes']:>4d} {r['rate']:>5.0%} {r['p']:>8.4f}"
              + ("  <0.05" if r['p']<0.05 else "")
              + ("  [confounded arm]" if r['confounded'] else ""))
    print("\n-> analysis/families.md")

if __name__=="__main__": sys.exit(main())
