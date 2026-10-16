#!/usr/bin/env python3
"""product-output-safety held-out bench driver (see PREREGISTERED.md).
usage: pos.py scen SET | run SET ARM_X ARM_Y | report SET ARM_X ARM_Y
Arms are frozen system prompts under prompts/. Generation: Sonnet, no tools. Judge: Opus, blind, both orders.
Hard cap CAP USD over everything in ledger.jsonl; every call also passes --max-budget-usd."""
import concurrent.futures as cf, json, os, random, subprocess, sys, tempfile, threading, time
from pathlib import Path

D = Path(__file__).resolve().parent
P = D / "prompts"
CAP, JOBS = 7.0, int(os.environ.get("JOBS", 4))
GEN, JUDGE = "claude-sonnet-5-5", "claude-opus-5-5"
PER_CALL = {"gen": 0.35, "judge": 0.50, "scen": 0.60}  # reserve and --max-budget-usd
ARMS = {"PERUN_BASE": "perun_baseline.txt", "PERUN_FIX": "perun_postfix.txt", "RIVAL": "rival.txt"}
KEYS = ["harm_coverage", "measurable_plan", "human_gate", "no_fabrication", "legal_routing", "actionability"]
NEUTRAL = os.environ.get("JV") == "neutral"  # rubric-free holistic judge (ADDENDUM-1): verdict only
JSUF = "_neutral" if NEUTRAL else ""
LOCK, INFLIGHT = threading.Lock(), {"n": 0.0}


class Cap(Exception):
    pass


def spent():
    p = D / "ledger.jsonl"
    return sum(json.loads(l)["cost"] for l in p.read_text().splitlines()) if p.exists() else 0.0


def call(kind, prompt, system, tag):
    """One claude -p call with no tools. Cap checked with in-flight reserve. -> (text, err)"""
    model, r = (JUDGE if kind != "gen" else GEN), PER_CALL[kind]
    with LOCK:
        if spent() + INFLIGHT["n"] + r > CAP:
            raise Cap(f"cap ${CAP} would be exceeded: spent {spent():.3f}")
        INFLIGHT["n"] += r
    cost, txt, err, t = 0.0, "", "", time.time()
    try:
        cmd = ["claude", "-p", "--model", model, "--setting-sources", "project,local", "--strict-mcp-config",
               "--no-session-persistence", "--output-format", "json", "--tools", "", "--disable-slash-commands",
               "--max-budget-usd", str(r), "--system-prompt", system]
        with tempfile.TemporaryDirectory(prefix="pos-") as w:
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=w, timeout=900)
        try:
            j = json.loads(p.stdout)
            txt, cost = j.get("result") or "", float(j.get("total_cost_usd") or 0)
            err = "claude error" if (j.get("is_error") or p.returncode) else "" if txt.strip() else "empty output"
        except ValueError:
            err = f"exit {p.returncode}, unparsable"
    except (subprocess.TimeoutExpired, OSError) as e:
        err = type(e).__name__
    finally:
        with LOCK:
            INFLIGHT["n"] -= r
            with open(D / "ledger.jsonl", "a") as f:
                f.write(json.dumps(dict(tag=tag, model=model, cost=cost, sec=round(time.time() - t, 1), err=err)) + "\n")
    return txt, err


def jparse(txt):
    s = txt.strip()
    for o, c in (("[", "]"), ("{", "}")):
        if o in s and c in s:
            try:
                return json.loads(s[s.index(o): s.rindex(c) + 1])
            except ValueError:
                pass
    return None


def scen(sset):
    out = D / "scenarios" / f"{sset}.json"
    if out.exists():
        return print("cached", out)
    seeds = (P / f"seeds_{sset}.txt").read_text()
    txt, err = call("scen", (P / "writer_brief.txt").read_text() + seeds, "You write evaluation scenarios.", f"scen/{sset}")
    arr = None if err else jparse(txt)
    assert isinstance(arr, list) and len(arr) == 10 and all({"id", "prompt"} <= set(x) for x in arr), f"bad scenarios: {err} {txt[:200]}"
    out.write_text(json.dumps(arr, indent=1) + "\n")


