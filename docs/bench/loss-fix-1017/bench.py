#!/usr/bin/env python3
"""Loss-fix bench, free PCSS models only (see PREREGISTERED.md). Adapted from ../comms-rubricfree-1016/bench.py.
usage: bench.py ping | scen | gen | judge | report      (env SKILLS=cs,pd to limit)
Generator Qwen3.5-397B-A17B for every arm, same settings. Judges: DeepSeek-V4-Flash both orders, GLM-5.2 tiebreak. No Claude call."""
import concurrent.futures as cf, json, os, random, re, sys, threading, time, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
P = D / "prompts"
URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
ENV = Path(os.environ.get("ENVFILE", D.parents[2] / ".env"))
GEN, WRITER, J1, J2 = "Qwen3.5-397B-A17B", "GLM-5.1", "DeepSeek-V4-Flash", "GLM-5.2"
GEN_OPTS = dict(temperature=0.7, max_tokens=3000, chat_template_kwargs={"enable_thinking": False})  # identical for every arm
JOBS = int(os.environ.get("JOBS", 3))
SKILLS = os.environ.get("SKILLS", "cs,pd").split(",")
ARMS = ("PERUN", "BASE", "RIVAL")
LOCK = threading.Lock()
T0, BUDGET = time.time(), int(os.environ.get("BUDGET", 0))  # seconds after which no new call starts (run resumes from the caches)
KEY = re.search(r"^PCSS_KEY=(.*)$", ENV.read_text(), re.M).group(1).strip().strip("\"'")


def call(model, system, user, tag, **opts):
    """One PCSS chat call, 3 tries. -> (text, err). Logs tag/model/tokens/sec only, never the key."""
    body = json.dumps(dict(model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **opts)).encode()
    err, t = "", time.time()
    for n in range(3):
        if BUDGET and time.time() - T0 > BUDGET:
            return "", "budget"
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
        f.write(json.dumps(dict(tag=tag, model=model, usage=usage, cost_usd=0, sec=round(time.time() - t, 1), err=err)) + "\n")


def jparse(txt):
    s = txt.strip()
    if "{" in s and "}" in s:
        try:
            return json.loads(s[s.index("{"): s.rindex("}") + 1])
        except ValueError:
            pass
    m = re.search(r'"verdict"\s*:\s*"(1|2|tie)"', s)
    return {"verdict": m.group(1), "reason": ""} if m else None


def scen_batch(sk, i):
    out = D / f"scenarios_{sk}_{i}.json"
    if out.exists():
        return
    seeds = (P / f"{sk}_seeds.txt").read_text().splitlines()
    txt, err = call(WRITER, "You write evaluation scenarios.", (P / f"{sk}_writer_brief.txt").read_text() + "\n".join(seeds[i:i + 10]) + "\n", f"scen/{sk}/{i}", temperature=0.7, max_tokens=32000)
    m = re.search(r"\[.*\]", txt, re.S)
    arr = json.loads(m.group(0)) if m else None
    assert isinstance(arr, list) and len(arr) == 10 and all({"id", "prompt"} <= set(x) for x in arr), f"bad scenarios {sk} {i}: {err} {txt[:200]}"
    out.write_text(json.dumps(arr, indent=1) + "\n")


def scen():
    """Two batches of 10 seeds per skill, run in parallel, cached per batch; merged into scenarios_<sk>.json."""
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda t: scen_batch(*t), [(sk, i) for sk in SKILLS for i in (0, 10)]))
    for sk in SKILLS:
        (D / f"scenarios_{sk}.json").write_text(json.dumps(json.load(open(D / f"scenarios_{sk}_0.json")) + json.load(open(D / f"scenarios_{sk}_10.json")), indent=1) + "\n")


def gen(sk, arm, sc):
    p = D / "outputs" / f"{sk}_{arm}" / f"{sc['id']}.txt"
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    txt, err = call(GEN, (P / f"{sk}_{arm.lower()}.txt").read_text(), (P / f"{sk}_gen_task.txt").read_text() + sc["prompt"], f"gen/{sk}/{arm}/{sc['id']}", **GEN_OPTS)
    if txt:
        p.write_text(txt)
    else:
        print("GEN FAIL", sk, arm, sc["id"], err)


