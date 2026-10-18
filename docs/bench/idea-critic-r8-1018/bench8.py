#!/usr/bin/env python3
"""Round 8 driver, idea-critic only (see PREREGISTERED.md). Derived from ../idea-critic-r7-1017/bench7.py; reuses ../exec-1017/bench.py (PCSS call, bootstrap,
JSON parse). PCSS only; PCSS_ENV must point at a file holding PCSS_KEY (never printed). Records are never overwritten: a judge record is written only
when all six calls parsed, a generation only when absent. BANLIST points the privacy gate at a banlist whose sibling .banlist.local.txt it reads in place.
usage: bench8.py seeds | scen SET | check | rival SET | run SET ARM | report SET ARM | choose | paired SET ARM
SET: tune (20 scenarios, ids r8t-001..) | held (60 scenarios, ids r8-001..). ARM: v0 | c8a | c8b (prompts/perun_idea-critic_<ARM>.txt)."""
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
SK, JP = "idea-critic", "v2"
SIZE = {"tune": 20, "held": 60}
PFX = {"tune": "r8t", "held": "r8"}


def scen_file(st):
    return H / f"scenarios8-{st}.json"  # at the dir root, where scripts/bench_check.py looks


def load(st):
    return json.loads(scen_file(st).read_text())


def out(st, arm, i):
    return H / "outputs" / st / arm / f"{i}.txt"


def clean(text):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "s.txt").write_text(text)
        return subprocess.run(["bash", str(ROOT / "scripts/ci-gates.sh"), "privacy", "--banlist", BAN, d], capture_output=True).returncode == 0


def earlier():
    """All text under docs/bench outside this directory, the eval fixtures, idea-critic evals, plus every earlier scenario dict that has a prompt."""
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
    """80 fresh fictional settings with unique invented company names (20 tune + 60 held), drawn by the writer model, screened against every earlier file."""
    f = H / "prompts" / "seeds8.txt"
    assert not f.exists(), "seeds already frozen"
    old, _ = earlier()
    n = sum(SIZE.values())
    got, tries = [], 0
    while len(got) < n and tries < 16:
        tries += 1
        t = b.call(b.WRITER, "You invent fictional business settings for test scenarios.",
                   "List 40 varied, distinct settings, one per line, each exactly: a short description of an organisation weighing a plan, then an invented, unusual two-word "
                   "company name in parentheses, e.g. 'a regional freight broker building an in-house load-matching app (Quillfeather Logistics)'. Mix industries, sizes and "
                   f"countries; no real brands, no markdown, no numbering. Batch {tries}.", f"seeds8/{tries}", 4000, 0.9)
        for ln in t.splitlines():
            m = re.search(r"\(([A-Z][\w'&-]+(?: [A-Z][\w'&-]+)+)\)\s*$", ln.strip())
            if m and m.group(1).lower() not in old.lower() and not any(m.group(1) in g for g in got) and clean(ln):
                got.append(ln.strip())
    assert len(got) >= n, f"only {len(got)} seeds"
    f.write_text("\n".join(got[:n]) + "\n")


def scen(st):
    if scen_file(st).exists():
        return print("cached", scen_file(st))
    allseeds = (H / "prompts" / "seeds8.txt").read_text().strip().splitlines()
    seeds_ = allseeds[:SIZE["tune"]] if st == "tune" else allseeds[SIZE["tune"]:]
    sysm, brief = (X / "prompts" / "writer_common.txt").read_text(), (X / "prompts" / f"writer_{SK}.txt").read_text()

    def one(i):
        for _ in range(4):
            t = b.call(b.WRITER, sysm, f"{brief}\nSetting: {seeds_[i]}\nWrite the scenario now.", f"scen8/{st}/{i}", 4000, 0.9)
            if 100 <= len(t.split()) <= 280 and clean(t):
                return dict(id=f"{PFX[st]}-{i + 1:03d}", split=st, setting=seeds_[i], prompt=t)
        raise SystemExit(f"scenario {st}/{i} failed word-count or privacy screen after 4 tries")

    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        arr = list(ex.map(one, range(len(seeds_))))
    scen_file(st).write_text(json.dumps(arr, indent=1) + "\n")


def words(t):
    return re.findall(r"\w+", t.lower())


