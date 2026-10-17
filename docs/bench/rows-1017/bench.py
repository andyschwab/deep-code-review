#!/usr/bin/env python3
"""Row re-test driver on PCSS (see PREREGISTERED.md). No paid claude -p calls.

usage: bench.py ROW SET scen|run|report [X Y]      e.g. bench.py contribution N1 run PERUN RIVAL
Layout under ROW/: prompts/{writer_brief,gen_task,judge}.txt, prompts/<arm lowercase>.txt (frozen system
prompts), seeds_<SET>.txt (one "NN text" per line). Writer and generator: Qwen3.5-397B-A17B, no tools.
Judge: DeepSeek-V4-Flash, blind, no criteria, both orders. Tiebreak: GLM-5.2 (both orders) on every scenario
where the two DS orders do not agree on one arm. Score per scenario in [0,1] for X: 1 win, 0.5 tie, 0 loss.
"""
import concurrent.futures as cf, json, random, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pcss import chat

D = Path(__file__).resolve().parent
GEN, J1, J2 = "Qwen3.5-397B-A17B", "DeepSeek-V4-Flash", "GLM-5.2"
JOBS = 4


def jparse(txt):
    for o, c in (("[", "]"), ("{", "}")):
        if o in txt and c in txt:
            try:
                return json.loads(txt[txt.index(o): txt.rindex(c) + 1])
            except ValueError:
                pass
    return None


def scen(row, st):
    out = row / f"scenarios_{st}.json"
    if out.exists():
        return print("cached", out)
    seeds = [l for l in (row / f"seeds_{st}.txt").read_text().splitlines() if l.strip()]
    arr = []
    for i in range(0, len(seeds), 10):
        part = seeds[i:i + 10]
        brief = (row / "prompts/writer_brief.txt").read_text().replace("{n}", str(len(part)))
        for _ in range(3):
            t = chat(GEN, "You write evaluation scenarios.", brief + "\n".join(part), max_tokens=8000)
            j = [dict(id=m[0], prompt=m[1].strip()) for m in re.findall(r"^###\s*(\d\d)[^\n]*\n(.*?)(?=^###|\Z)", t, flags=re.S | re.M)]
            if [x["id"] for x in j] == [s[:2] for s in part] and all(len(x["prompt"].split()) > 40 for x in j):
                arr += j
                break
        else:
            raise SystemExit(f"bad scenarios for seeds {part[0][:2]}..")
    out.write_text(json.dumps(arr, indent=1) + "\n")


def gen(row, st, arm, sc):
    p = row / "outputs" / st / arm / f"{sc['id']}.txt"
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        t = chat(GEN, (row / "prompts" / f"{arm.lower()}.txt").read_text(), (row / "prompts/gen_task.txt").read_text() + sc["prompt"], max_tokens=4000)
        if len(t) > 200:
            return p.write_text(t)
    print("GEN FAIL", arm, sc["id"])


def judge(row, st, model, first, second, sc):
    tag = "ds" if model == J1 else "glm"
    p = row / f"judge_{tag}" / st / f"{first}__{second}" / f"{sc['id']}.json"
    if p.exists():
        return
    a, b = (row / "outputs" / st / x / f"{sc['id']}.txt" for x in (first, second))
    if not (a.exists() and b.exists()):
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    prompt = f"REQUEST:\n{sc['prompt']}\n\n=== Response 1 ===\n{a.read_text()}\n\n=== Response 2 ===\n{b.read_text()}\n"
    for _ in range(3):
        j = jparse(chat(model, (row / "prompts/judge.txt").read_text(), prompt, max_tokens=1500, temperature=0))
        if isinstance(j, dict) and str(j.get("verdict")) in ("1", "2", "tie"):
            j["verdict"] = str(j["verdict"])
            return p.write_text(json.dumps(j, indent=1) + "\n")
    print("JUDGE FAIL", model, first, second, sc["id"])


def score(row, st, tag, x, y, sid):
    """Mean over both orders of x's result, or None if an order is missing."""
    s = []
    for f, g in ((x, y), (y, x)):
        p = row / f"judge_{tag}" / st / f"{f}__{g}" / f"{sid}.json"
        if not p.exists():
            return None
        w = {"1": f, "2": g, "tie": None}[json.loads(p.read_text())["verdict"]]
        s.append(0.5 if w is None else 1.0 if w == x else 0.0)
    return sum(s) / 2


def pmap(fn, items):
    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(fn, items))


def run(row, st, x, y):
    scs = json.loads((row / f"scenarios_{st}.json").read_text())
    pmap(lambda t: gen(row, st, *t), [(a, s) for a in (x, y) for s in scs])
    pmap(lambda t: judge(row, st, J1, *t), [(f, g, sc) for sc in scs for f, g in ((x, y), (y, x))])
    amb = [sc for sc in scs if score(row, st, "ds", x, y, sc["id"]) not in (0.0, 1.0)]
    pmap(lambda t: judge(row, st, J2, *t), [(f, g, sc) for sc in amb for f, g in ((x, y), (y, x))])
    report(row, st, x, y)


def boot(vals, n=10000, seed=1):
    rng, m = random.Random(seed), len(vals)
    bs = sorted(sum(vals[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def summarize(per):
    v = list(per.values())
    lo, hi = boot(v)
    return dict(n=len(v), win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)], verdict="PASS" if lo > 0.5 else "FAIL")


def report(row, st, x, y):
    """Primary: DS score, replaced by GLM score where DS orders did not agree. Also DS-only."""
    scs = json.loads((row / f"scenarios_{st}.json").read_text())
    prim, ds, tb = {}, {}, []
    for sc in scs:
        d = score(row, st, "ds", x, y, sc["id"])
        if d is None:
            continue
        ds[sc["id"]] = d
        if d in (0.0, 1.0):
            prim[sc["id"]] = d
            continue
        g = score(row, st, "glm", x, y, sc["id"])
        prim[sc["id"]] = d if g is None else g
        tb.append(sc["id"])
    res = dict(x=x, y=y, set=st, judge="DeepSeek-V4-Flash, GLM-5.2 tiebreak", tiebreak_scenarios=tb, primary=summarize(prim),
               ds_only=summarize(ds), per_scenario=prim, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    (row / f"results_{st}_{x}-vs-{y}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}, indent=1))


if __name__ == "__main__":
    row, st, ph, *xy = sys.argv[1:]
    row = D / row
    {"scen": lambda: scen(row, st), "run": lambda: run(row, st, *xy), "report": lambda: report(row, st, *xy)}[ph]()
