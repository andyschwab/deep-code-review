#!/usr/bin/env python3
"""Round 5 driver, idea-critic only (see PREREGISTERED.md). Reuses ../exec-1017/bench.py (PCSS call, bootstrap, JSON parse). PCSS only; PCSS_ENV must
point at a file holding PCSS_KEY (never printed). Records are never overwritten: a judge record is written only when all six calls parsed, a
generation only when absent, and a second pass over the same tag is a no-op.
usage: bench5.py scen | seed SPLIT | rival | run ARM SPLIT JP | report ARM SPLIT JP
SPLIT: tune (old scenarios 01-10) | pilot (round-4 held-out, judge-prompt check only) | h5 (scenarios5/, h01-h40).  JP: judge prompt v1 | v2.
ARM: v0 | c5 (prompts/perun_idea-critic_<ARM>.txt).  `seed` copies the already-generated round-4 v0 and RIVAL answers for tune/pilot (no regeneration)."""
import concurrent.futures as cf, hashlib, json, random, shutil, subprocess, sys, tempfile
from pathlib import Path

H = Path(__file__).resolve().parent
X, R4 = H.parent / "exec-1017", H.parent / "idea-critic-r4-1017"
sys.path.insert(0, str(X))
import bench as b

b.D = H  # ledger goes to this directory
ROOT = H.parents[2]
JUDGES = [("GLM-5.1", True), ("GLM-5.2", True), ("gpt-oss_120b", False)]  # (model, thinking off); the generator Qwen3.5-397B-A17B never judges
SK = "idea-critic"


def load(split):
    if split == "tune":
        return [s for s in json.loads((X / "scenarios" / f"{SK}.json").read_text()) if s["split"] == "tune"]
    f = R4 / "scenarios4" / f"{SK}-h4.json" if split == "pilot" else H / "scenarios5" / f"{SK}-h5.json"
    return json.loads(f.read_text())


def out(arm, split, i):
    return H / "outputs" / split / arm / f"{i}.txt"


def clean(text):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "s.txt").write_text(text)
        return subprocess.run(["bash", str(ROOT / "scripts/ci-gates.sh"), "privacy", "--banlist", str(ROOT / ".banlist.txt"), d], capture_output=True).returncode == 0


def scen():
    f = H / "scenarios5" / f"{SK}-h5.json"
    if f.exists():
        return print("cached", f)
    seeds = (H / "prompts" / "seeds5.txt").read_text().strip().splitlines()
    sysm, brief = (X / "prompts" / "writer_common.txt").read_text(), (X / "prompts" / f"writer_{SK}.txt").read_text()

    def one(i):
        for _ in range(4):
            t = b.call(b.WRITER, sysm, f"{brief}\nSetting: {seeds[i]}\nWrite the scenario now.", f"scen5/{i}", 4000, 0.9)
            if 100 <= len(t.split()) <= 280 and clean(t):
                return dict(id=f"h{i + 1:02d}", split="h5", setting=seeds[i], prompt=t)
        raise SystemExit(f"scenario {i} failed word-count or privacy screen after 4 tries")

    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        arr = list(ex.map(one, range(len(seeds))))
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps(arr, indent=1) + "\n")


def seed(split):
    """Copy the existing round-4 answers (v0 and RIVAL, generated once there) for tune and pilot."""
    for s in load(split):
        for arm in ("v0", "RIVAL"):
            src = R4 / "outputs" / SK / ("RIVAL" if arm == "RIVAL" else "PERUN_v0") / f"{s['id']}.txt"
            if not out(arm, split, s["id"]).exists():
                out(arm, split, s["id"]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, out(arm, split, s["id"]))


def gen(arm, split, s):
    p = out(arm, split, s["id"])
    if p.exists():
        return
    f = X / "prompts" / f"rival_{SK}.txt" if arm == "RIVAL" else H / "prompts" / f"perun_{SK}_{arm}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    t = b.call(b.GEN, f.read_text(), (X / "prompts" / "gen_task.txt").read_text() + s["prompt"], f"gen5/{split}/{arm}/{s['id']}", 3000, 0.7, True)
    p.write_text(t) if t else print("GEN FAIL", arm, split, s["id"])


def sha(split):
    return {s["id"]: hashlib.sha256(out("RIVAL", split, s["id"]).read_bytes()).hexdigest() for s in load(split)}


