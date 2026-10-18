#!/usr/bin/env python3
"""product-output-safety round 1 (2026-10-18): one targeted SKILL.md edit (prompts/edit.md) against the unedited skill (prompts/v0.md)
and the promptfoo redteam-setup rival (prompts/rival.txt), judged with scripts/rival_eval.py judge protocol v2 (unchanged).

usage: bench.py seeds | scenarios | sha NAME | prereg | run tune|held [--jobs N]
  seeds      80 fresh seeds (20 tune + 60 held), none close to any earlier bench seed
  scenarios  write them in batches of 10 from the skill's own writer brief; reject any scenario whose 6-word shingles overlap the
             docs/bench corpus (other dirs) or each other by more than 10%; write scenarios-tune.json and scenarios-heldout.json
  sha NAME   write SHA256-NAME.txt over the freeze list
  prereg     write the FIRST line of ledger.jsonl: event "preregistered" + sha256 of SHA256-frozen.txt; refuses if ledger.jsonl exists
  run SPLIT  generate v0, edit and rival once per scenario, judge edit-vs-rival and v0-vs-rival, write <split>/results.json;
             tune logs to ledger-tune.jsonl, held logs to ledger.jsonl; refuses to overwrite a results file
Needs PCSS_KEY in the environment (never printed).
"""
import argparse, concurrent.futures as cf, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rival_eval as R  # noqa: E402

P = HERE / "prompts"
ARMS = {"V0": P / "v0.md", "EDIT": P / "edit.md", "RIVAL": P / "rival.txt"}
SPLITS = {"tune": ("t", 20), "held": ("h", 60)}  # id prefix, n; ids sr1t01.. / sr1h01..
MAX_OVERLAP, BATCH = 0.10, 10
TOPIC = "a product team making a feature safe before launch, where the feature's own AI outputs or automated decisions reach end users and could harm them"
FREEZE = ["PREREGISTERED.md", "bench.py", "prompts/v0.md", "prompts/edit.md", "prompts/rival.txt", "prompts/writer_brief.txt",
          "seeds.txt", "scenarios-tune.json", "scenarios-heldout.json"]


def words(t):
    return set(re.findall(r"[a-z]{3,}", t.lower()))


def near(seed, others, thr=0.5):
    a = words(seed)
    return any(len(a & words(o)) / max(1, min(len(a), len(words(o)))) > thr for o in others)


def corpus():
    """6-word shingles of every text file under docs/bench (other dirs; raw outputs and judge records excluded) and the rival fixtures."""
    ps = [p for p in (ROOT / "docs/bench").rglob("*") if p.is_file() and p.suffix in (".json", ".txt", ".md", ".py", ".jsonl")
          and not {"outputs", "judge", "run"} & set(p.parts) and HERE not in p.parents and p.stat().st_size < 4_000_000]
    ps += list((ROOT / "scripts/eval-fixtures/rival").rglob("*.json")) + list((ROOT / "scripts/eval-fixtures/rival").rglob("*.txt"))
    out = set()
    for p in ps:
        out |= R.shingles(p.read_text(errors="ignore").replace("\\n", " "))
    return out


def overlap(prompt, sh):
    s = R.shingles(prompt)
    return len(s & sh) / max(1, len(s))


def old_seeds():
    out = []
    for p in list((ROOT / "docs/bench").rglob("seeds*.txt")) + list((ROOT / "scripts/eval-fixtures/rival").rglob("seeds.txt")):
        if HERE not in p.parents:
            out += [re.sub(r"^\d+\s+", "", l) for l in p.read_text().splitlines() if re.match(r"\d\d ", l)]
    return out


def seeds():
    old, keep = old_seeds(), []
    mine = [re.sub(r"^\d+\s+", "", l) for l in (ROOT / "docs/bench/pos-1016/prompts/seeds_A.txt").read_text().splitlines() if re.match(r"\d\d ", l)]
    for _ in range(8):
        txt = R.chat(R.GEN_MODEL, "You write evaluation scenario seeds.", (
            f"Write 80 one-line seeds, one per line, no numbering, no commentary. Each seed is a distinct work situation about {TOPIC}. "
            "Vary industry, company size, stage, team size, constraint and country; fictional only. Each is 8 to 20 words, plain text. "
            "Do not repeat any of these:\n" + "\n".join(mine[:30])), max_tokens=6000, temperature=0.9)
        for l in txt.splitlines():
            l = re.sub(r"^[\s\-*\d.)]+", "", l).strip()
            if 5 <= len(l.split()) <= 30 and not near(l, old + keep):
                keep.append(l)
        if len(keep) >= 80:
            break
    assert len(keep) >= 80, f"only {len(keep)} seeds"
    (HERE / "seeds.txt").write_text("\n".join(f"{i:02d} {l}" for i, l in enumerate(keep[:80], 1)) + "\n")