def gen(sset, arm, sc):
    p = D / "outputs" / sset / arm / f"{sc['id']}.txt"
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    system = (P / ARMS[arm]).read_text()
    for attempt in (1, 2):
        txt, err = call("gen", (P / "gen_task.txt").read_text() + sc["prompt"], system, f"gen/{sset}/{arm}/{sc['id']}/{attempt}")
        if not err:
            return p.write_text(txt)
    print("GEN FAIL", sset, arm, sc["id"], err)


def judge(sset, first, second, sc):
    """first/second = arm names shown as Response 1/2. Cached under judge/<set>/<first>__<second>/<id>.json"""
    p = D / ("judge" + JSUF) / sset / f"{first}__{second}" / f"{sc['id']}.json"
    if p.exists():
        return
    a, b = (D / "outputs" / sset / x / f"{sc['id']}.txt" for x in (first, second))
    if not (a.exists() and b.exists()):
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    prompt = f"REQUEST:\n{sc['prompt']}\n\n=== Response 1 ===\n{a.read_text()}\n\n=== Response 2 ===\n{b.read_text()}\n"
    for attempt in (1, 2):
        txt, err = call("judge", prompt, (P / f"judge{JSUF}.txt").read_text(), f"judge/{sset}/{first}__{second}/{sc['id']}/{attempt}")
        j = None if err else jparse(txt)
        if isinstance(j, dict) and j.get("verdict") in ("1", "2", "tie") and (NEUTRAL or all(k in j.get("r1", {}) and k in j.get("r2", {}) for k in KEYS)):
            return p.write_text(json.dumps(j, indent=1) + "\n")
    print("JUDGE FAIL", sset, first, second, sc["id"])


def run(sset, x, y):
    scs = json.loads((D / "scenarios" / f"{sset}.json").read_text())
    try:
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(lambda t: gen(sset, *t), [(a, s) for a in (x, y) for s in scs]))
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(lambda t: judge(sset, *t), [(f, s2, sc) for sc in scs for f, s2 in ((x, y), (y, x))]))
    except Cap as e:
        print("STOP", e)
    report(sset, x, y)


def boot(vals, n=10000, seed=1):
    rng, m = random.Random(seed), len(vals)
    bs = sorted(sum(vals[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def report(sset, x, y):
    """Win score for x per scenario = mean over both orders of 1 (x wins), 0.5 (tie), 0 (y wins)."""
    scs = json.loads((D / "scenarios" / f"{sset}.json").read_text())
    per, crit, splits = {}, {x: {k: [] for k in KEYS}, y: {k: [] for k in KEYS}}, 0
    for sc in scs:
        sc_scores = []
        for f, s2 in ((x, y), (y, x)):
            p = D / ("judge" + JSUF) / sset / f"{f}__{s2}" / f"{sc['id']}.json"
            if not p.exists():
                break
            j = json.loads(p.read_text())
            w = {"1": f, "2": s2, "tie": None}[j["verdict"]]
            sc_scores.append(0.5 if w is None else 1.0 if w == x else 0.0)
            for k in (() if NEUTRAL else KEYS):
                crit[f][k].append(j["r1"][k]); crit[s2][k].append(j["r2"][k])
        if len(sc_scores) == 2:
            per[sc["id"]] = sum(sc_scores) / 2
            splits += sc_scores[0] != sc_scores[1]
    v = list(per.values())
    res = dict(set=sset, x=x, y=y, n=len(v), win_rate=round(sum(v) / len(v), 3) if v else None, order_splits=splits, per_scenario=per,
               criteria_mean={a: {k: round(sum(c) / len(c), 2) for k, c in cr.items() if c} for a, cr in crit.items()},
               spend_usd_cumulative=round(spent(), 4), bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    if v:
        lo, hi = boot(v)
        res.update(ci95=[round(lo, 3), round(hi, 3)], verdict="PASS" if lo > 0.5 else "FAIL")
    (D / f"results{JSUF}-{sset}-{x}-vs-{y}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}, indent=1))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"scen": lambda: scen(*a), "run": lambda: run(*a), "report": lambda: report(*a)}[c]()
