#!/usr/bin/env python3
"""business-ops "lead with the call" against its rival, round 5 (PCSS only, $0). Procedure: PREREGISTERED.md.
Derived from ../bizops-r4-1017/bench.py; reuses scripts/rival_eval.py for the PCSS call, generator wrapper, neutral-label judge, cascade and bootstrap.

  bench.py seeds                  draw 70 fresh one-line settings (10 tune + 60 held-out)
  mkvariants.py                   (separate script) build prompts/perun_business-ops_<arm>.txt
  bench.py write SPLIT            tune (10, ids t01-t10) or heldout (60, ids h01-h60) from the harness writer brief
  bench.py check                  no identical prompt and no 6-word-shingle overlap above 0.3 with any earlier business-ops set or between splits
  bench.py run SPLIT ARM [ARM..]  generate (rival once, shared), judge with the first healthy cascade judge, write results/<split>-<arm>.json
  bench.py paired SPLIT EDIT      per-scenario (EDIT - v0) bootstrap, write results/paired-<split>-<edit>.json
Judge cascade (R.JUDGES): GLM-5.1, then GLM-5.2, then gpt-oss_120b; the first whose slot-1 rate over every verdict of the split lies in 0.4-0.6
scores all arms of the split. Both orders, a scenario counts only when both agree, else 0.5. Qwen3.5-397B-A17B generates and writes; it never judges.
Existing records are never overwritten."""
import concurrent.futures as cf, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "scripts"))
import rival_eval as R

P, SK = HERE / "prompts", "business-ops"
SPLITS = {"tune": ("t", 10), "heldout": ("h", 60)}
JOBS = 6
SEED_ASK = ("Write {n} distinct one-line settings for test scenarios, one per line, numbered 01 to {n}, same style as the examples. "
            "Each names a fictional-style product, who buys it and one tension. Cover many different industries and company sizes; "
            "avoid the example industries. About half should hinge on a legal, tax, accounting or regulatory question, the rest on pricing, "
            "unit economics, runway, market sizing or fundraising.\n\nTopic: {topic}\n\nExamples (do not reuse):\n{ex}\n")
TOPIC = "a founder or operator with a money or compliance question on taking a product to market (pricing, unit economics, runway, market sizing, legal, tax, fundraising)"


def scen(split):
    return json.loads((HERE / "scenarios" / f"{SK}-{split}.json").read_text())


def seeds():
    f = P / f"seeds_{SK}.txt"
    assert not f.exists(), "seeds are frozen"
    ex = "\n".join((R.FIX / SK / "seeds.txt").read_text().splitlines()[:5])
    used = "\n".join(l[3:] for fn in (HERE.parent / "bizops-r4-1017/prior/seeds_business-ops-r3.txt", HERE.parent / "bizops-r4-1017/prompts/seeds_business-ops.txt")
                     for l in fn.read_text().splitlines())
    for _ in range(2):  # one whole redraw allowed
        txt = R.chat(R.GEN_MODEL, "You write evaluation settings.", SEED_ASK.format(n=70, topic=TOPIC, ex=ex) + "\nAlready used, do not repeat any of these products or industries:\n" + used + "\n", max_tokens=12000, temperature=0.9)
        lines = [re.sub(r"^\s*\d+[.)]?\s*", "", l).strip() for l in txt.splitlines() if re.match(r"\s*\d+", l)]
        if len(lines) == 70 and len(set(lines)) == 70:
            f.write_text("".join(f"{i + 1:02d} {l}\n" for i, l in enumerate(lines)))
            return
    raise SystemExit("seed writer failed twice")


def write(split):
    pre, n = SPLITS[split]
    out_f = HERE / "scenarios" / f"{SK}-{split}.json"
    assert not out_f.exists(), "scenarios are frozen"
    seeds_ = [l for l in (P / f"seeds_{SK}.txt").read_text().splitlines() if l[:2].isdigit()]
    use_all = seeds_[:10] if split == "tune" else seeds_[10:]
    brief, out = (R.FIX / SK / "brief.txt").read_text(), []
    for i in range(0, n, 10):
        use = use_all[i:i + 10]
        for _ in range(12):
            txt = R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief.replace("{N}", str(len(use))) + "\n" + "\n".join(use) + "\n", max_tokens=12000, temperature=0.7)
            arr = R.jparse(txt)
            if not isinstance(arr, list):
                bits = re.split(r"(?m)^(\d\d)[ \t]*\n?", txt)
                arr = [{"id": i, "prompt": " ".join(b.split())} for i, b in zip(bits[1::2], bits[2::2]) if b.strip()]
            if isinstance(arr, list) and len(arr) == len(use) and all(isinstance(x, dict) and "prompt" in x for x in arr):
                out += [{"id": f"{pre}{i + k + 1:02d}", "setting": u, "prompt": x["prompt"]} for k, (u, x) in enumerate(zip(use, arr))]
                break
        else:
            raise SystemExit(f"{split}: writer failed on batch {i}")
    (HERE / "scenarios").mkdir(exist_ok=True)
    out_f.write_text(json.dumps(out, indent=1) + "\n")


