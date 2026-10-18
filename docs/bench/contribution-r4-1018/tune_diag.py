"""Tune-only diagnostic (run from the repo root): tune_diag.py OUTDIR SKILL_MD. Generates the skill arm and the rival on scenarios-tune.json
(outputs cached under OUTDIR; copy a previous OUTDIR/rival to share rival answers), judges both orders with GLM-5.1, prints the skill
win rate and the judge analysis of every both-orders loss, and writes OUTDIR/judge.json. Never produces a verdict.
"""
import sys, json, concurrent.futures as cf
from pathlib import Path
sys.path.insert(0, "scripts"); import rival_eval as R
H = Path("docs/bench/contribution-r4-1018"); out = Path(sys.argv[1]); skill = sys.argv[2]
scs = json.loads((H/"scenarios-tune.json").read_text())
T = {"S": Path(skill).read_text(), "rival": (H/"frozen/rival.md").read_text()}
def gen(a):
    k, sc = a; p = out/k/f"{sc['id']}.txt"
    if not p.exists(): R.save(p, R.chat(R.GEN_MODEL, T[k], R.GEN_TASK+sc["prompt"], temperature=0.3))
    return k, sc["id"], p.read_text()
O = {}
with cf.ThreadPoolExecutor(6) as ex:
    for k, i, t in ex.map(gen, [(k, s) for k in T for s in scs]): O.setdefault(k, {})[i] = t
def j(sc):
    res = []
    for a, b in (("S","rival"),("rival","S")):
        x, y = R.labels(sc, O[a][sc["id"]], O[b][sc["id"]])
        u = f"REQUEST:\n{sc['prompt']}\n\n=== Response {x} ===\n{O[a][sc['id']]}\n\n=== Response {y} ===\n{O[b][sc['id']]}\n"
        t = R.chat("GLM-5.1", R.JUDGE_SYSTEM.format(a=x, b=y), u, max_tokens=3000)
        v = R.parse_verdict(t, x, y); w = {"1": a, "2": b}.get(v, "tie")
        res.append((w, t))
    return sc["id"], res
with cf.ThreadPoolExecutor(6) as ex: J = dict(ex.map(j, scs))
sc_ = {i: sum({"S":1,"rival":0}.get(w,0.5) for w,_ in r)/2 for i, r in J.items()}
print("S win", sum(sc_.values())/len(sc_))
json.dump(J, open(out/"judge.json", "w"), indent=1)
for i, s in sc_.items():
    if s == 0: print(i, J[i][0][1][:700].replace("\n"," "))
