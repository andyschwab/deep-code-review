#!/usr/bin/env python3
"""business-ops shipped SKILL.md vs its rival on 200 fresh held-out scenarios (PCSS only, $0). Procedure: PREREGISTERED.md. Derived from ../bizops-e-confirm-1018/bench.py.

  bench.py seeds    draw 200 fresh one-line settings (4 calls of 50), frozen once written
  bench.py write    200 scenarios s200-001..s200-200 from the harness writer brief; a scenario that is not disjoint from every earlier set is redrawn
  bench.py check    every scenario: no shared id, no identical text, 6-word-shingle overlap <= 0.10 with every earlier set and inside this set
  bench.py freeze   write SHA256-frozen.txt and the first ledger line (`preregistered`, sha256 of SHA256-frozen.txt); refuses if the ledger exists
  bench.py run      generate both arms once, judge both orders with GLM-5.1 only, write results/heldout-shipped.json (refuses before freeze)
Records are never rewritten; ledger.jsonl is append-only."""
import concurrent.futures as cf, hashlib, json, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rival_eval as R

SK, N, JOBS, MAXOV, MODEL = "business-ops", 200, 6, 0.10, R.JUDGE_MODEL
P, SCEN, SEEDS, LEDGER = HERE / "prompts", HERE / "scenarios-heldout.json", HERE / "prompts" / f"seeds_{SK}.txt", HERE / "ledger.jsonl"
SEED_ASK = ("Write {n} distinct one-line settings for test scenarios, one per line, numbered 01 to {n}, same style as the examples. "
            "Each names a fictional-style product, who buys it and one tension. Cover many different industries and company sizes; "
            "avoid the example industries. About half should hinge on a legal, tax, accounting or regulatory question, the rest on pricing, "
            "unit economics, runway, market sizing or fundraising.\n\nTopic: {topic}\n\nExamples (do not reuse):\n{ex}\n")
TOPIC = "a founder or operator with a money or compliance question on taking a product to market (pricing, unit economics, runway, market sizing, legal, tax, fundraising)"
TEXT_KEYS = ("prompt", "ticket", "text")


def led(event, **kw):
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **kw}) + "\n")


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def earlier():
    """(ids, [(shingles, normalized text)]) of every scenario in every JSON set under docs/bench and scripts/eval-fixtures, except this directory and judge/outputs/results records."""
    ids, pool = set(), []
    for base in (ROOT / "docs/bench", ROOT / "scripts/eval-fixtures"):
        for f in base.rglob("*.json"):
            if HERE in f.parents or {"judge", "outputs", "results"} & set(f.parts):
                continue
            try:
                d = json.loads(f.read_text())
            except ValueError:
                continue
            for x in (d.get("scenarios", []) if isinstance(d, dict) else d) if isinstance(d, (list, dict)) else []:
                t = next((x[k] for k in TEXT_KEYS if isinstance(x, dict) and isinstance(x.get(k), str)), None)
                if t:
                    ids.add(x.get("id"))
                    pool.append((R.shingles(t), R.norm(t)))
    return ids, pool


def clash(x, ids, pool):
    """Why scenario x is not disjoint from the pool (or None). Pool entries are (shingles, normalized text)."""
    sh, n = R.shingles(x["prompt"]), R.norm(x["prompt"])
    if x["id"] in ids:
        return "id clash"
    for s, m in pool:
        if n == m:
            return "identical text"
        if len(sh & s) / max(1, min(len(sh), len(s))) > MAXOV:
            return "shingle overlap above %.2f" % MAXOV
    return None


FOCUS = ("physical goods and food", "software and developer tools", "health, care and wellness", "education and training", "finance, insurance and property",
         "media, games and creator products", "industrial, energy and logistics", "marketplaces, travel and local services")


def seeds():
    assert not SEEDS.exists(), "seeds are frozen"
    ex = "\n".join((R.FIX / SK / "seeds.txt").read_text().splitlines()[:5])
    strip = lambda l: re.sub(r"^\s*\d+[.)]?\s*", "", l).strip()
    files = [R.FIX / SK / "seeds.txt", *(ROOT / "docs/bench").rglob(f"seeds_{SK}*.txt")]
    seen = {R.norm(strip(l)) for fn in files if HERE not in fn.parents for l in fn.read_text().splitlines() if l.strip()}
    got = []
    for k in range(24):  # calls of 50 until N lines that are new against every earlier seed line and this draw
        if len(got) >= N:
            break
        txt = R.chat(R.GEN_MODEL, "You write evaluation settings.", SEED_ASK.format(n=50, topic=TOPIC, ex=ex) + f"\nFocus this batch on: {FOCUS[k % len(FOCUS)]}.\n", max_tokens=12000, temperature=0.9)
        for l in (strip(l) for l in txt.splitlines() if re.match(r"\s*\d+", l)):
            if R.norm(l) not in seen and len(got) < N:
                seen.add(R.norm(l))
                got.append(l)
    if len(got) < N:
        raise SystemExit(f"seed writer produced {len(got)} new lines, need {N}")
    SEEDS.parent.mkdir(exist_ok=True)
    SEEDS.write_text("".join(f"{i % 10 + 1:02d} {l}\n" for i, l in enumerate(got)))


