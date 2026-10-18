#!/usr/bin/env python3
"""business-ops shipped SKILL.md on the c150 scenarios (PCSS only, $0). Procedure: PREREGISTERED.md. Descriptive check, not a keep decision.

  bench.py run      generate the shipped arm, judge both orders with GLM-5.1 (judge v2), write results/c150-shipped.json
  bench.py paired   per-scenario shipped - e and shipped - v0 bootstrap, write results/paired-c150-shipped.json
Scenarios, rival outputs, rival text and the e / v0 results are read in place from ../bizops-e-confirm-1018 (nothing copied).
Every step appends an event to ledger.jsonl; ledger and records are never rewritten."""
import concurrent.futures as cf, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "bizops-e-confirm-1018"
sys.path.insert(0, str(HERE.parent.parent.parent / "scripts"))
import rival_eval as R

JOBS, MODEL = 6, R.JUDGE_MODEL


def led(event, **kw):
    with open(HERE / "ledger.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **kw}) + "\n")


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def scen():
    return json.loads((OLD / "scenarios/business-ops-c150.json").read_text())


def gen(sc):
    p = HERE / "outputs" / "shipped" / f"{sc['id']}.txt"
    if not p.exists():
        R.save(p, R.chat(R.GEN_MODEL, (HERE / "prompts/perun_business-ops_shipped.txt").read_text(), R.GEN_TASK + sc["prompt"], temperature=0.3))
    return p.read_text()


def run():
    scs = scen()
    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(gen, scs))
    outs = {"PERUN": {s["id"]: gen(s) for s in scs}, "RIVAL": {s["id"]: (OLD / "outputs/RIVAL" / f"{s['id']}.txt").read_text() for s in scs}}
    led("gen", arm="shipped", n=len(scs), outputs_sha256=hashlib.sha256("".join(outs["PERUN"][s["id"]] for s in scs).encode()).hexdigest())
    both = lambda s: (s["id"], [R.judge_one(MODEL, s, x, y, HERE / "judge" / "shipped", outs) for x, y in (("PERUN", "RIVAL"), ("RIVAL", "PERUN"))])
    with cf.ThreadPoolExecutor(JOBS) as ex:
        vs = dict(ex.map(both, scs))
    rate = R.slot1_rate([x for pair in vs.values() for x in pair])
    f = HERE / "results" / "c150-shipped.json"
    assert not f.exists(), f"{f} exists: records are never overwritten"
    failed = sum(None in p for p in vs.values())
    per = {i: 0.5 if None in p else R.scenario_score([R.order_score(x, o) for x, o in zip(p, ("PERUN", "RIVAL"))]) for i, p in vs.items()}
    v = list(per.values())
    lo, hi = R.boot(v)
    res = dict(skill="business-ops", arm="shipped", split="c150", n=len(v), judge=MODEL, slot1_rate=None if rate is None else round(rate, 3),
               win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)], wins=v.count(1.0), ties=v.count(0.5), losses=v.count(0.0),
               failed_judge_orders=failed, per_scenario=per, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps(res, indent=1) + "\n")
    led("judge", arm="shipped", judge=MODEL, result_sha256=fsha(f), win_rate=res["win_rate"], slot1_rate=res["slot1_rate"], failed_judge_orders=failed)
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


def paired():
    s = json.loads((HERE / "results/c150-shipped.json").read_text())
    res = dict(split="c150", n=s["n"], judge=s["judge"], shipped_win_rate=s["win_rate"], shipped_ci95=s["ci95"])
    for o in ("e", "v0"):
        b = json.loads((OLD / "results" / f"c150-{o}.json").read_text())
        assert b["judge"] == s["judge"] and b["per_scenario"].keys() == s["per_scenario"].keys()
        d = [s["per_scenario"][k] - b["per_scenario"][k] for k in s["per_scenario"]]
        lo, hi = R.boot(d)
        res[f"shipped_minus_{o}"] = dict(diff=round(sum(d) / len(d), 3), ci95=[round(lo, 3), round(hi, 3)], other_win_rate=b["win_rate"], other_ci95=b["ci95"])
    f = HERE / "results" / "paired-c150-shipped.json"
    assert not f.exists(), f"{f} exists: records are never overwritten"
    f.write_text(json.dumps(res, indent=1) + "\n")
    led("paired", result_sha256=fsha(f))
    print(json.dumps(res))


if __name__ == "__main__":
    {"run": run, "paired": paired}[sys.argv[1]]()
