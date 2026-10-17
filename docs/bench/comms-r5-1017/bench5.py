#!/usr/bin/env python3
"""Round-5 bench: communication-structure + decision-brief mode vs humanizer, free PCSS models only (see PREREGISTERED.md).
usage: SPLIT=tune|held bench5.py seeds | scen | overlap | gen ARM.. | report ARM.. [--base V0]
Reuses scripts/rival_eval.py (judge v2: random 3-letter labels, analysis-before-verdict, both orders, strict else 0.5, judge cascade
GLM-5.1 -> GLM-5.2 -> gpt-oss_120b by slot-1 health, generator Qwen3.5-397B-A17B, GEN_TASK). Arms are generated once and cached; nothing is overwritten.
The judge is chosen once per split on the pooled verdicts of every arm vs RIVAL, so both arms of a paired comparison share one judge."""
import concurrent.futures as cf, json, os, re, sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parents[2] / "scripts"))
import rival_eval as R  # noqa: E402

SPLIT = os.environ.get("SPLIT", "tune")
WRITER = "DeepSeek-V4-Flash"
TAGS = {"tune": dict(ask=4, status=3, diff=2, report=1), "held": dict(ask=24, status=18, diff=9, report=9)}
JOBS = int(os.environ.get("JOBS", 4))


def seeds():
    """prompts/<split>_seeds.txt: fresh one-line topics, excluded against every earlier seed file under docs/bench."""
    tags = TAGS[SPLIT]
    out = D / "prompts" / f"{SPLIT}_seeds.txt"
    if out.exists():
        return
    old = "\n".join(l for f in sorted(D.parent.glob("*/prompts/*seeds*.txt")) if f.parent.parent != D for l in f.read_text().splitlines())
    old += "\n" + "\n".join(f.read_text() for f in D.glob("prompts/*_seeds.txt"))
    old = re.sub(r"(?m)^\d+ \[\w+\] ", "- ", old)  # topics only: old tags made the writer copy the old tag names
    desc = dict(ask="raw notes for a message to a named senior reader (VP, CFO, director, head of X) asking them to choose between two or three options, each with a cost or time figure; end the line with `(leans A)` or `(leans B)` or `(no lean)`, using no lean for about half of the seeds",
                status="raw notes for a status update to a named reader that asks for no decision (a blocker or an unknown is fine)",
                diff="a pull request description from a diff summary with test counts and one untested case, for a named reviewer",
                report="an executive summary of a long pasted report for a named executive who must decide something; end the line with `(leans X)` or `(no lean)`, no lean for about half")
    ls = []
    for tag, k in tags.items():  # one call per tag: a single mixed call kept returning the wrong tag counts
        brief = (f"Write exactly {k} one-line scenario seeds for an evaluation of an AI writing assistant. Each seed: `NN [{tag}] <topic line>`; [{tag}] = {desc[tag]}. "
                 "Every topic must be about a different subject from all earlier seeds listed below and from each other (new industries, systems, vendors, teams). Fictional only. The tag must be literally [{tag}]. "
                 f"Number from {len(ls) + 1:02d}. Output only the seed lines.\n\nEarlier seeds to avoid:\n" + old + "\n" + "\n".join(ls))
        for _ in range(6):
            txt = R.chat(WRITER, "You write evaluation seeds.", brief, max_tokens=12000, temperature=0.8)
            got = [l.strip() for l in txt.splitlines() if re.match(rf"^\W*\d+\s*\[{tag}\]", l.strip())]
            if len(got) >= k:  # the writer sometimes over-delivers: keep the first k
                got = got[:k]
                break
        assert len(got) == k, (SPLIT, tag, len(got))
        ls += [re.sub(r"^\W*\d+\s*", f"{len(ls) + i + 1:02d} ", g) for i, g in enumerate(got)]
    c = {k: sum(f"[{k}]" in l for l in ls) for k in tags}
    assert c == tags, (SPLIT, c)
    out.write_text("\n".join(ls) + "\n")


def scenarios():
    return json.loads((D / f"scenarios_{SPLIT}.json").read_text())


def scen():
    """scenarios_<split>.json from batches of 10 seeds (cached per batch, never overwritten)."""
    sd = (D / "prompts" / f"{SPLIT}_seeds.txt").read_text().splitlines()
    allv = []
    for i in range(0, len(sd), 10):
        f = D / f"scenarios_{SPLIT}_{i}.json"
        if not f.exists():
            for _ in range(3):
                txt = R.chat(WRITER, "You write evaluation scenarios.", (D / "prompts/writer_brief.txt").read_text() + "\n".join(sd[i:i + 10]) + "\n", max_tokens=32000, temperature=0.7)
                arr = R.jparse(txt)
                if isinstance(arr, list) and len(arr) == len(sd[i:i + 10]) and all(isinstance(x, dict) and {"id", "prompt"} <= set(x) for x in arr):
                    break
            else:
                raise SystemExit(f"bad scenario batch {i}")
            for k, x in enumerate(arr):
                x["id"] = f"{SPLIT[0]}{i + k + 1:02d}"
                x["tag"] = re.match(r"\d+ \[(\w+)\]", sd[i + k]).group(1)
            f.write_text(json.dumps(arr, indent=1) + "\n")
        allv += json.loads(f.read_text())
    (D / f"scenarios_{SPLIT}.json").write_text(json.dumps(allv, indent=1) + "\n")
    print(SPLIT, len(allv), "scenarios")


