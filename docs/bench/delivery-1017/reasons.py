#!/usr/bin/env python3
"""Print judge verdicts and reasons. usage: reasons.py A B SPLIT [rival-only]
Prints per ticket: scenario score, and each judge's verdict (as A-preferred 1 / rival 0 / tie .5) with reason."""
import json, os, sys
D = os.path.dirname(os.path.abspath(__file__))
a, b, sp = sys.argv[1:4]
only = len(sys.argv) > 4
T = [t for t in json.load(open(D + "/tickets.json")) if t["split"] == sp]
S = os.environ.get("SUF", "")
pos = {"ds" + S: [0, 0, 0], "glm" + S: [0, 0, 0]}
for t in T:
    rows = []
    for tag in ("ds" + os.environ.get("SUF", ""), "glm" + os.environ.get("SUF", "")):
        for o in ("AB", "BA"):
            f = f"{D}/judge/{tag}/{a}__{b}/{o}/{t['id']}.json"
            if not os.path.exists(f):
                continue
            v = json.load(open(f))
            pos[tag][("1", "2", "tie").index(v["verdict"])] += 1
            s = 0.5 if v["verdict"] == "tie" else float((v["verdict"] == "1") == (o == "AB"))
            rows.append((tag, o, s, v["reason"]))
    if only and all(r[2] != 0 for r in rows):
        continue
    print("##", t["id"], t["title"])
    for tag, o, s, r in rows:
        print(f"  {tag}/{o} A={s}: {r}")
print("verdict position counts (1,2,tie):", pos)
