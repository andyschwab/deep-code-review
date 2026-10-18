#!/usr/bin/env python3
"""First preregistered n=60 held-out bench of growth-analytics and product-output-safety against their rivals (2026-10-18), judge
protocol v2, via scripts/rival_eval.py (unchanged). Clone of docs/bench/confirm-v2-1017/confirm.py.

usage: bench.py seeds | scenarios | sha NAME | prereg | run [--jobs N]
  seeds      draw 60 fresh seeds per skill (Qwen writer), rejecting any seed close to an existing bench seed
  scenarios  write 60 scenarios per skill in batches of 6 from the skill's own writer brief; reject any scenario whose
             6-word shingles overlap the docs/bench corpus or each other; write fixtures/<skill>/{rival,heldout,tune}.json
  sha NAME   write SHA256-NAME.txt for every freeze-list file that exists (prereg: before seeds; frozen: before generation)
  prereg     append the ledger.jsonl "preregistered" event (sha256 of SHA256-frozen.txt); refuses if a ledger or a run record exists
  run        generate both arms once per scenario, judge with the v2 chain, write results; refuses to overwrite a record
Needs PCSS_KEY in the environment; RIVAL_CACHE should point at a writable dir (rival text is fetched once, never committed).
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rival_eval as R  # noqa: E402

R.FIX = FX = HERE / "fixtures"
ORIG = ROOT / "scripts/eval-fixtures/rival"
SKILLS = ("growth-analytics", "product-output-safety")
PFX = {"growth-analytics": "ga", "product-output-safety": "po"}  # ids differ from every earlier h01 / 01 / n01 id
N, BATCH, MAX_OVERLAP = 60, 10, 0.10  # batch of 10 = the skill writer briefs verbatim ("exactly 10 scenarios")
TOPIC = {  # one line per skill: what the seed list is about (taken from each skill's own writer brief)
    "growth-analytics": "a product manager, growth lead or analyst deciding what to measure (North Star metric, funnel, event list) or how to read an experiment for a product",
    "product-output-safety": "a product team making a feature safe before launch, where the feature's own AI outputs or automated decisions reach end users and could harm them",
}


def cfg(skill):
    return json.loads((ORIG / skill / "rival.json").read_text())


def words(t):
    return set(re.findall(r"[a-z]{3,}", t.lower()))


def corpus_text():
    """Every text/json file under docs/bench except raw model outputs, judge records and this run's own dir, plus the rival fixtures."""
    paths = [p for p in (ROOT / "docs/bench").rglob("*") if p.is_file() and p.suffix in (".json", ".txt", ".md", ".py", ".jsonl")
             and not {"outputs", "judge", "run"} & set(p.parts) and HERE not in p.parents and p.stat().st_size < 4_000_000]
    paths += list(ORIG.rglob("*.json")) + list(ORIG.rglob("*.txt"))
    return [p.read_text(errors="ignore").replace("\\n", " ") for p in paths]


def corpus_shingles(texts=None):
    out = set()
    for t in texts or corpus_text():
        out |= R.shingles(t)
    return out


def overlap(prompt, shingles):
    """Share of the prompt's 6-word shingles already present in `shingles`."""
    s = R.shingles(prompt)
    return len(s & shingles) / max(1, len(s))


def old_seeds():
    out = []
    for p in list((ROOT / "docs/bench").rglob("seeds*.txt")) + list(ORIG.rglob("seeds.txt")):
        out += [re.sub(r"^\d+\s+", "", l) for l in p.read_text().splitlines() if re.match(r"\d\d ", l)]
    return out


def near(seed, others, thr=0.5):
    a = words(seed)
    return any(len(a & words(o)) / max(1, min(len(a), len(words(o)))) > thr for o in others)


def seeds():
    old = old_seeds()
    FX.mkdir(exist_ok=True)
    for s in SKILLS:
        keep, mine = [], [re.sub(r"^\d+\s+", "", l) for l in (ROOT / cfg(s)["writer"]["seeds"]).read_text().splitlines() if re.match(r"\d\d ", l)]
        for _ in range(6):
            txt = R.chat(R.GEN_MODEL, "You write evaluation scenario seeds.", (
                f"Write 80 one-line seeds, one per line, no numbering, no commentary. Each seed is a distinct work situation about {TOPIC[s]}. "
                "Vary industry, company size, stage, team size, constraint and country; fictional only. Each is 8 to 20 words, plain text. "
                "Do not repeat any of these:\n" + "\n".join(mine[:30])), max_tokens=6000, temperature=0.9)
            for l in txt.splitlines():
                l = re.sub(r"^[\s\-*\d.)]+", "", l).strip()
                if 5 <= len(l.split()) <= 30 and not near(l, old + keep):
                    keep.append(l)
            if len(keep) >= N:
                break
        assert len(keep) >= N, f"{s}: only {len(keep)} seeds"
        (FX / s).mkdir(exist_ok=True)
        (FX / s / "seeds.txt").write_text("\n".join(f"{i:02d} {l}" for i, l in enumerate(keep[:N], 1)) + "\n")
        print(s, "seeds", N)


def as_list(txt):
    """Writer output -> list of {"id","prompt"}: a JSON array, an {"array": [...]} wrapper, back-to-back objects, or "NN" header lines plus prose."""
    arr = R.jparse(txt)
    if isinstance(arr, dict):
        arr = next(iter(arr.values())) if len(arr) == 1 and isinstance(next(iter(arr.values())), list) else [arr]
    if not isinstance(arr, list):
        bits = re.split(r"(?m)^(\d\d)[ \t]*$", txt)
        arr = [{"id": i, "prompt": b.strip()} for i, b in zip(bits[1::2], bits[2::2]) if b.strip()]
    return arr