def overlap():
    """Max word-trigram Jaccard of each scenario against every earlier scenario file under docs/bench and (held) this round's tune set."""
    def grams(t):
        w = re.findall(r"[a-z0-9']+", t.lower())
        return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}
    old = []
    for f in D.parent.glob("*/scenarios*.json"):
        if f.parent != D:
            old += [(f.parent.name + "/" + f.name, grams(x["prompt"])) for x in json.loads(f.read_text()) if isinstance(x, dict) and "prompt" in x]
    own = [(f"own tune {x['id']}", grams(x["prompt"])) for x in json.loads((D / "scenarios_tune.json").read_text())] if SPLIT == "held" else []
    for sc in scenarios():
        g = grams(sc["prompt"])
        print(SPLIT, sc["id"], round(max((len(g & o) / len(g | o) for _, o in old + own), default=0), 3))
    print("compared against", len(old), "earlier scenarios", len(own), "own tune")


def arm_text(arm):
    return (D / "prompts" / f"{arm}.txt").read_text()


def gen(arm, sc):
    p = D / "outputs" / SPLIT / arm / f"{sc['id']}.txt"
    if p.exists():
        return
    try:
        R.save(p, R.chat(R.GEN_MODEL, arm_text(arm), R.GEN_TASK + sc["prompt"], temperature=0.3))
    except RuntimeError as e:
        print("GEN FAIL", arm, sc["id"], e)


def outs(arms):
    o = {a: {} for a in arms}
    for a in arms:
        for sc in scenarios():
            p = D / "outputs" / SPLIT / a / f"{sc['id']}.txt"
            if p.exists():
                o[a][sc["id"]] = p.read_text()
    return o


def scores(model, x, o, d, scs):
    """x vs RIVAL, both orders under judge `model` -> ({id: score}, [raw verdicts]); score per rival_eval.scenario_score."""
    sc_out, raw = {}, []
    for sc in scs:
        pair = [R.judge_one(model, sc, a, b, d, o) for a, b in ((x, "RIVAL"), ("RIVAL", x))]
        raw += [v for v in pair if v]
        if None not in pair:
            sc_out[sc["id"]] = R.scenario_score([_os(v, f, x) for v, f in zip(pair, (x, "RIVAL"))])
    return sc_out, raw


def _os(verdict, first, x):
    """Score for arm x of one judged order: first = the arm shown as Response 1."""
    if verdict == "tie":
        return 0.5
    win = first if verdict == "1" else ("RIVAL" if first == x else x)
    return 1.0 if win == x else 0.0


def report(arms, base=None):
    scs = scenarios()
    o = outs(arms + ["RIVAL"])
    scs = [s for s in scs if all(s["id"] in o[a] for a in arms + ["RIVAL"])]
    d = D / "judge" / SPLIT
    d.mkdir(parents=True, exist_ok=True)
    res, health, used = {}, {}, None
    for model in R.JUDGES:
        with cf.ThreadPoolExecutor(JOBS) as ex:
            got = list(ex.map(lambda a: scores(model, a, o, d, scs), arms))
        res[model] = {a: g[0] for a, g in zip(arms, got)}
        rate = R.slot1_rate([v for g in got for v in g[1]])
        health[model] = None if rate is None else round(rate, 3)
        if used is None and rate is not None and R.SLOT1_OK[0] <= rate <= R.SLOT1_OK[1]:
            used = model
    print(json.dumps(dict(split=SPLIT, n_scenarios=len(scs), slot1_rate=health, judge_used=used)))
    num = lambda t: set(re.findall(r"\d[\d,.]*\d|\d", t))  # noqa: E731
    for a in arms + ["RIVAL"]:
        w = [len(o[a][s["id"]].split()) for s in scs]
        fab = [len(num(o[a][s["id"]]) - num(s["prompt"])) for s in scs]
        print(json.dumps(dict(arm=a, mean_words=round(sum(w) / len(w), 1), mean_numbers_not_in_prompt=round(sum(fab) / len(fab), 2))))
    for model in R.JUDGES:
        for a in arms:
            v = list(res[model][a].values())
            if v:
                lo, hi = R.boot(v)
                print(json.dumps(dict(judge=model, primary=model == used, arm=a, n=len(v), win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)], clear_wins=v.count(1.0), clear_losses=v.count(0.0), splits_or_ties=v.count(0.5))))
            if base and a != base:
                r = res[model]
                ids = [i for i in r[a] if i in r[base]]
                if ids:
                    df = [r[a][i] - r[base][i] for i in ids]
                    lo, hi = R.boot(df)
                    print(json.dumps(dict(judge=model, primary=model == used, paired=f"{a}-{base}", n=len(ids), mean_diff=round(sum(df) / len(df), 3), ci95=[round(lo, 3), round(hi, 3)])))
                    tags = {s["id"]: s.get("tag") for s in scs}
                    for grp, pick in (("decision-asking(ask+report)", ("ask", "report")), ("no-decision(status+diff)", ("status", "diff"))):
                        g = [x for i, x in zip(ids, df) if tags.get(i) in pick]
                        if g:
                            print(json.dumps(dict(judge=model, primary=model == used, paired=f"{a}-{base}", group=grp, n=len(g), mean_diff=round(sum(g) / len(g), 3))))
    (D / f"per_scenario_{SPLIT}.json").write_text(json.dumps(dict(judge_used=used, scores=res), indent=1) + "\n")


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    base = args[args.index("--base") + 1] if "--base" in args else None
    arms = [a for a in args if not a.startswith("--") and a != base] if base else args
    if cmd == "seeds":
        seeds()
    elif cmd == "scen":
        scen()
    elif cmd == "overlap":
        overlap()
    elif cmd == "gen":
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(lambda t: gen(*t), [(a, s) for a in arms + ["RIVAL"] for s in scenarios()]))
    elif cmd == "report":
        report(arms + ([base] if base else []), base)


if __name__ == "__main__":
    main()
