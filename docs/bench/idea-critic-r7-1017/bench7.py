#!/usr/bin/env python3
"""Round 7 driver, idea-critic only (see PREREGISTERED.md). Derived from ../idea-critic-r6-1017/bench6.py; reuses ../exec-1017/bench.py (PCSS call, bootstrap,
JSON parse). PCSS only; PCSS_ENV must point at a file holding PCSS_KEY (never printed). Records are never overwritten: a judge record is written only
when all six calls parsed, a generation only when absent. BANLIST points the privacy gate at a banlist whose sibling .banlist.local.txt it reads in place.
usage: bench7.py seeds | scen | check | rival | run ARM | report ARM | paired
ARM: v0 | c6 (prompts/perun_idea-critic_<ARM>.txt). Scenario ids are r7-001..r7-100."""
import concurrent.futures as cf, glob, hashlib, json, os, random, re, subprocess, sys, tempfile
from pathlib import Path

H = Path(__file__).resolve().parent
X = H.parent / "exec-1017"
sys.path.insert(0, str(X))
import bench as b

b.D = H  # ledger goes to this directory
ROOT = H.parents[2]
BAN = os.environ.get("BANLIST", str(ROOT / ".banlist.txt"))
JUDGES = [("GLM-5.1", True), ("GLM-5.2", True), ("gpt-oss_120b", False)]  # (model, thinking off); the generator Qwen3.5-397B-A17B never judges
SK, N, JP, SP = "idea-critic", 100, "v2", "r7"
SCEN = H / "scenarios7" / f"{SK}-r7.json"


def load():
    return json.loads(SCEN.read_text())


def out(arm, i):
    return H / "outputs" / SP / arm / f"{i}.txt"


def clean(text):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "s.txt").write_text(text)
        return subprocess.run(["bash", str(ROOT / "scripts/ci-gates.sh"), "privacy", "--banlist", BAN, d], capture_output=True).returncode == 0


def earlier():
    """All text under docs/bench outside this directory, the eval fixtures, idea-critic evals, plus every earlier scenario (id, prompt)."""
    txt, scs = "", []
    roots = (H.parent, ROOT / "scripts" / "eval-fixtures", ROOT / ".claude" / "skills" / "idea-critic" / "evals")
    for f in [g for r in roots for g in glob.glob(str(r / "**" / "*"), recursive=True)]:
        p = Path(f)
        if p.is_file() and H not in p.parents and p.suffix in (".json", ".md", ".txt", ".jsonl", ".py", ".tsv"):
            t = p.read_text(errors="ignore")
            txt += t
            if p.suffix == ".json":
                try:
                    j = json.loads(t)
                except ValueError:
                    continue
                scs += [x for x in (j if isinstance(j, list) else []) if isinstance(x, dict) and "prompt" in x]
    return txt, scs


def seeds():
    """100 fresh fictional settings with unique invented company names, drawn by the writer model, screened against every earlier file."""
    f = H / "prompts" / "seeds7.txt"
    assert not f.exists(), "seeds already frozen"
    old, _ = earlier()
    got, tries = [], 0
    while len(got) < N and tries < 12:
        tries += 1
        t = b.call(b.WRITER, "You invent fictional business settings for test scenarios.",
                   "List 40 varied, distinct settings, one per line, each exactly: a short description of an organisation weighing a plan, then an invented, unusual two-word "
                   "company name in parentheses, e.g. 'a regional freight broker building an in-house load-matching app (Quillfeather Logistics)'. Mix industries, sizes and "
                   f"countries; no real brands, no markdown, no numbering. Batch {tries}.", f"seeds7/{tries}", 4000, 0.9)
        for ln in t.splitlines():
            m = re.search(r"\(([A-Z][\w'&-]+(?: [A-Z][\w'&-]+)+)\)\s*$", ln.strip())
            if m and m.group(1).lower() not in old.lower() and not any(m.group(1) in g for g in got) and clean(ln):
                got.append(ln.strip())
    assert len(got) >= N, f"only {len(got)} seeds"
    f.write_text("\n".join(got[:N]) + "\n")


def scen():
    if SCEN.exists():
        return print("cached", SCEN)
    seeds_ = (H / "prompts" / "seeds7.txt").read_text().strip().splitlines()
    sysm, brief = (X / "prompts" / "writer_common.txt").read_text(), (X / "prompts" / f"writer_{SK}.txt").read_text()

    def one(i):
        for _ in range(4):
            t = b.call(b.WRITER, sysm, f"{brief}\nSetting: {seeds_[i]}\nWrite the scenario now.", f"scen7/{i}", 4000, 0.9)
            if 100 <= len(t.split()) <= 280 and clean(t):
                return dict(id=f"r7-{i + 1:03d}", split=SP, setting=seeds_[i], prompt=t)
        raise SystemExit(f"scenario {i} failed word-count or privacy screen after 4 tries")

    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        arr = list(ex.map(one, range(len(seeds_))))
    SCEN.parent.mkdir(exist_ok=True)
    SCEN.write_text(json.dumps(arr, indent=1) + "\n")


def check():
    """Disjointness from every earlier round: ids, company names, exact texts and 30-word shingles."""
    old, olds = earlier()
    sh = lambda t: {tuple(w) for w in zip(*[t.lower().split()[k:] for k in range(30)])}  # noqa: E731
    oldsh = set().union(*[sh(s["prompt"]) for s in olds])
    ids = {s["id"] for s in olds}
    bad = []
    for s in load():
        nm = re.search(r"\(([^)]+)\)\s*$", s["setting"]).group(1)
        if s["id"] in ids or nm.lower() in old.lower() or s["prompt"] in {o["prompt"] for o in olds} or sh(s["prompt"]) & oldsh:
            bad.append(s["id"])
    print(f"earlier scenarios {len(olds)}; r7 n={len(load())}; overlaps {bad or 'none'}")
    assert not bad


