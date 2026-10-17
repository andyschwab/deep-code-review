#!/usr/bin/env python3
"""Post hoc, descriptive only: paired C-minus-BASE difference (bootstrap over scenarios, seed 1) and win rates by scenario type. Run: SPLIT=held python3 analyze.py"""
import json, os, random, re, sys
os.environ.setdefault("SPLIT", "held")
sys.argv = ["bench.py"]
import bench
sc = bench.scenarios(); tag = {l.split()[0]: l.split()[1] for l in (bench.P / "held_seeds.txt").read_text().splitlines()}
m = {x: {s["id"]: bench.majority(x, s) for s in sc} for x in ("BASE", "C")}
d = [m["C"][i] - m["BASE"][i] for i in m["C"]]
lo, hi = bench.boot(d)
print(f"paired C - BASE majority: {sum(d)/len(d):+.3f} [{lo:+.3f}, {hi:+.3f}] n={len(d)}")
for t in ("notes", "diff", "report"):
    ids = [i for i in m["C"] if tag[i] == f"[{t}]"]
    print(t, len(ids), "C", round(sum(m["C"][i] for i in ids) / len(ids), 3), "BASE", round(sum(m["BASE"][i] for i in ids) / len(ids), 3))
import statistics as S
w = lambda a, i: len((bench.D / "outputs" / "held" / a / f"{i}.txt").read_text().split())
print("mean words BASE", round(S.mean(w("BASE", i) for i in m["C"]), 1), "C", round(S.mean(w("C", i) for i in m["C"]), 1), "RIVAL", round(S.mean(w("RIVAL", i) for i in m["C"]), 1))