def draw(brief, use):
    """One writer call for the given seed lines -> list of prompts (same length) or None when the reply is unusable."""
    txt = R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief.replace("{N}", str(len(use))) + "\n" + "\n".join(use) + "\n", max_tokens=12000, temperature=0.7)
    arr = R.jparse(txt)
    if not isinstance(arr, list):  # writer sometimes answers "NN" then the text, no JSON
        bits = re.split(r"(?m)^(\d\d)[ \t]*\n?", txt)
        arr = [{"id": i, "prompt": " ".join(b.split())} for i, b in zip(bits[1::2], bits[2::2]) if b.strip()]
    if isinstance(arr, list) and len(arr) == len(use) and all(isinstance(x, dict) and isinstance(x.get("prompt"), str) for x in arr):
        return [x["prompt"] for x in arr]


def write():
    assert not SCEN.exists(), "scenarios are frozen"
    seeds_, brief = SEEDS.read_text().splitlines(), (R.FIX / SK / "brief.txt").read_text()
    ids, pool = earlier()
    out = {}
    for i in range(0, N, 10):
        todo = list(range(i, i + 10))
        for _ in range(12):
            if not todo:
                break
            ps = draw(brief, [seeds_[j] for j in todo])
            if ps is None:
                continue
            left = []
            for j, p in zip(todo, ps):
                x = {"id": f"s200-{j + 1:03d}", "setting": seeds_[j], "prompt": p}
                if clash(x, ids, pool):
                    left.append(j)
                else:
                    out[j] = x
                    pool.append((R.shingles(p), R.norm(p)))
            todo = left
        if todo:
            raise SystemExit(f"seeds {[seeds_[j] for j in todo]} cannot pass the disjointness check in 12 rounds")
    SCEN.write_text(json.dumps([out[j] for j in range(N)], indent=1) + "\n")


def scen():
    return json.loads(SCEN.read_text())


def check():
    ids, pool = earlier()
    bad = []
    for x in scen():
        why = clash(x, ids, pool)
        bad += [f"{x['id']} {why}"] if why else []
        ids.add(x["id"])
        pool.append((R.shingles(x["prompt"]), R.norm(x["prompt"])))
    print(SK, len(scen()), f"vs {len(pool) - len(scen())} earlier scenarios:", "BAD: " + "; ".join(bad) if bad else "clean")
    return not bad


def freeze():
    assert not LEDGER.exists(), "already frozen"
    assert check() and len(scen()) == N, "scenarios not clean"
    files = ["PREREGISTERED.md", "bench.py", "prompts/perun_business-ops_shipped.txt", "prompts/rival_business-ops.txt", f"prompts/seeds_{SK}.txt", "scenarios-heldout.json",
             f"../../../scripts/eval-fixtures/rival/{SK}/brief.txt", "../../../scripts/rival_eval.py"]
    (HERE / "SHA256-frozen.txt").write_text("".join(f"{fsha(HERE / f)}  {f}\n" for f in files))
    led("preregistered", sha256=fsha(HERE / "SHA256-frozen.txt"))


def run():
    assert LEDGER.exists() and json.loads(LEDGER.read_text().splitlines()[0])["event"] == "preregistered", "freeze first"
    scs = scen()
    arms = {"PERUN": P / "perun_business-ops_shipped.txt", "RIVAL": P / "rival_business-ops.txt"}

    def gen(t):
        a, sc = t
        p = HERE / "outputs" / a / f"{sc['id']}.txt"
        if not p.exists():
            R.save(p, R.chat(R.GEN_MODEL, arms[a].read_text(), R.GEN_TASK + sc["prompt"], temperature=0.3))
        return p.read_text()

    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(gen, [(a, s) for a in arms for s in scs]))
    outs = {a: {s["id"]: gen((a, s)) for s in scs} for a in arms}
    led("gen", arms=list(arms), n=len(scs), outputs_sha256={a: hashlib.sha256("".join(outs[a][s["id"]] for s in scs).encode()).hexdigest() for a in arms})
    both = lambda s: (s["id"], [R.judge_one(MODEL, s, x, y, HERE / "judge", outs) for x, y in (("PERUN", "RIVAL"), ("RIVAL", "PERUN"))])
    with cf.ThreadPoolExecutor(JOBS) as ex:
        vs = dict(ex.map(both, scs))
    rate = R.slot1_rate([x for pair in vs.values() for x in pair])
    f = HERE / "results" / "heldout-shipped.json"
    assert not f.exists(), f"{f} exists: records are never overwritten"
    failed = sum(None in p for p in vs.values())
    per = {i: 0.5 if None in p else R.scenario_score([R.order_score(x, o) for x, o in zip(p, ("PERUN", "RIVAL"))]) for i, p in vs.items()}
    v = list(per.values())
    lo, hi = R.boot(v)
    healthy = rate is not None and R.SLOT1_OK[0] <= rate <= R.SLOT1_OK[1]
    res = dict(skill=SK, arm="shipped", split="heldout", n=len(v), judge=MODEL, slot1_rate=None if rate is None else round(rate, 3), judge_healthy=healthy,
               win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)], wins=v.count(1.0), ties=v.count(0.5), losses=v.count(0.0),
               failed_judge_orders=failed, superior=bool(lo > 0.5 and healthy), per_scenario=per, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps(res, indent=1) + "\n")
    led("judge", judge=MODEL, result_sha256=fsha(f), win_rate=res["win_rate"], ci95=res["ci95"], slot1_rate=res["slot1_rate"], failed_judge_orders=failed, superior=res["superior"])
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


if __name__ == "__main__":
    {"seeds": seeds, "write": write, "check": check, "freeze": freeze, "run": run}[sys.argv[1]]()