def sh(t, k):
    w = words(t)
    return {tuple(w[i:i + k]) for i in range(len(w) - k + 1)}


def check():
    """Disjointness from every earlier idea-critic set and between tune and held: ids, company names, exact texts, 30-word shingles (none allowed) and
    10-word shingles (share <= 0.2 after overlap-allow.txt template phrases, the scripts/bench_check.py rule)."""
    old, olds = earlier()
    ok = set().union(*[sh(l, 10) for l in (H / "overlap-allow.txt").read_text().splitlines() if l.strip()])
    pool = {"30": set().union(*[sh(s["prompt"], 30) for s in olds]), "10": set().union(*[sh(s["prompt"], 10) for s in olds]) - ok}
    ids, texts = {s["id"] for s in olds}, {s["prompt"] for s in olds}
    bad, mine = [], []
    for st in ("tune", "held"):
        for s in load(st):
            nm = re.search(r"\(([^)]+)\)\s*$", s["setting"]).group(1)
            s10 = sh(s["prompt"], 10) - ok
            r = len(s10 & pool["10"]) / len(s10) if s10 else 0
            if s["id"] in ids or nm.lower() in old.lower() or s["prompt"] in texts or sh(s["prompt"], 30) & pool["30"] or r > 0.2:
                bad.append(s["id"])
            mine.append((st, s["id"], nm, s["prompt"]))
    for k, (st, i, nm, t) in enumerate(mine):  # within the round (tune and held): names, texts, allow-listed 10-word ratio (addendum 1)
        for st2, i2, nm2, t2 in mine[k + 1:]:
            if nm == nm2 or t == t2 or len((sh(t, 10) & sh(t2, 10)) - ok) > 0.2 * max(1, len(sh(t, 10) - ok)):
                bad.append(f"{i}~{i2}")
    print(f"earlier scenarios {len(olds)}; r8 tune {len(load('tune'))} held {len(load('held'))}; overlaps {bad or 'none'}")
    assert not bad


def gen(st, arm, s):
    p = out(st, arm, s["id"])
    if p.exists():
        return
    f = X / "prompts" / f"rival_{SK}.txt" if arm == "RIVAL" else H / "prompts" / f"perun_{SK}_{arm}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    t = b.call(b.GEN, f.read_text(), (X / "prompts" / "gen_task.txt").read_text() + s["prompt"], f"gen8/{st}/{arm}/{s['id']}", 3000, 0.7, True)
    p.write_text(t) if t else print("GEN FAIL", arm, s["id"])


def sha(st):
    return {s["id"]: hashlib.sha256(out(st, "RIVAL", s["id"]).read_bytes()).hexdigest() for s in load(st)}


def rival(st):
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        list(ex.map(lambda s: gen(st, "RIVAL", s), load(st)))
    f = H / f"RIVAL-sha256-{st}.json"
    assert not f.exists(), "RIVAL already frozen"
    f.write_text(json.dumps(sha(st), indent=1) + "\n")


def one(model, nothink, s, st, first, second, tag):
    prompt = f"REQUEST:\n{s['prompt']}\n\n=== Response 1 ===\n{out(st, first, s['id']).read_text()}\n\n=== Response 2 ===\n{out(st, second, s['id']).read_text()}\n"
    for _ in range(2):
        j = b.jparse(b.call(model, (H / "prompts" / f"judge_{JP}.txt").read_text(), prompt, tag, 2500, 0.0, no_think=nothink))
        if isinstance(j, dict) and j.get("verdict") in ("1", "2", "tie"):
            return dict(winner={"1": first, "2": second, "tie": "tie"}[j["verdict"]], slot=j["verdict"], reason=j.get("reason", ""))
    return None