def as_list(txt):
    arr = R.jparse(txt)
    if isinstance(arr, dict):
        arr = next(iter(arr.values())) if len(arr) == 1 and isinstance(next(iter(arr.values())), list) else [arr]
    if not isinstance(arr, list):  # "NN" header lines plus prose
        bits = re.split(r"(?m)^(\d\d)[ \t]*$", txt)
        arr = [{"id": i, "prompt": b.strip()} for i, b in zip(bits[1::2], bits[2::2]) if b.strip()]
    return arr


def write_batch(brief, batch, sh):
    """Per position, keep the first draw that passes the length and overlap checks; redraw the whole batch (so the brief's per-position
    pressure rule still holds) until every position is filled."""
    got = [None] * len(batch)
    for _ in range(25):
        arr = as_list(R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief.replace("{N}", str(len(batch))) + "\n" + "\n".join(batch) + "\n",
                             max_tokens=12000, temperature=0.7))
        if not (isinstance(arr, list) and len(arr) == len(batch) and all(isinstance(x, dict) and isinstance(x.get("prompt"), str) for x in arr)):
            print("unusable writer output", flush=True)
            continue
        for i, x in enumerate(arr):
            if got[i] is None and 70 <= len(x["prompt"].split()) <= 260 and overlap(x["prompt"], sh) <= MAX_OVERLAP:
                got[i] = x["prompt"]
        if None not in got:
            return got
    raise SystemExit(f"batch starting {batch[0][:2]} failed after 25 tries")


def scenarios():
    sh = corpus()
    brief = (P / "writer_brief.txt").read_text()
    lines = (HERE / "seeds.txt").read_text().splitlines()
    with cf.ThreadPoolExecutor(3) as ex:
        prompts = [p for b in ex.map(lambda i: write_batch(brief, lines[i:i + BATCH], sh), range(0, 80, BATCH)) for p in b]
    assert len(prompts) == 80 and len({R.norm(p) for p in prompts}) == 80
    seen = set()
    for i, p in enumerate(prompts):  # a scenario may not echo an earlier new one: rewrite the offender alone
        if overlap(p, seen) > MAX_OVERLAP:
            prompts[i] = write_batch(brief, lines[i:i + 1], sh | seen)[0]
        seen |= R.shingles(prompts[i])
    for name, (pfx, n), chunk in (("tune", SPLITS["tune"], prompts[:20]), ("heldout", SPLITS["held"], prompts[20:])):
        (HERE / f"scenarios-{name}.json").write_text(json.dumps([{"id": f"sr1{pfx}{i:02d}", "prompt": q} for i, q in enumerate(chunk, 1)], indent=1) + "\n")
        assert len(chunk) == n


def sha_file(name):
    lines = [f"{R.sha((HERE / f).read_bytes())}  docs/bench/safety-r1-1018/{f}" for f in FREEZE if (HERE / f).is_file()]
    lines.append(f"{R.sha((ROOT / 'scripts/rival_eval.py').read_bytes())}  scripts/rival_eval.py")
    (HERE / f"SHA256-{name}.txt").write_text("\n".join(lines) + "\n")


def event(ledger, **kw):
    t = time.time()
    with (HERE / ledger).open("a") as f:
        f.write(json.dumps({"ts": int(t), "iso": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **kw}) + "\n")


def prereg():
    if (HERE / "ledger.jsonl").exists() or (HERE / "held").exists():
        raise SystemExit("ledger.jsonl or a held run exists; the preregistered event is the first line, once")
    event("ledger.jsonl", event="preregistered", sha256_of="SHA256-frozen.txt", sha256=R.sha((HERE / "SHA256-frozen.txt").read_bytes()))


