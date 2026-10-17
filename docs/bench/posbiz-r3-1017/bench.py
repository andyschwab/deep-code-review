#!/usr/bin/env python3
"""positioning and business-ops against their rivals, round 3 (PCSS only, $0). Procedure: PREREGISTERED.md.

  bench.py seeds                 draw 50 fresh one-line settings per skill (writer: Qwen, never shown skill text)
  bench.py mkvariants            build prompts/perun_<skill>_<arm>.txt from the unedited SKILL.md plus the candidate snippets
  bench.py write SKILL SPLIT     SPLIT tune (10 scenarios, ids t01-t10) or heldout (40, ids h01-h40) from the harness writer brief
  bench.py check SKILL           scenario hygiene: no identical prompt, no 6-word-shingle overlap above 0.3 with earlier sets or between splits
  bench.py run SKILL ARM SPLIT   generate (rival once per scenario), judge with three judges in both orders, write results-*.json
Reuses scripts/rival_eval.py for the PCSS call, the generator wrapper, the judge prompt and the bootstrap. Qwen generates and
writes scenarios and never judges. Judges: DeepSeek-V4-Flash, GLM-5.2 (thinking off), MiniMax-M2.5; each sees both orders and
counts only when both agree, else tie; the majority of the three decides, else tie (0.5)."""
import concurrent.futures as cf, json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "scripts"))
import rival_eval as R

P = HERE / "prompts"
SKILLS = ("positioning", "business-ops")
JUDGES = ("DeepSeek-V4-Flash", "GLM-5.2", "MiniMax-M2.5")
SPLITS = {"tune": ("t", 10), "heldout": ("h", 40)}
JOBS = 6
SEED_ASK = ("Write {n} distinct one-line settings for test scenarios, one per line, numbered 01 to {n}, same style as the examples. "
            "Each names a fictional-style product, who buys it and one tension. Cover many different industries and company sizes; "
            "avoid the example industries.\n\nTopic: {topic}\n\nExamples (do not reuse):\n{ex}\n")
TOPIC = {"positioning": "a founder or product marketer deciding how to position a product in its market",
         "business-ops": "a founder or operator with a money or compliance question on taking a product to market (pricing, unit economics, runway, market sizing, legal, tax, fundraising)"}


def brief(skill):
    return (R.FIX / skill / "brief.txt").read_text()


def seeds():
    for sk in SKILLS:
        ex = "\n".join((R.FIX / sk / "seeds.txt").read_text().splitlines()[:5])
        txt = R.chat(R.GEN_MODEL, "You write evaluation settings.", SEED_ASK.format(n=50, topic=TOPIC[sk], ex=ex), max_tokens=8000, temperature=0.9)
        lines = [re.sub(r"^\s*\d+[.)]?\s*", "", l).strip() for l in txt.splitlines() if re.match(r"\s*\d+", l)]
        assert len(lines) == 50 and len(set(lines)) == 50, f"{sk}: got {len(lines)} lines"
        (P / f"seeds_{sk}.txt").write_text("".join(f"{i + 1:02d} {l}\n" for i, l in enumerate(lines)))


def write(skill, split):
    pre, n = SPLITS[split]
    seeds = [l for l in (P / f"seeds_{skill}.txt").read_text().splitlines() if l[:2].isdigit()]
    use_all = seeds[:10] if split == "tune" else seeds[10:]
    out = []
    for i in range(0, n, 10):
        use = use_all[i:i + 10]
        for _ in range(12):
            txt = R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief(skill).replace("{N}", str(len(use))) + "\n" + "\n".join(use) + "\n", max_tokens=12000, temperature=0.7)
            arr = R.jparse(txt)
            if not isinstance(arr, list):  # writer ignored JSON: "NN" header lines followed by prose
                bits = re.split(r"(?m)^(\d\d)[ \t]*\n?", txt)
                arr = [{"id": i, "prompt": " ".join(b.split())} for i, b in zip(bits[1::2], bits[2::2]) if b.strip()]
            if isinstance(arr, list) and len(arr) == len(use) and all(isinstance(x, dict) and "prompt" in x for x in arr):
                out += [{"id": f"{pre}{i + k + 1:02d}", "setting": u, "prompt": x["prompt"]} for k, (u, x) in enumerate(zip(use, arr))]
                break
        else:
            raise SystemExit(f"{skill}/{split}: writer failed on batch {i}")
    (HERE / "scenarios").mkdir(exist_ok=True)
    (HERE / "scenarios" / f"{skill}-{split}.json").write_text(json.dumps(out, indent=1) + "\n")


