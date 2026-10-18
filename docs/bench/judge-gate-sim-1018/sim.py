#!/usr/bin/env python3
"""Offline replay and simulation of a judge with a slot-1 bonus (stdlib only, no model calls, $0).

Preregistered in README.md. Judge model: Perun is picked with probability clip(p + delta) when shown first
and clip(p - delta) when shown second; scenario score is 1/0 when both orders agree, else 0.5.

Usage: python3 sim.py selftest | python3 sim.py run   (run writes results/results.json and prints tables)
"""
import json
import multiprocessing
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
DELTAS = [round(0.05 * i, 2) for i in range(9)]
N, REPS, BOOT = 150, 2000, 1000
JUDGES = ("GLM-5.1", "GLM-5.2", "gpt-oss_120b")
MAX_BIAS, MIN_COV, VERDICT_DELTA = 0.01, 0.93, 0.20
KAPPAS, WS, W0 = (2, 8), (0.45, 0.50, 0.55, 0.60), 0.45


def clip(x):
    return min(1.0, max(0.0, x))


def judge_rep(p, delta, rng):
    """One scenario: returns (score, resolved, slot1_picks) for true preference p and slot-1 bonus delta."""
    a = rng.random() < clip(p + delta)  # Perun shown first: Perun picked
    b = rng.random() < clip(p - delta)  # rival shown first: Perun picked
    score = 1.0 if a and b else 0.0 if not a and not b else 0.5
    return score, a == b, int(a) + int(not b)  # slot 1 is Perun in order a, the rival in order b


def boot_ci(vals, rng):
    """95 percent percentile bootstrap CI of the mean, resampling the multiset of values via sequential binomials."""
    cats = sorted(set(vals))
    counts = [vals.count(c) for c in cats]
    n, ms = len(vals), []
    for _ in range(BOOT):
        left, pl, tot = n, 1.0, 0.0
        for c, k in zip(cats[:-1], counts[:-1]):
            q = k / n / pl if pl > 1e-12 else 0.0
            d = rng.binomialvariate(left, min(1.0, q))
            tot, left, pl = tot + c * d, left - d, pl - k / n
        ms.append((tot + cats[-1] * left) / n)
    ms.sort()
    return ms[int(0.025 * BOOT)], ms[int(0.975 * BOOT) - 1]


def cell(draw, delta, truth, seed):
    """REPS repetitions; draw(rng) -> (p0 list, p1 list). truth = dict stat -> true value (v0, v1, diff)."""
    rng = random.Random(seed)
    acc = {s: dict(est=0.0, hit=0, w=0.0) for s in truth}
    res = sl = 0.0
    for _ in range(REPS):
        p0, p1 = draw(rng)
        r0 = [judge_rep(p, delta, rng) for p in p0]
        r1 = [judge_rep(p, delta, rng) for p in p1]
        s0, s1 = [x[0] for x in r0], [x[0] for x in r1]
        for k, v in (("v0", s0), ("v1", s1), ("diff", [b - a for a, b in zip(s0, s1)])):
            m = sum(v) / N
            lo, hi = boot_ci(v, rng)
            acc[k]["est"] += m
            acc[k]["hit"] += lo <= truth[k] <= hi
            acc[k]["w"] += hi - lo
        res += sum(x[1] for x in r0 + r1) / (2 * N)
        sl += sum(x[2] for x in r0 + r1) / (4 * N)
    out = {k: dict(truth=round(truth[k], 4), bias=round(a["est"] / REPS - truth[k], 4), coverage=round(a["hit"] / REPS, 4),
                   ci_width=round(a["w"] / REPS, 4)) for k, a in acc.items()}
    return dict(delta=delta, stats=out, resolved=round(res / REPS, 4), slot1_share=round(sl / REPS, 4))


def passes(c):
    return all(abs(s["bias"]) <= MAX_BIAS and s["coverage"] >= MIN_COV for s in c["stats"].values())


def spent_p(rnd, judge, arm):
    """Observed scenario score per scenario id from results/judge-verdicts.json (tie = 0.5 for that order)."""
    d = json.loads((BENCH / f"growth-{rnd}-1018/results/judge-verdicts.json").read_text())
    out = {}
    for k, v in d.items():
        a, j, m, order, f = k.split("/")
        if a == arm and m == judge:
            y = 0.5 if v == "tie" else float((v == "1") == (order == "PERUN__RIVAL"))
            out.setdefault(f.split("-")[0], []).append(y)  # file suffix hash differs per order
    assert all(len(x) == 2 for x in out.values()) and len(out) == N, (rnd, judge, arm, len(out))
    return {f: sum(x) / 2 for f, x in out.items()}


