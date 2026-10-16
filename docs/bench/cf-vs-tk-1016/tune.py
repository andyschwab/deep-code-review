#!/usr/bin/env python3
"""Addendum-1 driver. usage: tune.py run|report|heldout-run|heldout-report [ARM]. See PREREGISTERED-ADDENDUM-1.md."""
import concurrent.futures as cf, json, random, sys, time
from pathlib import Path
import drive as d

D = d.D
d.CAP = 15.0
VAR = {"CF60": "cf60", "CFDIFF": "cfdiff", "CFHUNT": "cfhunt"}
for a, f in VAR.items():
    d.SYS[a] = (D / f"prompts/{f}_system.md").read_text()
SPLIT = json.loads((D / "split.json").read_text())
DEADLINE = 540
T0 = time.time()


def stage(fn, arms, cases):
    def run(c, a):
        return fn(c, a) if time.time() - T0 < DEADLINE else (c, "deferred")
    try:
        with cf.ThreadPoolExecutor(d.JOBS) as ex:
            for r in ex.map(lambda ca: run(*ca), [(c, a) for c in cases for a in arms]):
                print(*r, f"spent={d.spent():.3f}", flush=True)
    except d.Cap as e:
        print("CAP STOP:", e, flush=True)


def stats(rows, arm_i):
    s = lambda k: sum(r[arm_i][k] for r in rows)
    p, rc = s("good") / max(1, s("n")), s("cred") / max(1, s("bugs"))
    return p, rc, (2 * p * rc / (p + rc) if p + rc else 0.0), s("n")


def pair(arm, cases, base="TK"):
    rows, drops = [], []
    for c in cases:
        a, b = d.tally(c, arm) if (D / "outputs" / arm / f"{c}.json").exists() else None, d.tally(c, base)
        (rows.append((a, b)) if a and b else drops.append(c))
    return rows, drops


def boot(rows, B=10000, seed=1):
    rng = random.Random(seed); n = len(rows)
    f = lambda rs: [x - y for x, y in zip(stats(rs, 0)[:3], stats(rs, 1)[:3])]
    pt = f(rows); ds = [f([rows[rng.randrange(n)] for _ in range(n)]) for _ in range(B)]
    out = {}
    for i, k in enumerate(("precision", "recall", "f1")):
        v = sorted(x[i] for x in ds)
        out[k] = dict(d=round(pt[i], 3), ci=[round(v[int(.025 * B)], 3), round(v[int(.975 * B) - 1], 3)])
    return out


def row(rows, i):
    p, r, f, n = stats(rows, i)
    return dict(findings=n, precision=round(p, 3), recall=round(r, 3), f1=round(f, 3))


def tune_report():
    out = {}
    for a in ("CF", *VAR):
        rows, drops = pair(a, SPLIT["tune"])
        out[a] = dict(n=len(rows), dropped=drops, variant=row(rows, 0), TK=row(rows, 1))
    ok = {a: v for a, v in out.items() if a != "CF" and v["n"] and v["variant"]["precision"] >= v["TK"]["precision"]}
    pick = max(ok, key=lambda a: (ok[a]["variant"]["f1"], ok[a]["variant"]["precision"], -ok[a]["variant"]["findings"])) if ok else None
    out["chosen"] = pick; out["spend"] = round(d.spent(), 3)
    (D / "tune-results.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


def held_report(arm):
    rows, drops = pair(arm, SPLIT["heldout"])
    b = boot(rows); cref = pair("CF", SPLIT["heldout"])[0]
    out = dict(chosen=arm, n=len(rows), dropped=drops, variant=row(rows, 0), TK=row(rows, 1), diffs=b,
               CF_original_ref=dict(row=row(cref, 0), vs_TK=boot(cref)),
               PASS=b["recall"]["d"] >= -0.03 and b["precision"]["d"] > 0, precision_ci_excludes_0=b["precision"]["ci"][0] > 0,
               spend=round(d.spent(), 3))
    (D / "heldout-results.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    c = sys.argv[1]
    if c in ("run", "verify"):
        for fn in ((d.review,) if c == "run" else (d.verify,)):
            stage(fn, list(VAR), SPLIT["tune"])
    elif c in ("hrun", "hverify"):
        stage(d.review if c == "hrun" else d.verify, [sys.argv[2]], SPLIT["heldout"])
    elif c == "report": tune_report()
    elif c == "hreport": held_report(sys.argv[2])
