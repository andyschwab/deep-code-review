#!/usr/bin/env python3
"""Round 4: paired test of one edit to the contribution skill against its rival (PCSS only, $0; no claude -p).

  bench.py seeds SPLIT N    the blind writer drafts N new one-line seeds into prompts/seeds-SPLIT.txt (SPLIT = tune | held)
  bench.py write SPLIT      draw scenarios-SPLIT.json from those seeds (the writer never sees skill text) and report the
                            maximum 6-word-shingle overlap with every earlier contribution scenario set
  bench.py run SPLIT OUT    v0, v1 (frozen/) and the rival (frozen/rival.md) on the scenarios; raw files go under OUT
  bench.py fold SPLIT OUT   copy OUT outputs into results-SPLIT/ and fold the judge caches into one json
Reuses scripts/rival_eval.py (generator, rubric-free judge v2 in both orders, slot-1 gate, bootstrap seed 1). The rival's
answers are generated once per scenario and shared by both arms, so (v1 - v0) is a paired difference.
The tune split uses the first judge only and never produces a verdict. The decision rule is in PREREGISTERED.md.
"""
import concurrent.futures as cf, json, os, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "scripts"))
import rival_eval as R

PREFIX = {"tune": "r4t", "held": "r4h"}
BENCH = HERE.parent  # docs/bench


def overlap(scs):
    """Max 6-word-shingle overlap of each scenario with ANY text file under docs/bench (this round's own dir excluded), streamed;
    plus any scenario id that already appears anywhere there. Returns (overlap per scenario, id collisions)."""
    mine = [R.shingles(s["prompt"]) for s in scs]
    want, hit = set().union(*mine), set()
    ids = {s["id"] for s in scs}
    clash = set()
    for p in BENCH.rglob("*"):
        if (HERE in p.parents and p.name != "scenarios-tune.json") or not p.is_file() or p.suffix not in (".md", ".json", ".jsonl", ".txt"):
            continue
        t = p.read_text(errors="ignore")
        clash |= {i for i in ids if f'"{i}' in t or f"{i}-" in p.name}
        w = R.norm(t).split()
        hit |= {g for g in (" ".join(w[i:i + 6]) for i in range(len(w) - 5)) if g in want}
    return [len(m & hit) / len(m) for m in mine], clash


def seeds(split, n):
    prior = [l.split(" ", 1)[1] for p in sorted(BENCH.glob("contrib*/prompts/seeds*.txt")) for l in p.read_text().splitlines()]
    old = "\n".join("- " + t for t in prior)
    ask = (f"Write {n} new one-line scenario seeds, each 1 to 2 sentences, for tests of an AI assistant that helps a developer contribute a fix "
           "or improvement to someone else's open-source project without leaking anything private. Each seed names a different situation: vary the "
           "language, project type and size, what the contributor wants back (a message, a snippet, a document, a decision), and the one uncertainty "
           "(company code in a repro, an employer rule, a maintainer rule or silence, a leaked secret, a large diff, a licence or sign-off line, a security bug, an AI-use rule, a "
           "stale PR, a rejected PR). Fictional names only. Do not repeat or paraphrase any seed below. Output exactly {n} lines, each 'NN text' with NN = 01.."
           f"{n:02d}, nothing else.\n\nSeeds to avoid:\n").format(n=n) + old
    for _ in range(6):
        lines = [l.strip() for l in R.chat(R.GEN_MODEL, "You write evaluation seeds.", ask, max_tokens=12000, temperature=0.9).splitlines() if re.match(r"\d{2,3} ", l.strip())]
        if len(lines) == n and not {l.split(" ", 1)[1] for l in lines} & set(prior):  # the writer must not echo the avoid list
            p = HERE / f"prompts/seeds-{split}.txt"
            assert not p.exists(), "never overwrite a record"
            p.write_text("\n".join(lines) + "\n")
            return print(len(lines), R.sha(p.read_bytes()))
    raise SystemExit("seed writer failed")


def write(split):
    seeds_ = (HERE / f"prompts/seeds-{split}.txt").read_text().splitlines()
    brief, out, SCEN = (HERE / "prompts/brief.txt").read_text(), [], HERE / f"scenarios-{split}.json"
    def batch(i):
        use = seeds_[i:i + 10]
        for _ in range(6):
            txt = R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief.replace("{N}", str(len(use))) + "\n" + "\n".join(use) + "\n", max_tokens=12000, temperature=0.7)
            arr = R.jparse(txt)
            if not isinstance(arr, list):  # writer ignored JSON: "NN text" paragraphs
                bits = re.split(r"(?m)^(\d{2,3})[ \t]*\n?", txt)
                arr = [{"id": a, "prompt": " ".join(b.split())} for a, b in zip(bits[1::2], bits[2::2]) if b.strip()]
            if isinstance(arr, list) and len(arr) == len(use) and all(isinstance(x, dict) and "prompt" in x for x in arr):
                return [{"id": PREFIX[split] + u.split()[0], "prompt": x["prompt"]} for u, x in zip(use, arr)]
        raise SystemExit(f"writer failed for seeds {i}")

    def redraw(i):
        for _ in range(6):
            arr = R.jparse(R.chat(R.GEN_MODEL, "You write evaluation scenarios.", brief.replace("{N}", "1") + "\n" + seeds_[i] + "\n", max_tokens=6000, temperature=0.9))
            arr = [arr] if isinstance(arr, dict) else arr  # a single scenario often comes back as a bare object
            if isinstance(arr, list) and len(arr) == 1 and isinstance(arr[0], dict) and "prompt" in arr[0]:
                out[i] = {"id": out[i]["id"], "prompt": arr[0]["prompt"]}
                return

    with cf.ThreadPoolExecutor(5) as ex:
        out = [x for part in ex.map(batch, range(0, len(seeds_), 10)) for x in part]
    for rnd in range(8):  # redraw any scenario above the overlap bar, one seed at a time
        ov, clash = overlap(out)
        bad = [i for i, o in enumerate(ov) if o > 0.10]
        print("round", rnd, "bad", len(bad), "worst", round(max(ov), 3), file=sys.stderr, flush=True)
        if not bad or rnd == 7:
            break
        with cf.ThreadPoolExecutor(6) as ex:
            list(ex.map(redraw, bad))
    if os.environ.get("DRAFT_OUT"):  # scratch copy of the draft for diagnosis; the record is only written below, once it passes
        Path(os.environ["DRAFT_OUT"]).write_text(json.dumps(out, indent=1) + "\n")
    worst = max(ov)
    assert worst <= 0.10 and not clash, f"overlap {worst:.3f} clash {sorted(clash)}"
    assert not SCEN.exists(), "never overwrite a record: " + str(SCEN)
    SCEN.write_text(json.dumps(out, indent=1) + "\n")
    print(len(out), R.sha(SCEN.read_bytes()), "max_6word_overlap_vs_all_docs_bench", round(worst, 3))


