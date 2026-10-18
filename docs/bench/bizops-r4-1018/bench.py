#!/usr/bin/env python3
"""business-ops SKILL.md edit (round 4, 2026-10-18) against the shipped text and its rival (PCSS only, $0). Procedure: PREREGISTERED.md. Derived from ../bizops-sup-1018/bench.py.

  bench.py mkvariants   build prompts/variants/perun_business-ops_{a,b,c}.txt from the shipped SKILL.md plus one snippet each
  bench.py tune         generate each variant on the 200 scenarios of ../bizops-sup-1018 (spent: tune data only), judge against that run's rival outputs,
                        compare with that run's shipped scores; records go to ledger-tune.jsonl and tune/, never to ledger.jsonl
  bench.py seeds        draw 150 fresh one-line settings, frozen once written
  bench.py write        150 scenarios r4-001..r4-150 from the harness writer brief, redrawn until disjoint from every earlier set
  bench.py check        every scenario: no shared id, no identical text, 6-word-shingle overlap <= 0.10 with every earlier set and inside this set
  bench.py freeze       write SHA256-frozen.txt and the first ledger line (`preregistered`); refuses if the ledger exists
  bench.py run          generate SHIPPED, EDIT and RIVAL once, judge EDIT and SHIPPED against RIVAL (GLM-5.1 only, both orders), write results/heldout.json
Records are never rewritten; both ledgers are append-only."""
import concurrent.futures as cf, hashlib, json, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rival_eval as R

SK, N, JOBS, MAXOV, MODEL = "business-ops", 150, 6, 0.10, R.JUDGE_MODEL
P, SCEN, SEEDS, LEDGER, TUNE_LEDGER = HERE / "prompts", HERE / "scenarios-heldout.json", HERE / "prompts" / f"seeds_{SK}.txt", HERE / "ledger.jsonl", HERE / "ledger-tune.jsonl"
SUP = ROOT / "docs/bench/bizops-sup-1018"
SKILL = ROOT / ".claude/skills/business-ops/SKILL.md"
SEED_ASK = ("Write {n} distinct one-line settings for test scenarios, one per line, numbered 01 to {n}, same style as the examples. "
            "Each names a fictional-style product, who buys it and one tension. Cover many different industries and company sizes; "
            "avoid the example industries. About half should hinge on a legal, tax, accounting or regulatory question, the rest on pricing, "
            "unit economics, runway, market sizing or fundraising.\n\nTopic: {topic}\n\nExamples (do not reuse):\n{ex}\n")
TOPIC = "a founder or operator with a money or compliance question on taking a product to market (pricing, unit economics, runway, market sizing, legal, tax, fundraising)"
TEXT_KEYS = ("prompt", "ticket", "text")
FOCUS = ("physical goods and food", "software and developer tools", "health, care and wellness", "education and training", "finance, insurance and property",
         "media, games and creator products", "industrial, energy and logistics", "marketplaces, travel and local services")

# Candidate snippets: each is inserted into the shipped SKILL.md right before the line that starts `Do not print "tier"`.
ANCHOR = 'Do not print "tier" or "Lane" labels'
VARIANTS = {
    "a": ("Work the arithmetic before you commit to the call. Use every figure the user gave (fees, shipping, add-on and recurring revenue all count), "
          "write each calculation once from top to bottom, and make the call agree with the result: when an input is missing, state the call as a "
          "threshold (\"you go negative only if beans cost over $X\"). Do not print \"Wait\", \"Correction\" or a recomputation; if a line fails a sanity "
          "check, show only the corrected line. Introduce no input the user did not give (burn, volume, inventory) as a fact: an assumption is "
          "labelled ASSUMED and bracketed."),
    "b": ("Answer every question the user asks, in their order, each with its own labelled result (a number, a rule or a verdict). If a requested "
          "figure needs an input the user did not give, give the closed form in that variable and one worked example at a labelled assumption, "
          "not a request to come back with more data. End on the decision, not on a list of inputs to gather."),
    "c": ("For a legal, tax, accounting or regulatory question, tier 2 carries the weight: name the specific rule, test, threshold or treaty position "
          "by its name and say what usually follows from it on the user's facts (labelled usual treatment, UNVERIFIED where you are unsure), so the "
          "reader leaves with the substance and the routing note stays at two lines. A bare \"consult a professional\" with no rule stated fails."),
}


def led(event, ledger=None, **kw):
    with open(ledger or LEDGER, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **kw}) + "\n")


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mkvariants():
    base = SKILL.read_text()
    assert base.count(ANCHOR) == 1
    (P / "variants").mkdir(parents=True, exist_ok=True)
    for k, snip in VARIANTS.items():
        (P / "variants" / f"perun_{SK}_{k}.txt").write_text(base.replace(ANCHOR, snip + "\n\n" + ANCHOR))


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
                x = {"id": f"r4-{j + 1:03d}", "setting": seeds_[j], "prompt": p}
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
    files = ["PREREGISTERED.md", "bench.py", "prompts/perun_business-ops_shipped.txt", "prompts/perun_business-ops_edit.txt", "prompts/rival_business-ops.txt", f"prompts/seeds_{SK}.txt",
             "scenarios-heldout.json", f"../../../scripts/eval-fixtures/rival/{SK}/brief.txt", "../../../scripts/rival_eval.py"]
    (HERE / "SHA256-frozen.txt").write_text("".join(f"{fsha(HERE / f)}  {f}\n" for f in files))
    led("preregistered", sha256=fsha(HERE / "SHA256-frozen.txt"))


