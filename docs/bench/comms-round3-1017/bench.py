#!/usr/bin/env python3
"""Round-3 bench for communication-structure vs humanizer, free PCSS models only (see PREREGISTERED.md).
usage: SPLIT=tune|held bench.py scen | overlap | gen ARM.. | judge ARM.. | report ARM..
Adapted from ../comms-round2-1017/bench.py. Generator Qwen3.5-397B-A17B for every arm; three judges (DeepSeek-V4-Flash,
GLM-5.2 non-thinking, gpt-oss_120b), both orders each, strict agreement per judge, majority across judges; never the generator."""
import concurrent.futures as cf, json, os, random, re, sys, threading, time, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
P = D / "prompts"
SPLIT = os.environ.get("SPLIT", "tune")
URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
KEY = re.search(r"^PCSS_KEY=(.*)$", Path(os.environ.get("ENVFILE", D.parents[2] / ".env")).read_text(), re.M).group(1).strip().strip("\"'")
GEN, WRITER = "Qwen3.5-397B-A17B", "GLM-5.1"
JUDGES = ("DeepSeek-V4-Flash", "GLM-5.2", "gpt-oss_120b")
NOTHINK = {"chat_template_kwargs": {"enable_thinking": False}}
GEN_OPTS = dict(temperature=0.7, max_tokens=3000, chat_template_kwargs={"enable_thinking": False})
JOBS = int(os.environ.get("JOBS", 4))
LOCK = threading.Lock()


def call(model, system, user, tag, **opts):
    """One PCSS chat call, 3 tries -> (text, err). Ledger holds tag/model/tokens/sec only, never the key."""
    body = json.dumps(dict(model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **opts)).encode()
    err, t = "", time.time()
    for n in range(3):
        try:
            r = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(r, timeout=600))
            txt = re.sub(r"<think>.*?</think>", "", j["choices"][0]["message"].get("content") or "", flags=re.S).strip()
            if txt:
                _log(tag, model, j.get("usage"), t, "")
                return txt, ""
            err = "empty"
        except Exception as e:  # noqa: BLE001 - network/HTTP errors all retry the same way
            err = type(e).__name__ + " " + str(e)[:80].replace(KEY, "***")
        time.sleep(5 * (n + 1))
    _log(tag, model, None, t, err)
    return "", err


def _log(tag, model, usage, t, err):
    with LOCK, open(D / "ledger.jsonl", "a") as f:
        f.write(json.dumps(dict(split=SPLIT, tag=tag, model=model, usage=usage, cost_usd=0, sec=round(time.time() - t, 1), err=err)) + "\n")


def scenarios():
    return json.loads((D / f"scenarios_{SPLIT}.json").read_text())


def scen_batch(i):
    out = D / f"scenarios_{SPLIT}_{i}.json"
    if out.exists():
        return
    seeds = (P / f"{SPLIT}_seeds.txt").read_text().splitlines()
    txt, err = call(WRITER, "You write evaluation scenarios.", (P / "writer_brief.txt").read_text() + "\n".join(seeds[i:i + 10]) + "\n", f"scen/{SPLIT}/{i}", temperature=0.7, max_tokens=32000)
    m = re.search(r"\[.*\]", txt, re.S)
    arr = json.loads(m.group(0)) if m else None
    assert isinstance(arr, list) and len(arr) == 10 and all({"id", "prompt"} <= set(x) for x in arr), f"bad scenarios {i}: {err} {txt[:200]}"
    for k, x in enumerate(arr):
        x["id"] = f"{i + k + 1:02d}"
    out.write_text(json.dumps(arr, indent=1) + "\n")


def overlap():
    """Max word-trigram Jaccard of each new scenario against every earlier scenario file under docs/bench (own dir excluded)."""
    def grams(t):
        w = re.findall(r"[a-z0-9']+", t.lower())
        return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}
    old = []
    for f in D.parent.glob("*/scenarios*.json"):
        if f.parent != D:
            old += [(f.parent.name + "/" + f.name, grams(x["prompt"])) for x in json.loads(f.read_text()) if isinstance(x, dict) and "prompt" in x]
    for sp in ("tune", "held"):
        for sc in json.loads((D / f"scenarios_{sp}.json").read_text()):
            g = grams(sc["prompt"])
            best = max(((len(g & o) / len(g | o), n) for n, o in old), default=(0, ""))
            print(sp, sc["id"], round(best[0], 3), best[1])
    print("compared against", len(old), "earlier scenarios")


def gen(arm, sc):
    p = D / "outputs" / SPLIT / arm / f"{sc['id']}.txt"
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    txt, err = call(GEN, (P / f"{arm}.txt").read_text(), (P / "gen_task.txt").read_text() + sc["prompt"], f"gen/{SPLIT}/{arm}/{sc['id']}", **GEN_OPTS)
    if txt:
        p.write_text(txt)
    else:
        print("GEN FAIL", arm, sc["id"], err)


