#!/usr/bin/env python3
"""Tests for docs/bench/xvendor-judge-1017/xvendor.py (offline: no PCSS call is made).

Pins that the harness reproduces the ORIGINAL committed results from the committed raw verdicts, so a cross-vendor
number is compared against a recomputed, not retyped, original; and that the scoring helpers orient and tiebreak
correctly. Prints PASS/FAIL per case and a final "Tests: P/N"; exits non-zero on any failure.
"""
import os, sys
from pathlib import Path

os.environ.setdefault("PCSS_KEY", "offline-test-key")  # never used: no network call is made here
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/bench/xvendor-judge-1017"))
import xvendor as xv  # noqa: E402

fails, total = [], 0


def ok(cond, name):
    global total
    total += 1
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


def orig_wr(bench, x, y):
    per = {}
    for i in xv.items():
        if i["bench"] == bench and i["x"] == x and i["y"] == y and i["orig"] is not None:
            per.setdefault(i["id"], []).append(i["orig"] if i["f"] == x else 1 - i["orig"])
    return xv.wr(per)


# original results recomputed from the committed judge files must equal the figures in docs/perun-vs-rivals.md
for bench, x, y, win, ci in [
    ("H1d idea-critic", "PERUN", "RIVAL", 0.65, [0.45, 0.85]),
    ("H1c communication-structure", "PERUN", "RIVAL", 0.5, [0.25, 0.8]),
    ("H1d product-discovery", "PERUN", "RIVAL", 0.3, [0.1, 0.5]),
    ("H1d growth-analytics", "PERUN", "RIVAL", 0.7, [0.5, 0.9]),
    ("H1e idea-critic v2", "NEW", "OLD", 0.65, [0.45, 0.85]),
    ("H1f communication-structure fix", "PERUN", "RIVAL", 0.1, [0.0, 0.3]),
    ("H1f communication-structure fix", "PERUN", "PLAIN", 0.1, [0.0, 0.3]),
    ("H1b pos set A rubric", "PERUN_BASE", "RIVAL", 1.0, [1.0, 1.0]),
    ("H1b pos set A rubric-free", "PERUN_BASE", "RIVAL", 0.15, [0.0, 0.4]),
    ("H1b pos set B base rubric-free", "PERUN_BASE", "RIVAL", 0.25, [0.1, 0.4]),
    ("H1b pos set B edit rubric-free", "PERUN_FIX", "RIVAL", 0.4, [0.2, 0.65]),
]:
    r = orig_wr(bench, x, y)
    ok(r["win"] == win and r["ci"] == ci, f"original {bench} {x}/{y} = {win} {ci} (got {r['win']} {r['ci']})")

# H7 original precision/recall difference from the committed Opus verdicts
A, T = dict(xv.recs("cf-vs-tk-1016", "CF")), dict(xv.recs("cf-vs-tk-1016", "TK"))
rows = [(xv.tally(c, A[c], A[c]["verdicts"]), xv.tally(c, T[c], T[c]["verdicts"])) for c in sorted(set(A) & set(T))]
d = xv.pdiff([r[0] for r in rows], [r[1] for r in rows])
ok(len(rows) == 43, "H7 original uses all 43 cases")
ok(d["precision"] == {"d": 0.137, "ci": [0.032, 0.247]}, f"H7 original precision diff {d['precision']}")
ok(d["recall"] == {"d": -0.14, "ci": [-0.256, -0.047]}, f"H7 original recall diff {d['recall']}")

# helpers
it = dict(x="PERUN", f="PERUN")
ok(xv.sx(it, "1") == 1.0 and xv.sx(it, "2") == 0.0 and xv.sx(it, "tie") == 0.5, "sx: Perun shown first")
it = dict(x="PERUN", f="RIVAL")
ok(xv.sx(it, "1") == 0.0 and xv.sx(it, "2") == 1.0 and xv.sx(it, "tie") == 0.5, "sx: Perun shown second")
ok(xv.jobj('<think>x</think>```json\n{"verdict": "2", "reason": "r"}\n```') == {"verdict": "2", "reason": "r"}, "jobj extracts fenced JSON")
ok(xv.jobj("no json here") is None, "jobj returns None without JSON")
ok(xv.wr({"01": [1.0, 1.0], "02": [0.0, 1.0]})["splits"] == 1, "wr counts order splits")
ok(xv.wr({str(i): [0.0, 0.0] for i in range(10)})["verdict"] == "LOSS", "wr labels a CI wholly below 0.5 a LOSS")
ok(xv.wr({str(i): [1.0, 1.0] for i in range(10)})["verdict"] == "PASS", "wr labels a CI wholly above 0.5 a PASS")