def gen_all(arms, scs, outdir):
    """Generate every (arm, scenario) answer once (cached on disk); arms = {name: prompt path}. Returns {arm: {id: text}}."""
    def gen(t):
        a, sc = t
        p = outdir / a / f"{sc['id']}.txt"
        if not p.exists():
            R.save(p, R.chat(R.GEN_MODEL, arms[a].read_text(), R.GEN_TASK + sc["prompt"], temperature=0.3))
        return p.read_text()

    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(gen, [(a, s) for a in arms for s in scs]))
    return {a: {s["id"]: gen((a, s)) for s in scs} for a in arms}


def judge_vs_rival(scs, edit_outs, rival_outs, jdir):
    """Edit (as PERUN) against the rival, both orders -> ({id: score}, slot-1 rate, failed orders)."""
    outs = {"PERUN": edit_outs, "RIVAL": rival_outs}
    both = lambda s: (s["id"], [R.judge_one(MODEL, s, x, y, jdir, outs) for x, y in (("PERUN", "RIVAL"), ("RIVAL", "PERUN"))])
    with cf.ThreadPoolExecutor(JOBS) as ex:
        vs = dict(ex.map(both, scs))
    per = {i: 0.5 if None in p else R.scenario_score([R.order_score(x, o) for x, o in zip(p, ("PERUN", "RIVAL"))]) for i, p in vs.items()}
    return per, R.slot1_rate([x for pair in vs.values() for x in pair]), sum(None in p for p in vs.values())


def summ(v, ref=None):
    """Win rate with CI, W/T/L; with ref (scores of the shipped text on the same scenarios) also the paired difference with CI."""
    lo, hi = R.boot(v)
    r = dict(n=len(v), win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)], wins=v.count(1.0), ties=v.count(0.5), losses=v.count(0.0))
    if ref:
        d = [a - b for a, b in zip(v, ref)]
        dl, dh = R.boot(d)
        r["paired_vs_shipped"] = dict(mean=round(sum(d) / len(d), 3), ci95=[round(dl, 3), round(dh, 3)])
    return r


def tune():
    """Tune data only: the 200 scenarios of ../bizops-sup-1018 are spent. Shipped score = that run's per-scenario scores."""
    scs = json.loads((SUP / "scenarios-heldout.json").read_text())
    rival = {s["id"]: (SUP / "outputs/RIVAL" / f"{s['id']}.txt").read_text() for s in scs}
    base = json.loads((SUP / "results/heldout-shipped.json").read_text())["per_scenario"]
    ref = [base[s["id"]] for s in scs]
    res = {"shipped": summ(ref)}
    for k in VARIANTS:
        name = f"tune-{k}"
        outs = gen_all({name: P / "variants" / f"perun_{SK}_{k}.txt"}, scs, HERE / "tune/outputs")[name]
        per, rate, failed = judge_vs_rival(scs, outs, rival, HERE / "tune/judge")
        res[k] = dict(summ([per[s["id"]] for s in scs], ref), slot1_rate=None if rate is None else round(rate, 3), failed_judge_orders=failed)
        led("tune", TUNE_LEDGER, variant=k, prompt_sha256=fsha(P / "variants" / f"perun_{SK}_{k}.txt"), **res[k])
    (HERE / "tune/results.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


def run():
    assert LEDGER.exists() and json.loads(LEDGER.read_text().splitlines()[0])["event"] == "preregistered", "freeze first"
    scs = scen()
    arms = {"SHIPPED": P / "perun_business-ops_shipped.txt", "EDIT": P / "perun_business-ops_edit.txt", "RIVAL": P / "rival_business-ops.txt"}
    outs = gen_all(arms, scs, HERE / "outputs")
    led("gen", arms=list(arms), n=len(scs), outputs_sha256={a: hashlib.sha256("".join(outs[a][s["id"]] for s in scs).encode()).hexdigest() for a in arms})
    f = HERE / "results" / "heldout.json"
    assert not f.exists(), f"{f} exists: records are never overwritten"
    ids = [s["id"] for s in scs]
    sh, shr, shf = judge_vs_rival(scs, outs["SHIPPED"], outs["RIVAL"], HERE / "judge/shipped")
    ed, edr, edf = judge_vs_rival(scs, outs["EDIT"], outs["RIVAL"], HERE / "judge/edit")
    ref, v = [sh[i] for i in ids], [ed[i] for i in ids]
    healthy = lambda r: r is not None and R.SLOT1_OK[0] <= r <= R.SLOT1_OK[1]
    e, s = summ(v, ref), summ(ref)
    ship = e["paired_vs_shipped"]["ci95"][0] > 0
    win = e["ci95"][0] > 0.5 and healthy(edr)
    res = dict(skill=SK, split="heldout", judge=MODEL, bootstrap="10000 resamples, seed 1, percentile, over scenarios",
               edit=dict(e, slot1_rate=None if edr is None else round(edr, 3), failed_judge_orders=edf, vs_rival_win_claim=win),
               shipped=dict(s, slot1_rate=None if shr is None else round(shr, 3), failed_judge_orders=shf), ship_edit=ship,
               per_scenario={"edit": ed, "shipped": sh})
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps(res, indent=1) + "\n")
    led("judge", judge=MODEL, result_sha256=fsha(f), edit=res["edit"], shipped=res["shipped"], ship_edit=ship)
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


if __name__ == "__main__":
    {"mkvariants": mkvariants, "tune": tune, "seeds": seeds, "write": write, "check": check, "freeze": freeze, "run": run}[sys.argv[1]]()