def gen(arm, s):
    p = out(arm, s["id"])
    if p.exists():
        return
    f = X / "prompts" / f"rival_{SK}.txt" if arm == "RIVAL" else H / "prompts" / f"perun_{SK}_{arm}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    t = b.call(b.GEN, f.read_text(), (X / "prompts" / "gen_task.txt").read_text() + s["prompt"], f"gen7/{arm}/{s['id']}", 3000, 0.7, True)
    p.write_text(t) if t else print("GEN FAIL", arm, s["id"])


def sha():
    return {s["id"]: hashlib.sha256(out("RIVAL", s["id"]).read_bytes()).hexdigest() for s in load()}


def rival():
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        list(ex.map(lambda s: gen("RIVAL", s), load()))
    f = H / "RIVAL-sha256-r7.json"
    assert not f.exists(), "RIVAL already frozen"
    f.write_text(json.dumps(sha(), indent=1) + "\n")


def one(model, nothink, s, first, second, tag):
    prompt = f"REQUEST:\n{s['prompt']}\n\n=== Response 1 ===\n{out(first, s['id']).read_text()}\n\n=== Response 2 ===\n{out(second, s['id']).read_text()}\n"
    for _ in range(2):
        j = b.jparse(b.call(model, (H / "prompts" / f"judge_{JP}.txt").read_text(), prompt, tag, 2500, 0.0, no_think=nothink))
        if isinstance(j, dict) and j.get("verdict") in ("1", "2", "tie"):
            return dict(winner={"1": first, "2": second, "tie": "tie"}[j["verdict"]], slot=j["verdict"], reason=j.get("reason", ""))
    return None


def judge(arm, s):
    p = H / "judge7" / JP / SP / arm / f"{s['id']}.json"
    if p.exists():
        return
    votes, verdicts = {}, []
    for model, nt in JUDGES:
        o = [arm, "RIVAL"]
        random.Random(f"{JP}-{arm}-{s['id']}-{model}").shuffle(o)
        r = [one(model, nt, s, x, y, f"judge7/{arm}/{s['id']}/{model}/{k}") for k, (x, y) in enumerate((o, o[::-1]))]
        w = [x["winner"] if x else "fail" for x in r]
        v = w[0] if w[0] == w[1] and w[0] in (arm, "RIVAL") else "tie"
        votes[model] = dict(orders=r, verdict=v)
        verdicts.append(v)
    if any(x is None for v in votes.values() for x in v["orders"]):
        return print("INCOMPLETE (not written; rerun)", arm, s["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x") as f:  # 'x': never overwrite a complete record
        f.write(json.dumps(dict(votes=votes, final=next((x for x in (arm, "RIVAL") if verdicts.count(x) >= 2), "tie")), indent=1) + "\n")


def run(arm):
    f = H / "RIVAL-sha256-r7.json"
    assert f.exists() and json.loads(f.read_text()) == sha(), "RIVAL files missing or changed since frozen"
    scs = load()
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        list(ex.map(lambda s: gen(arm, s), scs))
        list(ex.map(lambda s: judge(arm, s), scs))
    report(arm)


def scores(arm):
    per, recs = {}, []
    for s in load():
        p = H / "judge7" / JP / SP / arm / f"{s['id']}.json"
        if p.exists():
            recs.append(json.loads(p.read_text()))
            per[s["id"]] = {arm: 1.0, "RIVAL": 0.0}.get(recs[-1]["final"], 0.5)
    return per, recs


def report(arm):
    per, recs = scores(arm)
    v = list(per.values())
    cells = [m["orders"] for r in recs for m in r["votes"].values()]
    dis = sum(1 for o in cells if o[0]["winner"] != o[1]["winner"])
    res = dict(arm=arm, split=SP, judge_prompt=JP, n=len(v), win_rate=round(sum(v) / len(v), 3) if v else None,
               wins_ties_losses=[v.count(1.0), v.count(0.5), v.count(0.0)], order_disagree_rate=round(dis / len(cells), 3) if cells else None,
               judges=[m for m, _ in JUDGES], per_scenario=per, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    if v:
        lo, hi = b.boot(v)
        res.update(ci95=[round(lo, 3), round(hi, 3)])
    slots = {m: [x["slot"] for r in recs for x in r["votes"][m]["orders"]] for m, _ in JUDGES}
    res["slot1_rate"] = {m: round(s.count("1") / len(s), 3) for m, s in slots.items() if s}
    (H / f"results7-{arm}-{SP}-{JP}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


def paired():
    """Paired c6 - v0 over the same scenarios: 10,000 resamples of scenarios, seed 1, percentile 95% interval; decision per PREREGISTERED.md section 4."""
    a, c = scores("v0")[0], scores("c6")[0]
    ids = sorted(set(a) & set(c))
    d = [c[i] - a[i] for i in ids]
    rng, m, n = random.Random(1), len(ids), 10000
    bs = sorted(sum(d[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    lo, hi = bs[int(0.025 * n)], bs[int(0.975 * n) - 1]
    cl = b.boot([c[i] for i in ids])
    res = dict(n=m, c6_minus_v0=round(sum(d) / m, 4), paired_ci95=[round(lo, 4), round(hi, 4)], c6_win_rate_ci95=[round(cl[0], 3), round(cl[1], 3)],
               ship_c6=lo > 0, c6_superior_to_rival=cl[0] > 0.5, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    (H / "results7-paired.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"seeds": seeds, "scen": scen, "check": check, "rival": rival, "run": run, "report": report, "paired": paired}[c](*a)
