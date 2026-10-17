#!/usr/bin/env python3
"""Reproduces DIAGNOSIS.md numbers from the verdicts and outputs of the earlier comms benches under docs/bench.
Keyword clusters are approximate (regexes below); run: python3 diagnose.py  (from any directory)."""
import collections, glob, json, os, re, statistics as S
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []
for p in glob.glob(B + "/comms-*/judge/**/*.json", recursive=True) + glob.glob(B + "/loss-fix-1017/judge/cs/**/*.json", recursive=True):
    parts = p[len(B) + 1:].split("/")
    pair = [x for x in parts if "__" in x]
    try:
        d = json.load(open(p))
    except ValueError:
        continue
    if not pair or str(d.get("verdict")) not in ("1", "2") or "comms-r4" in parts[0]:
        continue
    a, b = pair[0].split("__")
    v = str(d["verdict"])
    rows.append(dict(bench=parts[0], path="/".join(parts), win=a if v == "1" else b, lose=b if v == "1" else a, reason=d.get("reason", ""), scen=parts[-1][:-5]))
rv_rows = [r for r in rows if r["bench"] in ("comms-round2-1017", "comms-round3-1017", "loss-fix-1017")]
rv = [r for r in rv_rows if r["win"] == "RIVAL"]
ow = [r for r in rv_rows if r["win"] != "RIVAL"]
print("verdicts (rounds 2, 3, loss-fix cs+pd):", len(rv_rows), " rival won:", len(rv), " ours won:", len(ow))
T = {"completeness": r"\bcomplete|\bdetail|comprehensive|thorough|\bfuller\b|more information|omits?\b|\blacks?\b|\bmissing|includes? all|full context|condensed|key (metrics|data|facts|context)",
     "recommendation": r"\brecommend|next step|path forward|\bguidance|\blean\b|decision-?ready|synthes",
     "options/tradeoffs": r"trade-?off|\boptions?\b|pros|cons\b|risk",
     "ready/placeholder": r"ready|placeholder|(fewer|minimal|no) edits|requir\w+ (edit|rewrit)",
     "meta/emoji/clutter": r"emoji|clutter|meta|extraneous|editorial|commentary|unnecessary",
     "concise": r"concise|brief|succinct|shorter|focused",
     "fabrication": r"invent|fabricat|unsupported|unrequested|hallucin|speculat|made-up"}
for k, v in T.items():
    a = sum(bool(re.search(v, r["reason"], re.I)) for r in rv)
    b = sum(bool(re.search(v, r["reason"], re.I)) for r in ow)
    print(f"  theme {k}: in {100*a/len(rv):.0f}% of rival-win reasons, {100*b/len(ow):.0f}% of ours-win reasons")
n = sum(bool(re.search(T["completeness"], r["reason"], re.I) or re.search(T["recommendation"], r["reason"], re.I)) for r in rv)
print(f"  completeness or recommendation: {100*n/len(rv):.0f}% of rival-win reasons")

def wc(p):
    return len(open(p).read().split()) if os.path.exists(p) else None
print("per-scenario rival share (of the 6 judge-order verdicts) vs our/rival word ratio:")
for bench, split in [("comms-round2-1017", "held"), ("comms-round3-1017", "held"), ("comms-round3-1017", "tune")]:
    arms = {r["win"] for r in rows if r["bench"] == bench and f"/{split}/" in r["path"]} | {r["lose"] for r in rows if r["bench"] == bench and f"/{split}/" in r["path"]}
    for arm in sorted(arms - {"RIVAL"}):
        sh = {}
        for r in rows:
            if r["bench"] == bench and f"/{split}/" in r["path"] and {r["win"], r["lose"]} == {arm, "RIVAL"}:
                sh.setdefault(r["scen"], [0, 0])[0 if r["win"] == "RIVAL" else 1] += 1
        xs, ys = [], []
        for i, (a, b) in sh.items():
            p1, p2 = (f"{B}/{bench}/outputs/{split}/{x}/{i}.txt" for x in (arm, "RIVAL"))
            if wc(p1) and wc(p2):
                xs.append(wc(p1) / wc(p2)); ys.append(a / (a + b))
        if len(xs) < 10:
            continue
        r_ = sum((x - S.mean(xs)) * (y - S.mean(ys)) for x, y in zip(xs, ys)) / len(xs) / (S.pstdev(xs) * S.pstdev(ys))
        short = [y for x, y in zip(xs, ys) if x < 0.9]; par = [y for x, y in zip(xs, ys) if x >= 0.9]
        print(f"  {bench} {split} {arm}: n={len(xs)} mean ratio {S.mean(xs):.2f} corr {r_:+.2f}; rival share when ours<0.9x: {S.mean(short):.2f} (n={len(short)}), else {S.mean(par):.2f} (n={len(par)})")

# round 3 held-out C2 vs RIVAL: does the rival state a recommendation (regex), and who wins then
REC = r"recommend|my lean|i suggest|i.d (go|pick)|propos|suggest"
sh = {}
for r in rows:
    if r["bench"] == "comms-round3-1017" and "/held/" in r["path"] and {r["win"], r["lose"]} == {"C2", "RIVAL"}:
        sh.setdefault(r["scen"], [0, 0])[0 if r["win"] == "RIVAL" else 1] += 1
yes, no = [], []
for i, (a, b) in sh.items():
    rival_rec = bool(re.search(REC, open(f"{B}/comms-round3-1017/outputs/held/RIVAL/{i}.txt").read(), re.I))
    (yes if rival_rec else no).append(a / (a + b))
print(f"round 3 held C2 vs RIVAL: rival share {S.mean(yes):.2f} when the rival answer states a recommendation (n={len(yes)}), {S.mean(no):.2f} otherwise (n={len(no)})")