def judge(st, arm, s):
    p = H / "judge8" / JP / st / arm / f"{s['id']}.json"
    if p.exists():
        return
    votes, verdicts = {}, []
    for model, nt in JUDGES:
        o = [arm, "RIVAL"]
        random.Random(f"{JP}-{arm}-{s['id']}-{model}").shuffle(o)
        r = [one(model, nt, s, st, x, y, f"judge8/{st}/{arm}/{s['id']}/{model}/{k}") for k, (x, y) in enumerate((o, o[::-1]))]
        w = [x["winner"] if x else "fail" for x in r]
        v = w[0] if w[0] == w[1] and w[0] in (arm, "RIVAL") else "tie"
        votes[model] = dict(orders=r, verdict=v)
        verdicts.append(v)
    if any(x is None for v in votes.values() for x in v["orders"]):
        return print("INCOMPLETE (not written; rerun)", arm, s["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x") as f:  # 'x': never overwrite a complete record
        f.write(json.dumps(dict(votes=votes, final=next((x for x in (arm, "RIVAL") if verdicts.count(x) >= 2), "tie")), indent=1) + "\n")


def run(st, arm):
    f = H / f"RIVAL-sha256-{st}.json"
    assert f.exists() and json.loads(f.read_text()) == sha(st), "RIVAL files missing or changed since frozen"
    scs = load(st)
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        list(ex.map(lambda s: gen(st, arm, s), scs))
        list(ex.map(lambda s: judge(st, arm, s), scs))
    report(st, arm)


def scores(st, arm):
    per, recs = {}, []
    for s in load(st):
        p = H / "judge8" / JP / st / arm / f"{s['id']}.json"
        if p.exists():
            recs.append(json.loads(p.read_text()))
            per[s["id"]] = {arm: 1.0, "RIVAL": 0.0}.get(recs[-1]["final"], 0.5)
    return per, recs


def report(st, arm):
    per, recs = scores(st, arm)
    v = list(per.values())
    cells = [m["orders"] for r in recs for m in r["votes"].values()]
    dis = sum(1 for o in cells if o[0]["winner"] != o[1]["winner"])
    res = dict(arm=arm, split=st, judge_prompt=JP, n=len(v), win_rate=round(sum(v) / len(v), 3) if v else None,
               wins_ties_losses=[v.count(1.0), v.count(0.5), v.count(0.0)], order_disagree_rate=round(dis / len(cells), 3) if cells else None,
               judges=[m for m, _ in JUDGES], per_scenario=per, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    if v:
        lo, hi = b.boot(v)
        res.update(ci95=[round(lo, 3), round(hi, 3)])
    slots = {m: [x["slot"] for r in recs for x in r["votes"][m]["orders"]] for m, _ in JUDGES}
    res["slot1_rate"] = {m: round(s.count("1") / len(s), 3) for m, s in slots.items() if s}
    (H / f"results8-{arm}-{st}-{JP}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


def diff(st, arm):
    """Paired arm - v0 over the same scenarios: 10,000 resamples of scenarios, seed 1, percentile 95% interval."""
    a, c = scores(st, "v0")[0], scores(st, arm)[0]
    ids = sorted(set(a) & set(c))
    d = [c[i] - a[i] for i in ids]
    rng, m, n = random.Random(1), len(ids), 10000
    bs = sorted(sum(d[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    cl = b.boot([c[i] for i in ids])
    return dict(arm=arm, split=st, n=m, edit_minus_v0=round(sum(d) / m, 4), paired_ci95=[round(bs[int(0.025 * n)], 4), round(bs[int(0.975 * n) - 1], 4)],
                edit_win_rate=round(sum(c[i] for i in ids) / m, 3), edit_win_rate_ci95=[round(cl[0], 3), round(cl[1], 3)],
                bootstrap="10000 resamples, seed 1, percentile, over scenarios")


def choose():
    """Tune rule (PREREGISTERED.md section 4): the candidate with the larger tune paired difference over v0 goes to held-out; a tie goes to c8a."""
    r = {a: diff("tune", a) for a in ("c8a", "c8b")}
    pick = "c8b" if r["c8b"]["edit_minus_v0"] > r["c8a"]["edit_minus_v0"] else "c8a"
    res = dict(chosen=pick, tune=r)
    (H / "CHOICE.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


def paired(st, arm):
    """Held-out decision per PREREGISTERED.md section 4."""
    res = diff(st, arm)
    res.update(ship=res["paired_ci95"][0] > 0, superior_to_rival=res["edit_win_rate_ci95"][0] > 0.5)
    (H / f"results8-paired-{arm}-{st}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"seeds": seeds, "scen": scen, "check": check, "rival": rival, "run": run, "report": report, "choose": choose, "paired": paired}[c](*a)