def jparse(txt):
    s = txt.strip()
    if "{" in s and "}" in s:
        try:
            return json.loads(s[s.index("{"): s.rindex("}") + 1])
        except ValueError:
            pass
    m = re.search(r'"verdict"\s*:\s*"(1|2|tie)"', s)
    return {"verdict": m.group(1), "reason": ""} if m else None


def verdict(model, first, second, sc):
    """Cached blind verdict, `first`/`second` shown as Response 1/2. judge/<split>/<model>/<first>__<second>/<id>.json"""
    p = D / "judge" / SPLIT / model / f"{first}__{second}" / f"{sc['id']}.json"
    if p.exists():
        return json.loads(p.read_text())
    a, b = (D / "outputs" / SPLIT / x / f"{sc['id']}.txt" for x in (first, second))
    if not (a.exists() and b.exists()):
        return None
    prompt = f"REQUEST:\n{sc['prompt']}\n\n=== Response 1 ===\n{a.read_text()}\n\n=== Response 2 ===\n{b.read_text()}\n"
    for n in range(3):
        txt, err = call(model, (P / "judge.txt").read_text(), prompt, f"judge/{SPLIT}/{model}/{first}__{second}/{sc['id']}/{n}", temperature=0, max_tokens=4000 if model == "gpt-oss_120b" else 1500, **(NOTHINK if model == "GLM-5.2" else {}))
        j = jparse(txt) if txt else None
        if j and j.get("verdict") in ("1", "2", "tie"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(j, indent=1) + "\n")
            return j
    print("JUDGE FAIL", model, first, second, sc["id"])
    return None


def score(model, x, sc):
    """x vs RIVAL, both orders: win or loss counts only when both orders pick the same arm; a split or any tie is 0.5. -> score or None."""
    ds = []
    for f, s in ((x, "RIVAL"), ("RIVAL", x)):
        j = verdict(model, f, s, sc)
        if j is None:
            return None
        w = {"1": f, "2": s, "tie": None}[j["verdict"]]
        ds.append(0.5 if w is None else 1.0 if w == x else 0.0)
    return ds[0] if ds[0] == ds[1] else 0.5


def boot(vals, n=10000, seed=1):
    rng, m = random.Random(seed), len(vals)
    bs = sorted(sum(vals[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def slot1():
    """Per judge: share of cached verdicts that picked Response 1 (0.5 = no position bias), with and without ties."""
    out = {}
    for p in sorted((D / "judge" / SPLIT).glob("*")):
        v = [json.load(open(q))["verdict"] for q in p.glob("*/*.json")]
        out[p.name] = dict(verdicts=len(v), ties=v.count("tie"), slot1_rate=round(v.count("1") / len(v), 3), slot1_rate_excl_ties=round(v.count("1") / max(1, len(v) - v.count("tie")), 3))
    return out


def majority(x, sc):
    """Per scenario: 1 if at least 2 of the 3 judges give x a clear win, 0 if at least 2 give a clear loss, else 0.5. None if any judge is missing."""
    r = [score(m, x, sc) for m in JUDGES]
    if None in r:
        return None
    return 1.0 if r.count(1.0) >= 2 else 0.0 if r.count(0.0) >= 2 else 0.5


def report(arms):
    for x in arms:
        for name, fn in [("majority", lambda s: majority(x, s))] + [(m, (lambda m: lambda s: score(m, x, s))(m)) for m in JUDGES]:
            per = {sc["id"]: r for sc in scenarios() if (r := fn(sc)) is not None}
            v = list(per.values())
            if not v:
                continue
            lo, hi = boot(v)
            print(json.dumps(dict(split=SPLIT, arm=x, judge=name, n=len(v), win_rate=round(sum(v) / len(v), 3), ci95=[round(lo, 3), round(hi, 3)], clear_wins=v.count(1.0), clear_losses=v.count(0.0), splits_or_ties=v.count(0.5), per_scenario=per if name == "majority" else None)))
    print("slot-1", json.dumps(slot1()))


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "scen":
        batches = (0,) if SPLIT == "tune" else (0, 10, 20, 30)
        with cf.ThreadPoolExecutor(4) as ex:
            list(ex.map(scen_batch, batches))
        (D / f"scenarios_{SPLIT}.json").write_text(json.dumps(sum((json.load(open(D / f"scenarios_{SPLIT}_{i}.json")) for i in batches), []), indent=1) + "\n")
    elif cmd == "overlap":
        overlap()
    elif cmd == "gen":
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(lambda t: gen(*t), [(a, s) for a in args for s in scenarios()]))
    elif cmd == "judge":
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(lambda t: majority(*t), [(a, s) for a in args for s in scenarios()]))
        report(args)
    elif cmd == "report":
        report(args)


if __name__ == "__main__":
    main()