# H1e new vs rival: the original is 4 complete scenarios (0.875, "not a result") plus a 5th judged in one order only
per = {}
for i in xv.items():
    if i["bench"] == "H1e idea-critic v2" and i["x"] == "NEW" and i["y"] == "RIVAL" and i["orig"] is not None:
        per.setdefault(i["id"], []).append(i["orig"] if i["f"] == i["x"] else 1 - i["orig"])
ok(len(per) == 5 and sorted(len(v) for v in per.values()) == [1, 2, 2, 2, 2], "H1e NEW/RIVAL: 5 scenarios carry an original verdict, 9 judgments, one in a single order")
ok(xv.wr({k: v for k, v in per.items() if len(v) == 2})["win"] == 0.875, "H1e NEW/RIVAL: the 4 complete scenarios give the documented 0.875")
ok(xv.wr(per)["win"] == 0.9 and xv.wr(per)["ci"] == [0.7, 1.0], "H1e NEW/RIVAL: all 9 committed verdicts give 0.9 [0.7, 1.0]")

# tiebreak median
ok(xv.tb_score(1.0, 0.0, 0.5) == 0.5 and xv.tb_score(1.0, 0.0, 0.0) == 0.0 and xv.tb_score(0.0, 1.0, 1.0) == 1.0, "tb_score is the median of original, Qwen and GLM")
ok(xv.tb_score(0.5, 1.0, 0.0) == 0.5, "tb_score: a split original is the median when Qwen and GLM disagree")

# verdicts_for mode tb on a synthetic finding set (cache entries are removed afterwards; nothing is written to disk)
K = "rev|T|A|c1"
V = lambda v: {"verdict": v}
rec = {"verdicts": {"0": V("real"), "1": V("not_a_bug"), "2": V("real"), "3": V("real")}}
xv.CACHE[xv.QWEN].d[K] = {"verdicts": {"0": V("real"), "1": V("gt_same"), "2": V("not_a_bug"), "3": V("not_a_bug")}}
xv.CACHE[xv.GLM].d[K] = {"verdicts": {"0": V("not_a_bug"), "1": V("real"), "2": V("not_a_bug")}}  # no GLM verdict for finding 3
try:
    tb = xv.verdicts_for("T", "A", "c1", rec, "tb")
    ok(tb["0"] == V("real"), "tb: Qwen and original agree -> GLM is ignored")
    ok(tb["1"] == V("real"), "tb: three different classes -> the median class (real)")
    ok(tb["2"] == V("not_a_bug"), "tb: GLM sides with Qwen against the original -> Qwen's class")
    ok(tb["3"] == V("not_a_bug"), "tb: no GLM verdict for a disagreement -> Qwen's verdict kept")
    ok(xv.verdicts_for("T", "A", "c1", rec, "orig") is rec["verdicts"] and xv.verdicts_for("T", "A", "c1", rec, "qwen")["1"] == V("gt_same"), "verdicts_for orig and qwen modes return the unmodified sets")
finally:
    xv.CACHE[xv.QWEN].d.pop(K); xv.CACHE[xv.GLM].d.pop(K)

# position counts in results.json agree with the cached verdicts, and GLM's share is reported
import json  # noqa: E402
R = json.load(open(Path(xv.D) / "results.json"))
tot = R["position_total"]
ok(all(sum(1 for i in xv.items() if (xv.CACHE[xv.QWEN].d.get(i["key"]) or {}).get("verdict") == s) == tot["qwen"][s] for s in ("1", "2", "tie")), "position_total.qwen equals a recount from verdicts-qwen.jsonl")
ok(all(sum(1 for i in xv.items() if (xv.CACHE[xv.GLM].d.get(i["key"]) or {}).get("verdict") == s) == tot["glm"][s] for s in ("1", "2", "tie")), "position_total.glm equals a recount from verdicts-glm52.jsonl")
ok(tot["glm"] == {"1": 75, "2": 27, "tie": 0}, "GLM picked the first slot in 75 of 102 verdicts (the figure quoted in the doc)")
ok(all(sum(b[w][s] for b in R["position"].values() if w in b) == tot[w][s] for w in tot for s in ("1", "2", "tie")), "per-bench position counts sum to position_total")

# the tiebreak mix is reported per row
row = next(p for p in R["pairwise"] if p["row"] == "H1e idea-critic v2" and p["y"] == "RIVAL")
ok(row["scenarios_with_original"] == 5 and row["tiebreak_qwen_only_scenarios"] == 5, "H1e NEW/RIVAL tiebreak: 5 scenarios use the median, 5 are Qwen alone")
ok(all(p["tiebreak_qwen_only_scenarios"] == 0 for p in R["pairwise"] if p is not row), "every other row has an original verdict on all scenarios")

print(f"Tests: {total - len(fails)}/{total}")
sys.exit(1 if fails else 0)