def check():
    root = HERE.parent.parent.parent
    files = list((R.FIX / SK).glob("*.json")) + list(HERE.parent.glob(f"**/*{SK}*.json")) + list(HERE.parent.glob("**/scenarios*/*business*.json"))
    old = [x["prompt"] for f in set(files) if f.name != "rival.json" and "bizops-call" not in str(f)
           for x in (json.loads(f.read_text()) if f.read_text().lstrip().startswith("[") else []) if isinstance(x, dict) and "prompt" in x]
    pool, bad = [(R.shingles(p), R.norm(p)) for p in old], []
    for sp in SPLITS:
        if not (HERE / "scenarios" / f"{SK}-{sp}.json").exists():
            continue
        for x in scen(sp):
            sh, n = R.shingles(x["prompt"]), R.norm(x["prompt"])
            if any(n == m or len(sh & s) / max(1, min(len(sh), len(s))) > 0.3 for s, m in pool):
                bad.append(f"{sp}/{x['id']} overlaps an earlier set")
            pool.append((sh, n))
    print(SK, {s: len(scen(s)) for s in SPLITS if (HERE / "scenarios" / f"{SK}-{s}.json").exists()}, f"vs {len(old)} earlier prompts:", "BAD: " + "; ".join(bad) if bad else "clean")
    return not bad


def gen(arm, sc):
    p = HERE / "outputs" / arm / f"{sc['id']}.txt"
    if not p.exists():
        R.save(p, R.chat(R.GEN_MODEL, (P / (f"rival_{SK}.txt" if arm == "RIVAL" else f"perun_{SK}_{arm}.txt")).read_text(), R.GEN_TASK + sc["prompt"], temperature=0.3))
    return p.read_text()


def run(split, *arms):
    scs = scen(split)
    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(lambda t: gen(*t), [(a, s) for a in ("RIVAL", *arms) for s in scs]))
    outs = {a: {s["id"]: gen(a, s) for s in scs} for a in ("RIVAL", *arms)}
    health, used, vs = {}, None, {}
    for model in R.JUDGES:
        def both(t, model=model):
            a, sc = t
            o = {"PERUN": outs[a], "RIVAL": outs["RIVAL"]}
            return (a, sc["id"]), [R.judge_one(model, sc, x, y, HERE / "judge" / a, o) for x, y in (("PERUN", "RIVAL"), ("RIVAL", "PERUN"))]
        with cf.ThreadPoolExecutor(JOBS) as ex:
            vs = dict(ex.map(both, [(a, s) for a in arms for s in scs]))
        rate = R.slot1_rate([x for pair in vs.values() for x in pair])
        health[model] = None if rate is None else round(rate, 3)
        if rate is not None and R.SLOT1_OK[0] <= rate <= R.SLOT1_OK[1]:
            used = model
            break
    if used is None:
        raise SystemExit(f"no healthy judge {health}: the split gets no verdict")
    (HERE / "results").mkdir(exist_ok=True)
    for a in arms:
        f, per, failed = HERE / "results" / f"{split}-{a}.json", {}, 0
        assert not f.exists(), f"{f} exists: records are never overwritten"
        for s in scs:
            pair = vs[(a, s["id"])]
            failed += None in pair
            per[s["id"]] = 0.5 if None in pair else R.scenario_score([R.order_score(x, o) for x, o in zip(pair, ("PERUN", "RIVAL"))])
        v = list(per.values())
        lo, hi = R.boot(v)
        res = dict(skill=SK, arm=a, split=split, n=len(v), judge=used, slot1_rate=health, win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)],
                   wins=v.count(1.0), ties=v.count(0.5), losses=v.count(0.0), failed_judge_orders=failed, per_scenario=per,
                   bootstrap="10000 resamples, seed 1, percentile, over scenarios")
        f.write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


def paired(split, edit):
    a, b = (json.loads((HERE / "results" / f"{split}-{x}.json").read_text()) for x in (edit, "v0"))
    assert a["judge"] == b["judge"] and a["per_scenario"].keys() == b["per_scenario"].keys()
    d = [a["per_scenario"][k] - b["per_scenario"][k] for k in a["per_scenario"]]
    lo, hi = R.boot(d)
    res = dict(split=split, edit=edit, n=len(d), judge=a["judge"], paired_diff=round(sum(d) / len(d), 3), ci95=[round(lo, 3), round(hi, 3)],
               edit_win_rate=a["win_rate"], edit_ci95=a["ci95"], v0_win_rate=b["win_rate"], v0_ci95=b["ci95"],
               ship=bool(split == "heldout" and lo > 0), superior=bool(split == "heldout" and a["ci95"][0] > 0.5))
    f = HERE / "results" / f"paired-{split}-{edit}.json"
    assert not f.exists(), f"{f} exists: records are never overwritten"
    f.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"seeds": seeds, "write": write, "check": check, "run": run, "paired": paired}[c](*a)