def write_batch(skill, brief, batch, shingles):
    for _ in range(8):
        txt = R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief.replace("{N}", str(len(batch))) + "\n" + "\n".join(batch) + "\n",
                     max_tokens=12000, temperature=0.7)
        arr = as_list(txt)
        if not (isinstance(arr, list) and len(arr) == len(batch) and all(isinstance(x, dict) and isinstance(x.get("prompt"), str) for x in arr)):
            print(f"{skill} {batch[0][:2]}: unusable writer output ({type(arr).__name__}, {len(arr) if isinstance(arr, list) else 0} items)", flush=True)
            continue
        bad = [(len(x["prompt"].split()), round(overlap(x["prompt"], shingles), 2)) for x in arr if not (70 <= len(x["prompt"].split()) <= 260 and overlap(x["prompt"], shingles) <= MAX_OVERLAP)]
        if bad:
            print(f"{skill} {batch[0][:2]}: rejected (words, overlap) {bad}", flush=True)
            continue
        return [{"id": PFX[skill] + b[:2], "prompt": x["prompt"]} for b, x in zip(batch, arr)]
    raise SystemExit(f"{skill}: batch starting {batch[0][:2]} failed after 8 tries")


def scenarios():
    sh = corpus_shingles()
    for s in SKILLS:
        c = cfg(s)
        brief = (ROOT / c["writer"]["brief"]).read_text()
        if "{N}" not in brief:
            brief = re.sub(r"\b10\b", "{N}", brief)
        lines = (FX / s / "seeds.txt").read_text().splitlines()
        with cf.ThreadPoolExecutor(3) as ex:
            got = [x for b in ex.map(lambda i: write_batch(s, brief, lines[i:i + BATCH], sh), range(0, len(lines), BATCH)) for x in b]
        assert len(got) == N and len({norm for norm in map(lambda x: R.norm(x["prompt"]), got)}) == N
        seen = set()
        for i, x in enumerate(got):  # no scenario may echo an earlier new one: rewrite the offender alone against corpus + earlier
            if overlap(x["prompt"], seen) > MAX_OVERLAP:
                got[i] = write_batch(s, brief, lines[i:i + 1], sh | seen)[0]
            seen |= R.shingles(got[i]["prompt"])
        (FX / s / "heldout.json").write_text(json.dumps(got, indent=1) + "\n")
        (HERE / f"scenarios-heldout-{s}.json").write_text(json.dumps(got, indent=1) + "\n")  # top-level copy for scripts/bench_check.py
        (FX / s / "tune.json").write_bytes((ORIG / s / "tune.json").read_bytes())  # only for the harness's split-hygiene check
        c["writer"]["seeds"] = str((FX / s / "seeds.txt").relative_to(ROOT))
        (FX / s / "rival.json").write_text(json.dumps(c, indent=1) + "\n")
        c["heldout_sha256"] = R.digest(s)
        (FX / s / "rival.json").write_text(json.dumps(c, indent=1) + "\n")
        print(s, "scenarios", len(got), "split problems:", R.check_split(s))


def freeze_list():
    out = [HERE / "PREREGISTERED.md", HERE / "bench.py", ROOT / "scripts/rival_eval.py"]
    for s in SKILLS:
        c = cfg(s)
        out += [ROOT / c["perun"], ROOT / c["writer"]["brief"], FX / s / "seeds.txt", FX / s / "heldout.json", FX / s / "rival.json",
                HERE / f"scenarios-heldout-{s}.json"]
        out.append(ROOT / c["rival"]["path"] if "path" in c["rival"] else None)
    return [p for p in out if p is not None and p.is_file()]


def sha_file(name):
    lines = [f"{R.sha(p.read_bytes())}  {p.relative_to(ROOT)}" for p in freeze_list()]
    for s in SKILLS:  # rival text fetched once into RIVAL_CACHE; recorded by hash, never committed (licence)
        lines.append(f"{R.sha(rival_text(s))}  rival-text:{s}")
    (HERE / f"SHA256-{name}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def rival_text(skill):
    R.FIX = FX if (FX / skill / "rival.json").is_file() else ORIG
    try:
        return R.arm_text(skill, "RIVAL")
    finally:
        R.FIX = FX


def event(**kw):
    t = time.time()
    with (HERE / "ledger.jsonl").open("a") as f:
        f.write(json.dumps({"ts": int(t), "iso": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **kw}) + "\n")


def prereg():
    if (HERE / "ledger.jsonl").exists() or (HERE / "run").exists():
        raise SystemExit("ledger or run record exists; the preregistered event comes first, once")
    event(event="preregistered", sha256_of="SHA256-frozen.txt", sha256=R.sha((HERE / "SHA256-frozen.txt").read_bytes()))


def run(jobs):
    event(event="run_start", note="no answer or judge call existed before this event")
    res = []
    for s in SKILLS:
        if list((HERE / "run" / s).glob("heldout-*/results.json")):
            raise SystemExit(f"{s}: a record exists under run/; never overwrite")
        res.append(R.run_skill(s, "heldout", "pcss", HERE / "run", jobs, 0.0))
        print(R.summary([res[-1]]).splitlines()[-1], flush=True)
    (HERE / "run").mkdir(exist_ok=True)
    (HERE / "run" / "summary.json").write_text(json.dumps({"results": res}, indent=1) + "\n")
    (HERE / "run" / "summary.md").write_text(R.summary(res))
    event(event="run_done", summary_sha256=R.sha((HERE / "run" / "summary.json").read_bytes()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("seeds", "scenarios", "sha", "prereg", "run"))
    ap.add_argument("name", nargs="?")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    {"seeds": seeds, "scenarios": scenarios, "sha": lambda: sha_file(a.name), "prereg": prereg, "run": lambda: run(a.jobs)}[a.cmd]()