def task(t):
    kind, args, delta = t
    if kind == "replay":
        rnd, judge = args
        a0, a1 = spent_p(rnd, judge, "v0"), spent_p(rnd, judge, "v1")
        ids = sorted(a0)
        p0, p1 = [a0[i] for i in ids], [a1[i] for i in ids]
        truth = dict(v0=sum(p0) / N, v1=sum(p1) / N, diff=(sum(p1) - sum(p0)) / N)

        def draw(rng):
            ix = [rng.randrange(N) for _ in range(N)]
            return [p0[i] for i in ix], [p1[i] for i in ix]
    else:
        w, kap = args
        truth = dict(v0=W0, v1=w, diff=w - W0)

        def draw(rng):
            return ([rng.betavariate(W0 * kap, (1 - W0) * kap) for _ in range(N)],
                    [rng.betavariate(w * kap, (1 - w) * kap) for _ in range(N)])
    c = cell(draw, delta, truth, f"{kind}|{args}|{delta}")
    return dict(source=kind, cell=list(args), **c, passes=passes(c))


def summarize(cells):
    """Per source and delta: worst |bias|, lowest coverage, all-cells pass; verdict over delta <= VERDICT_DELTA."""
    out = {}
    for src in ("replay", "synthetic"):
        rows = []
        for d in DELTAS:
            cs = [c for c in cells if c["source"] == src and c["delta"] == d]
            st = [s for c in cs for s in c["stats"].values()]
            rows.append(dict(delta=d, max_abs_bias=max(abs(s["bias"]) for s in st), min_coverage=min(s["coverage"] for s in st),
                             mean_resolved=round(sum(c["resolved"] for c in cs) / len(cs), 4),
                             mean_slot1=round(sum(c["slot1_share"] for c in cs) / len(cs), 4), passes=all(c["passes"] for c in cs)))
        out[src] = rows
    ok = lambda r: r["passes"]
    best = -1.0
    for d in DELTAS:
        if all(ok(r) for s in out.values() for r in s if r["delta"] <= d):
            best = d
        else:
            break
    return dict(by_source=out, largest_passing_delta=None if best < 0 else best,
                verdict="PASS" if all(ok(r) for s in out.values() for r in s if r["delta"] <= VERDICT_DELTA) else "FAIL")


def selftest():
    rng = random.Random(1)
    assert judge_rep(1.0, 0.0, rng)[0] == 1.0 and judge_rep(0.0, 0.0, rng)[0] == 0.0
    # p = 1 with bonus .2: Perun first always picked, second picked w.p. .8 -> E[score] = (1 + .8) / 2 = .9 (shrinks toward .5)
    m = sum(judge_rep(1.0, 0.2, rng)[0] for _ in range(20000)) / 20000
    assert abs(m - 0.9) < 0.01, m
    # linear region: p = .5, any delta <= .5 leaves E[score] at .5; slot-1 share is .5 + delta
    r = [judge_rep(0.5, 0.2, rng) for _ in range(20000)]
    assert abs(sum(x[0] for x in r) / 20000 - 0.5) < 0.01 and abs(sum(x[2] for x in r) / 40000 - 0.7) < 0.01
    lo, hi = boot_ci([0.0, 0.5, 1.0] * 50, rng)
    assert lo < 0.5 < hi and hi - lo < 0.15
    p = spent_p("r5", "GLM-5.1", "v0")  # frozen verdict.json says win_v0 = 0.537
    assert abs(sum(p.values()) / N - 0.537) < 0.001
    print("selftest ok")


def main():
    if sys.argv[1:] == ["selftest"]:
        return selftest()
    assert sys.argv[1:] == ["run"], __doc__
    jobs = [("replay", (r, j), d) for r in ("r4", "r5") for j in JUDGES for d in DELTAS]
    jobs += [("synthetic", (w, k), d) for k in KAPPAS for w in WS for d in DELTAS]
    with multiprocessing.Pool() as pool:
        cells = pool.map(task, jobs, chunksize=1)
    res = dict(params=dict(deltas=DELTAS, n=N, reps=REPS, boot=BOOT, max_abs_bias=MAX_BIAS, min_coverage=MIN_COV,
                           verdict_delta=VERDICT_DELTA), summary=summarize(cells), cells=cells)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results/results.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    main()
