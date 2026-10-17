#!/usr/bin/env python3
"""Delivery-plan bench on PCSS models (no paid calls). See PREREGISTERED.md.

  bench.py tickets            write 40 fictional tickets, freeze the tune/held split
  bench.py gen ARM            generate a plan per ticket with prompts/<ARM>.txt as system prompt
  bench.py judge A B [SPLIT]  blind judge A vs B (both orders; tiebreak on inconsistency)
  bench.py score A B          win rate + bootstrap CI per split -> results/<A>__<B>.json

The key is read from env PCSS_KEY, else from the file named by env KEYFILE; never printed.
"""
import glob, json, os, random, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = os.path.dirname(os.path.abspath(__file__))
URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
GEN, JUDGE, TIEB = "Qwen3.5-397B-A17B", "DeepSeek-V4-Flash", "GLM-5.2"
LOCK = threading.Lock()
TH = os.environ.get("JTHINK") == "1"  # amendment A1: judges think; judge dirs and results get a -t suffix
SUF = "-t" if TH else ""


def key():
    k = os.environ.get("PCSS_KEY")
    if not k:
        for l in open(os.environ["KEYFILE"]):
            if l.startswith("PCSS_KEY="):
                k = l.split("=", 1)[1].strip().strip("\"'")
    return k