def run(split, jobs):
    assert (ARMS["EDIT"]).read_bytes() == (ROOT / ".claude/skills/product-output-safety/SKILL.md").read_bytes(), "prompts/edit.md != SKILL.md"
    ledger = "ledger.jsonl" if split == "held" else "ledger-tune.jsonl"
    d = HERE / split
    if (d / "results.json").exists():
        raise SystemExit("results.json exists; never overwrite")
    event(ledger, event="run_start", split=split, arms={a: R.sha(p.read_bytes())[:16] for a, p in ARMS.items()})
    scs = json.loads((HERE / ("scenarios-heldout.json" if split == "held" else "scenarios-tune.json")).read_text())
    sysm = {a: p.read_text() for a, p in ARMS.items()}
    outs, errs = {a: {} for a in ARMS}, []

    def gen(a, sc):
        p = d / "outputs" / a / f"{sc['id']}.txt"
        if not p.exists():
            try:
                R.save(p, R.chat(R.GEN_MODEL, sysm[a], R.GEN_TASK + sc["prompt"], temperature=0.3))
            except RuntimeError as e:
                return errs.append(f"gen {a}/{sc['id']}: {e}")
        outs[a][sc["id"]] = p.read_text()

    with cf.ThreadPoolExecutor(jobs) as ex:
        list(ex.map(lambda t: gen(*t), [(a, s) for a in ARMS for s in scs]))
    ok = [s for s in scs if all(s["id"] in outs[a] for a in ARMS)]
    res, health, used = {}, {}, None
    for model in R.JUDGES:
        vs = {}
        for x in ("V0", "EDIT"):
            o = {"PERUN": outs[x], "RIVAL": outs["RIVAL"]}  # reuse rival_eval's judge with the arm under test as "PERUN"
            for sc, pair in zip(ok, cf.ThreadPoolExecutor(jobs).map(lambda sc: [R.judge_one(model, sc, a, b, d / x, o) for a, b in (("PERUN", "RIVAL"), ("RIVAL", "PERUN"))], ok)):
                vs[x, sc["id"]] = pair
        rate = R.slot1_rate([v for p in vs.values() for v in p])
        health[model] = None if rate is None else round(rate, 3)
        if rate is not None and R.SLOT1_OK[0] <= rate <= R.SLOT1_OK[1]:
            used = model
            for k, pair in vs.items():
                if None in pair:
                    errs.append(f"judge {k}: no verdict")
                else:
                    res[k] = R.scenario_score([R.order_score(v, f) for v, f in zip(pair, ("PERUN", "RIVAL"))])
            break
    out = dict(split=split, judge=used, slot1_rate=health, n_scenarios=len(scs), errors=errs, boot="10000 resamples, seed 1, percentile, over scenarios",
               arm_sha256={a: R.sha(t.encode())[:16] for a, t in sysm.items()})
    ids = [s["id"] for s in ok if ("V0", s["id"]) in res and ("EDIT", s["id"]) in res]
    if ids:
        v0, ed = [res["V0", i] for i in ids], [res["EDIT", i] for i in ids]
        dif = [b - a for a, b in zip(v0, ed)]
        for name, v in (("v0", v0), ("edit", ed), ("paired_edit_minus_v0", dif)):
            lo, hi = R.boot(v)
            out[name] = dict(mean=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)])
        out["n"] = len(ids)
        out["edit_vs_v0_up_down"] = [sum(x > 0 for x in dif), sum(x < 0 for x in dif)]
        out["edit_wld"] = [sum(x == 1 for x in ed), sum(x == .5 for x in ed), sum(x == 0 for x in ed)]
        out["v0_wld"] = [sum(x == 1 for x in v0), sum(x == .5 for x in v0), sum(x == 0 for x in v0)]
        out["per_scenario"] = {i: [res["V0", i], res["EDIT", i]] for i in ids}
        if split == "held":
            out["keep_rule_paired_lo_gt_0"] = out["paired_edit_minus_v0"]["ci95"][0] > 0
            out["superiority_lo_gt_0.5"] = out["edit"]["ci95"][0] > 0.5
    (d / "results.json").write_text(json.dumps(out, indent=1) + "\n")
    event(ledger, event="run_done", split=split, results_sha256=R.sha((d / "results.json").read_bytes()))
    print(json.dumps({k: v for k, v in out.items() if k != "per_scenario"}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("seeds", "scenarios", "sha", "prereg", "run"))
    ap.add_argument("name", nargs="?")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    {"seeds": seeds, "scenarios": scenarios, "sha": lambda: sha_file(a.name), "prereg": prereg, "run": lambda: run(a.name, a.jobs)}[a.cmd]()