def verdict(model, sk, first, second, sc, tag):
    """Cached blind verdict with `first`/`second` shown as Response 1/2. judge/<sk>/<model>/<first>__<second>/<id>.json"""
    p = D / "judge" / sk / model / f"{first}__{second}" / f"{sc['id']}.json"
    if p.exists():
        return json.loads(p.read_text())
    a, b = (D / "outputs" / f"{sk}_{x}" / f"{sc['id']}.txt" for x in (first, second))
    if not (a.exists() and b.exists()):
        return None
    prompt = f"REQUEST:\n{sc['prompt']}\n\n=== Response 1 ===\n{a.read_text()}\n\n=== Response 2 ===\n{b.read_text()}\n"
    for n in range(3):
        txt, err = call(model, (P / f"{sk}_judge.txt").read_text(), prompt, f"judge/{sk}/{model}/{first}__{second}/{sc['id']}/{n}", temperature=0, max_tokens=12000 if model == J2 else 1500)
        j = jparse(txt) if txt else None
        if j and j.get("verdict") in ("1", "2", "tie"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(j, indent=1) + "\n")
            return j
    print("JUDGE FAIL", model, sk, first, second, sc["id"])
    return None


def score(sk, model, x, sc):
    """x vs RIVAL on one scenario with one judge, both orders (position-bias control, amendment 4): a win or loss counts only when both orders
    pick the same arm; a split or any tie scores 0.5. -> score or None."""
    ds = []
    for f, s in ((x, "RIVAL"), ("RIVAL", x)):
        j = verdict(model, sk, f, s, sc, "")
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
    """Per judge: share of all cached verdicts that picked Response 1 (0.5 = no position bias), and ties."""
    out = {}
    for m in (J1, J2):
        v = [json.load(open(p))["verdict"] for p in (D / "judge").glob(f"*/{m}/*/*.json")]
        out[m] = dict(verdicts=len(v), slot1_rate=round(v.count("1") / len(v), 3) if v else None, ties=v.count("tie"))
    return out


def report():
    for sk in SKILLS:
        scs = json.loads((D / f"scenarios_{sk}.json").read_text())
        res = {}
        for x, models in (("PERUN", (J1, J2)), ("BASE", (J1,))):
            for m in models:
                per = {sc["id"]: r for sc in scs if (r := score(sk, m, x, sc)) is not None}
                v = list(per.values())
                e = dict(arm=x, vs="RIVAL", judge=m, n=len(v), win_rate=round(sum(v) / len(v), 3) if v else None, clear_wins=v.count(1.0), clear_losses=v.count(0.0), ties_or_splits=v.count(0.5),
                         per_scenario=per, bootstrap="10000 resamples, seed 1, percentile, over scenarios")
                if v:
                    lo, hi = boot(v)
                    e.update(ci95=[round(lo, 3), round(hi, 3)], verdict="PASS" if lo > 0.5 and len(v) == 20 else "FAIL")
                res[f"{x}/{m}"] = e
                print(sk, json.dumps({k: e[k] for k in e if k != "per_scenario"}))
        (D / f"results_{sk}.json").write_text(json.dumps(res, indent=1) + "\n")
    r = slot1()
    (D / "position_bias.json").write_text(json.dumps(r, indent=1) + "\n")
    print("slot-1 rate", json.dumps(r))


def main(cmd):
    if cmd == "ping":
        for m in (GEN, WRITER, J1, J2):
            print(m, call(m, "You are terse.", 'Reply with only: {"verdict": "1"}', "ping", max_tokens=200, temperature=0))
        return
    if cmd == "scen":
        return scen()
    if cmd == "report":
        return report()
    scs = {sk: json.loads((D / f"scenarios_{sk}.json").read_text()) for sk in SKILLS}
    if cmd == "gen":
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(lambda t: gen(*t), [(sk, a, s) for sk in SKILLS for a in ARMS for s in scs[sk]]))
    elif cmd == "judge":
        def one(t):
            sk, m, x, sc = t
            score(sk, m, x, sc)
        jobs = [(sk, m, x, sc) for sk in SKILLS for x, ms in (("PERUN", (J1, J2)), ("BASE", (J1,))) for m in ms for sc in scs[sk]]
        jobs.sort(key=lambda t: t[1] != J1)  # DeepSeek first, GLM-5.2 after
        with cf.ThreadPoolExecutor(JOBS) as ex:
            list(ex.map(one, jobs))
        report()


if __name__ == "__main__":
    main(sys.argv[1])
