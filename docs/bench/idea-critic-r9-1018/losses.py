#!/usr/bin/env python3
"""Cluster the judge reasons of every v0 loss (final == RIVAL) in the spent idea-critic rounds. Keyword rule, deterministic; clusters overlap.
usage: losses.py  (run from the repo root). Prints counts per round group; the largest cluster picks which edit goes first (PREREGISTERED.md section 2)."""
import glob, json, re, collections

C = {"ARITH": r"arithmetic|math|recomput|recalcul|calculat|miscalc|computes|figure|error",
     "TRIG": r"trigger|kill|halt|abort|stop|pivot|threshold",
     "STEP": r"pilot|phased|capped|sprint|staged|first step|rollout"}
G = {"r5r6": r"idea-critic-r[56]-", "r7r8": r"idea-critic-r[78]-"}
cnt = collections.defaultdict(collections.Counter)
for f in sorted(glob.glob("docs/bench/idea-critic-r[5678]-*/judge*/v2/**/v0/*.json", recursive=True)):
    j = json.load(open(f))
    if j["final"] != "RIVAL":
        continue
    txt = " ".join(o["reason"].lower() for v in j["votes"].values() for o in v["orders"] if o and o["winner"] == "RIVAL")
    for g, p in G.items():
        if re.search(p, f):
            cnt[g]["losses"] += 1
            for k, r in C.items():
                cnt[g][k] += bool(re.search(r, txt))
for g in cnt:
    print(g, dict(cnt[g]))