def rival():
    """h5 RIVAL answers, each generated exactly once, then frozen; run refuses to start if they change."""
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        list(ex.map(lambda s: gen("RIVAL", "h5", s), load("h5")))
    f = H / "RIVAL-sha256-h5.json"
    assert not f.exists(), "RIVAL already frozen"
    f.write_text(json.dumps(sha("h5"), indent=1) + "\n")


def one(model, nothink, jp, s, first, second, split, tag):
    prompt = f"REQUEST:\n{s['prompt']}\n\n=== Response 1 ===\n{out(first, split, s['id']).read_text()}\n\n=== Response 2 ===\n{out(second, split, s['id']).read_text()}\n"
    for _ in range(2):
        j = b.jparse(b.call(model, (H / "prompts" / f"judge_{jp}.txt").read_text(), prompt, tag, 2500, 0.0, no_think=nothink))
        if isinstance(j, dict) and j.get("verdict") in ("1", "2", "tie"):
            return dict(winner={"1": first, "2": second, "tie": "tie"}[j["verdict"]], slot=j["verdict"], reason=j.get("reason", ""))
    return None


def judge(arm, split, jp, s):
    p = H / "judge5" / jp / split / arm / f"{s['id']}.json"
    if p.exists():
        return
    votes, verdicts = {}, []
    for model, nt in JUDGES:
        o = [arm, "RIVAL"]
        random.Random(f"{jp}-{arm}-{s['id']}-{model}").shuffle(o)
        r = [one(model, nt, jp, s, x, y, split, f"judge5/{jp}/{split}/{arm}/{s['id']}/{model}/{k}") for k, (x, y) in enumerate((o, o[::-1]))]
        w = [x["winner"] if x else "fail" for x in r]
        v = w[0] if w[0] == w[1] and w[0] in (arm, "RIVAL") else "tie"
        votes[model] = dict(orders=r, verdict=v)
        verdicts.append(v)
    if any(x is None for v in votes.values() for x in v["orders"]):
        return print("INCOMPLETE (not written; rerun)", jp, split, arm, s["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x") as f:  # 'x': never overwrite a complete record
        f.write(json.dumps(dict(votes=votes, final=next((x for x in (arm, "RIVAL") if verdicts.count(x) >= 2), "tie")), indent=1) + "\n")


def run(arm, split, jp):
    scs = load(split)
    if split == "h5":
        f = H / "RIVAL-sha256-h5.json"
        assert f.exists() and json.loads(f.read_text()) == sha("h5"), "RIVAL files missing or changed since frozen"
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        list(ex.map(lambda s: gen(arm, split, s), scs))
        list(ex.map(lambda s: judge(arm, split, jp, s), scs))
    report(arm, split, jp)


def report(arm, split, jp):
    per, recs = {}, []
    for s in load(split):
        p = H / "judge5" / jp / split / arm / f"{s['id']}.json"
        if p.exists():
            recs.append(json.loads(p.read_text()))
            per[s["id"]] = {arm: 1.0, "RIVAL": 0.0}.get(recs[-1]["final"], 0.5)
    v = list(per.values())
    cells = [x for r in recs for m in r["votes"].values() for x in [m["orders"]]]
    dis = sum(1 for o in cells if o[0]["winner"] != o[1]["winner"])
    res = dict(arm=arm, split=split, judge_prompt=jp, n=len(v), win_rate=round(sum(v) / len(v), 3) if v else None,
               wins_ties_losses=[v.count(1.0), v.count(0.5), v.count(0.0)], order_disagree_rate=round(dis / len(cells), 3) if cells else None,
               judges=[m for m, _ in JUDGES], per_scenario=per, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
    if v:
        lo, hi = b.boot(v)
        res.update(ci95=[round(lo, 3), round(hi, 3)])
    slots = {m: [x["slot"] for r in recs for x in r["votes"][m]["orders"]] for m, _ in JUDGES}
    res["slot1_rate"] = {m: round(s.count("1") / len(s), 3) for m, s in slots.items() if s}
    (H / f"results5-{arm}-{split}-{jp}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in res if k != "per_scenario"}))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"scen": scen, "seed": seed, "rival": rival, "run": run, "report": report}[c](*a)