def call(model, system, user, max_tokens=2500, temp=0.7, think=False):
    body = {"model": model, "max_tokens": max_tokens, "temperature": temp,
            "chat_template_kwargs": {"enable_thinking": think},
            "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]}
    err = None
    for a in range(3):
        try:
            r = urllib.request.Request(URL, json.dumps(body).encode(), {"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(r, timeout=300))
            t = j["choices"][0]["message"].get("content") or ""
            t = re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()
            if not t:
                raise ValueError("empty")
            with LOCK, open(D + "/ledger.jsonl", "a") as f:
                f.write(json.dumps({"model": model, "usage": j.get("usage"), "ts": int(time.time())}) + "\n")
            return t
        except Exception as e:  # retry on any transport/format error
            err = type(e).__name__ + " " + str(e)[:120]
            time.sleep(5 * (a + 1))
    with LOCK, open(D + "/ledger.jsonl", "a") as f:
        f.write(json.dumps({"model": model, "error": err, "ts": int(time.time())}) + "\n")
    raise RuntimeError(err)


def tickets():
    return json.load(open(D + "/tickets.json"))


def make_tickets():
    brief = open(D + "/prompts/writer_brief.txt").read()
    seeds = [l.rstrip("\n").split("|", 1) for l in open(D + "/prompts/seeds.txt") if l.strip()]
    jobs = [(f"{int(n):02d}{v}", a, v) for n, a in seeds for v in "ab"]

    def one(j):
        i, a, v = j
        for _ in range(3):
            t = call(GEN, brief, f"Archetype: {a}\nVariant {v.upper()}: choose a different industry and different details from variant {'B' if v == 'a' else 'A'}.", 900, 0.9)
            try:
                o = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
                return i, {"id": i, "archetype": a, **{k: o[k] for k in ("title", "ticket", "repo_context")}}
            except Exception:
                pass
        raise RuntimeError("ticket " + i)

    with ThreadPoolExecutor(6) as ex:
        out = dict(ex.map(one, jobs))
    ids = sorted(out)
    random.Random(1).shuffle(ids)
    for k, i in enumerate(ids):
        out[i]["split"] = "tune" if k < 16 else "held"
    json.dump([out[i] for i in sorted(out)], open(D + "/tickets.json", "w"), indent=1)


def gen(arm, split=None):
    sysmsg = open(f"{D}/prompts/{arm}.txt").read()
    task = open(D + "/prompts/gen_task.txt").read()
    os.makedirs(f"{D}/outputs/{arm}", exist_ok=True)

    def one(t):
        p = f"{D}/outputs/{arm}/{t['id']}.txt"
        if os.path.exists(p):
            return
        txt = call(GEN, sysmsg, task + f"{t['title']}\n\n{t['ticket']}\n\nREPOSITORY FACTS:\n{t['repo_context']}", 2500, 0.7)
        open(p, "w").write(txt)

    with ThreadPoolExecutor(int(os.environ.get("PAR", "5"))) as ex:
        list(ex.map(one, [t for t in tickets() if split in (None, t["split"])]))


def verdict(model, t, r1, r2):
    u = (f"TICKET: {t['title']}\n{t['ticket']}\n\nREPOSITORY FACTS:\n{t['repo_context']}\n\n"
         f"=== Response 1 ===\n{r1}\n\n=== Response 2 ===\n{r2}")
    x = call(model, open(D + "/prompts/judge.txt").read(), u, 8000 if TH else 600, 0.0, TH)
    m = re.search(r"\{.*\}", x, re.S)
    j = json.loads(m.group(0))
    assert str(j["verdict"]) in ("1", "2", "tie")
    return {"verdict": str(j["verdict"]), "reason": j.get("reason", "")}


def judge(a, b, split=None):
    """A = the arm under test. Orders: A first, A second. Tiebreak model only when the judge's mean is not 0 or 1."""
    def one(t):
        out = {}
        for model, tag in ((JUDGE, "ds" + SUF), (TIEB, "glm" + SUF)):
            for order in ("AB", "BA"):
                if tag.startswith("glm") and os.environ.get("NOGLM"):  # secondary column only; run later
                    continue
                p = f"{D}/judge/{tag}/{a}__{b}/{order}"
                os.makedirs(p, exist_ok=True)
                f = f"{p}/{t['id']}.json"
                if tag.startswith("glm") and not os.path.exists(f):
                    s = [score_of(json.load(open(f"{D}/judge/ds{SUF}/{a}__{b}/{o}/{t['id']}.json")), o) for o in ("AB", "BA")]
                    if sum(s) / 2 in (0, 1):
                        continue
                if not os.path.exists(f):
                    ra, rb = (open(f"{D}/outputs/{x}/{t['id']}.txt").read() for x in (a, b))
                    r1, r2 = (ra, rb) if order == "AB" else (rb, ra)
                    try:
                        json.dump(verdict(model, t, r1, r2), open(f, "w"))
                    except Exception:  # tiebreak unavailable (timeout): scen() falls back to the primary judge
                        if tag.startswith("ds"):
                            raise
    ts = [t for t in tickets() if split in (None, t["split"])]
    with ThreadPoolExecutor(int(os.environ.get("PAR", "5"))) as ex:
        list(ex.map(one, ts))


def score_of(v, order):  # 1 = A (under test) preferred
    if v["verdict"] == "tie":
        return 0.5
    return 1.0 if (v["verdict"] == "1") == (order == "AB") else 0.0


def scen(a, b, i):
    """Returns (strict, tiebroken, glm_used). strict (the bar, amendment A2): DeepSeek's two orders must agree
    for a win or loss, any split or tie scores 0.5. tiebroken (secondary): GLM-5.2's two-order mean replaces a non-0/1 strict score."""
    ds = [score_of(json.load(open(f"{D}/judge/ds{SUF}/{a}__{b}/{o}/{i}.json")), o) for o in ("AB", "BA")]
    s = sum(ds) / 2
    if s in (0, 1):
        return s, s, False
    try:
        g = [score_of(json.load(open(f"{D}/judge/glm{SUF}/{a}__{b}/{o}/{i}.json")), o) for o in ("AB", "BA")]
    except FileNotFoundError:  # tiebreak never returned: keep the primary judge's mean
        return s, s, False
    return s, sum(g) / 2, True


def slot1(a, b, tag):
    """Share of verdicts naming Response 1 (position-bias check; 0.5 is unbiased)."""
    n = k = 0
    for o in ("AB", "BA"):
        for f in glob.glob(f"{D}/judge/{tag}{SUF}/{a}__{b}/{o}/*.json"):
            v = json.load(open(f))["verdict"]
            n += 1
            k += v == "1"
    return {"n": n, "slot1": k, "rate": k / n if n else None}


def summ(xs):
    lo, hi = boot(xs)
    return {"win_rate": sum(xs) / len(xs), "ci95": [lo, hi], "wins": sum(x == 1 for x in xs),
            "losses": sum(x == 0 for x in xs), "mixed": sum(x not in (0, 1) for x in xs)}


def boot(xs, n=10000):
    r = random.Random(1)
    m = sorted(sum(r.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return m[int(.025 * n)], m[int(.975 * n) - 1]


def score(a, b):
    res = {}
    for sp in ("tune", "held", "all"):
        ids = [t["id"] for t in tickets() if sp in ("all", t["split"])
               and all(os.path.exists(f"{D}/judge/ds{SUF}/{a}__{b}/{o}/{t['id']}.json") for o in ("AB", "BA"))]
        if not ids:
            continue
        rows = {i: scen(a, b, i) for i in ids}
        res[sp] = {"n": len(ids), "strict": summ([v[0] for v in rows.values()]),
                   "tiebroken": {**summ([v[1] for v in rows.values()]), "glm_used": sum(v[2] for v in rows.values())},
                   "scenarios_strict": {i: v[0] for i, v in rows.items()}, "scenarios_tiebroken": {i: v[1] for i, v in rows.items()}}
    res["slot1"] = {t: slot1(a, b, t) for t in ("ds", "glm")}
    os.makedirs(D + "/results", exist_ok=True)
    json.dump(res, open(f"{D}/results/{a}__{b}{SUF}.json", "w"), indent=1)
    for sp in [s for s in ("tune", "held", "all") if s in res]:
        for k in ("strict", "tiebroken"):
            r = res[sp][k]
            print(a, "vs", b, sp, k, f"n={res[sp]['n']} win={r['win_rate']:.3f} CI=[{r['ci95'][0]:.3f},{r['ci95'][1]:.3f}] W/L/mixed={r['wins']}/{r['losses']}/{r['mixed']}")
    print("slot-1 rate", {t: v["rate"] for t, v in res["slot1"].items()})


if __name__ == "__main__":
    c, *a = sys.argv[1:]
    {"tickets": make_tickets, "gen": gen, "judge": judge, "score": score}[c](*a)