def check(skill):
    old = [x["prompt"] for f in list((R.FIX / skill).glob("*.json")) + list((HERE.parent / "exec-1017").glob(f"scenarios*/{skill}*.json"))
           if f.name != "rival.json" for x in json.loads(f.read_text()) if isinstance(x, dict) and "prompt" in x]
    mine = {s: scen(skill, s) for s in SPLITS if (HERE / "scenarios" / f"{skill}-{s}.json").exists()}
    pool = [(R.shingles(p), R.norm(p)) for p in old]
    bad = []
    for sp, arr in mine.items():
        for x in arr:
            sh, n = R.shingles(x["prompt"]), R.norm(x["prompt"])
            if any(n == m or len(sh & s) / max(1, min(len(sh), len(s))) > 0.3 for s, m in pool):
                bad.append(f"{sp}/{x['id']} overlaps an earlier set")
            pool.append((sh, n))
    print(skill, {s: len(a) for s, a in mine.items()}, "BAD: " + "; ".join(bad) if bad else "clean")
    return not bad


def scen(skill, split):
    return json.loads((HERE / "scenarios" / f"{skill}-{split}.json").read_text())


def arm_system(skill, arm):
    if arm == "RIVAL":
        p = P / f"rival_{skill}.txt"
        if not p.exists():
            p.write_text(R.arm_text(skill, "RIVAL"))
        return p.read_text()
    return (P / f"perun_{skill}_{arm}.txt").read_text()


def gen(skill, arm, sc):
    p = HERE / "outputs" / skill / arm / f"{sc['id']}.txt"
    if not p.exists():
        R.save(p, R.chat(R.GEN_MODEL, arm_system(skill, arm), R.GEN_TASK + sc["prompt"], temperature=0.3))
    return p.read_text()


def one(model, sc, first, second, outs):
    user = f"REQUEST:\n{sc['prompt']}\n\n=== Response 1 ===\n{outs[first]}\n\n=== Response 2 ===\n{outs[second]}\n"
    for _ in range(2):
        try:
            j = R.jparse(R.chat(model, R.JUDGE_SYSTEM, user, max_tokens=3000))
        except RuntimeError:
            continue
        if isinstance(j, dict) and j.get("verdict") in ("1", "2", "tie"):
            return dict(winner={"1": first, "2": second, "tie": "tie"}[j["verdict"]], slot=j["verdict"], reason=str(j.get("reason", "")))
    return None


def judge(skill, arm, sc):
    p = HERE / "judge" / skill / arm / f"{sc['id']}.json"
    if p.exists():
        return
    outs = {a: gen(skill, a, sc) for a in (arm, "RIVAL")}
    votes, verdicts = {}, []
    for m in JUDGES:
        o = [arm, "RIVAL"]
        random.Random(f"{skill}-{arm}-{sc['id']}-{m}").shuffle(o)
        r = [one(m, sc, x, y, outs) for x, y in (o, o[::-1])]
        w = [x["winner"] if x else "fail" for x in r]
        v = w[0] if w[0] == w[1] and w[0] in (arm, "RIVAL") else "tie"
        votes[m] = dict(orders=r, verdict=v)
        verdicts.append(v)
    final = next((x for x in (arm, "RIVAL") if verdicts.count(x) >= 2), "tie")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(votes=votes, final=final), indent=1) + "\n")


def score(v, arm):
    return {arm: 1.0, "RIVAL": 0.0}.get(v, 0.5)


def report(skill, arm, split):
    recs = {sc["id"]: json.loads((HERE / "judge" / skill / arm / f"{sc['id']}.json").read_text()) for sc in scen(skill, split)
            if (HERE / "judge" / skill / arm / f"{sc['id']}.json").exists()}
    per = {k: score(r["final"], arm) for k, r in recs.items()}
    v = list(per.values())
    res = dict(skill=skill, arm=arm, split=split, n=len(v), win_rate=round(sum(v) / len(v), 3) if v else None, per_scenario=per,
               wins=v.count(1.0), ties=v.count(0.5), losses=v.count(0.0), bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    if v:
        lo, hi = R.boot(v)
        res.update(ci95=[round(lo, 3), round(hi, 3)])
    slots = {m: [x["slot"] for r in recs.values() for x in r["votes"][m]["orders"] if x] for m in JUDGES}
    res["slot1_rate"] = {m: round(s.count("1") / len(s), 3) for m, s in slots.items() if s}
    res["per_judge"] = {}
    for m in JUDGES:  # sensitivity only, never the verdict
        s = [score(r["votes"][m]["verdict"], arm) for r in recs.values()]
        if s:
            res["per_judge"][m] = dict(win_rate=round(sum(s) / len(s), 3), ci95=[round(x, 3) for x in R.boot(s)])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"{skill}-{arm}-{split}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


def run(skill, arm, split):
    scs = scen(skill, split)
    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(lambda t: gen(skill, *t), [(a, s) for a in (arm, "RIVAL") for s in scs]))
    with cf.ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(lambda s: judge(skill, arm, s), scs))
    report(skill, arm, split)


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"seeds": seeds, "write": write, "check": check, "run": run, "report": report, "mkvariants": lambda: __import__("mkvariants").main()}[c](*a)