def paired_boot(d, n=10000, seed=1):
    rng, m = random.Random(seed), len(d)
    bs = sorted(sum(d[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def run(split, out):
    scs, out = json.loads((HERE / f"scenarios-{split}.json").read_text()), Path(out)
    texts = {"v0": (HERE / "frozen/contribution.v0.md").read_text(), "v1": (HERE / "frozen/contribution.v1.md").read_text(), "rival": (HERE / "frozen/rival.md").read_text()}
    outs, errs = {k: {} for k in texts}, []

    def gen(k, sc):
        p = out / "outputs" / k / f"{sc['id']}-{R.sha(sc['prompt'])[:8]}-{R.sha(texts[k])[:8]}.txt"
        if not p.exists():
            try:
                R.save(p, R.chat(R.GEN_MODEL, texts[k], R.GEN_TASK + sc["prompt"], temperature=0.3))
            except RuntimeError as e:
                return errs.append(f"gen {k}/{sc['id']}: {e}")
        outs[k][sc["id"]] = p.read_text()

    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda t: gen(*t), [(k, s) for k in texts for s in scs]))
    ok = [s for s in scs if all(s["id"] in outs[k] for k in texts)]
    res = dict(split=split, n_scenarios=len(scs), n_generated=len(ok), errors=errs, sha256={k: R.sha(v) for k, v in texts.items()}, judges={})
    for model in (R.JUDGES[:1] if split == "tune" else R.JUDGES):
        sc_scores, raw = {}, {}
        for arm in ("v0", "v1"):
            o = {"PERUN": outs[arm], "RIVAL": outs["rival"]}
            d = out / "judge" / arm
            def both(sc):
                return sc["id"], [R.judge_one(model, sc, a, b, d, o) for a, b in (R.ARMS, R.ARMS[::-1])]
            with cf.ThreadPoolExecutor(6) as ex:
                vs = dict(ex.map(both, ok))
            raw[arm] = vs
            sc_scores[arm] = {i: R.scenario_score([R.order_score(x, a) for x, a in zip(p, R.ARMS)]) for i, p in vs.items() if None not in p}
        rate = R.slot1_rate([x for arm in raw.values() for p in arm.values() for x in p])
        ids = sorted(set(sc_scores["v0"]) & set(sc_scores["v1"]))
        v0, v1 = [sc_scores["v0"][i] for i in ids], [sc_scores["v1"][i] for i in ids]
        diff = [b - a for a, b in zip(v0, v1)]
        r = dict(slot1=None if rate is None else round(rate, 3), healthy=rate is not None and R.SLOT1_OK[0] <= rate <= R.SLOT1_OK[1], n_scored=len(ids))
        if ids:
            r.update(win_v0=round(sum(v0) / len(v0), 3), ci_v0=[round(x, 3) for x in R.boot(v0)], win_v1=round(sum(v1) / len(v1), 3), ci_v1=[round(x, 3) for x in R.boot(v1)],
                     paired_diff=round(sum(diff) / len(diff), 3), ci_diff=[round(x, 3) for x in paired_boot(diff)],
                     strict_v1={"win": v1.count(1.0), "tie_or_split": v1.count(0.5), "loss": v1.count(0.0)})
        res["judges"][model] = r
        if split == "held" and r["healthy"] and "used" not in res:
            res["used"] = model
            res["keep"] = bool(r["n_scored"] >= 135 and r["ci_diff"][0] > 0)
            res["superior"] = bool(r["n_scored"] >= 135 and r["ci_v1"][0] > 0.5)
    (out / "verdict.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "sha256"}, indent=1))


def fold(split, out):
    """Keep every output file; fold the one-file-per-verdict judge caches into one json (file-count limit of the privacy gate)."""
    import shutil
    out, dest = Path(out), HERE / f"results-{split}"
    shutil.copytree(out / "outputs", dest / "outputs")
    shutil.copy(out / "verdict.json", dest / "verdict.json")
    (dest / "judge-verdicts.json").write_text(json.dumps({str(p.relative_to(out / "judge")): json.loads(p.read_text())["verdict"]
                                                         for p in sorted((out / "judge").rglob("*.json"))}, indent=1) + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"seeds": lambda: seeds(a[1], int(a[2])), "write": lambda: write(a[1]), "run": lambda: run(a[1], a[2]), "fold": lambda: fold(a[1], a[2])}[a[0]]()
