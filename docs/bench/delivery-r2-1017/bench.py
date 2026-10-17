#!/usr/bin/env python3
"""Delivery-plan bench round 2 on PCSS models ($0). Preregistration: PREREGISTERED.md.

  bench.py tickets              write 40 fresh held-out tickets h2-01..h2-40 (never edited, never dropped)
  bench.py gen ARM              one plan per ticket (existing files are never regenerated)
  bench.py judge A B            3 judges x 2 orders, judge prompt v2 from scripts/rival_eval.py; write-once records
  bench.py score A B            strict per-judge, majority over judges, bootstrap CI -> results/A__B.json
  bench.py paired A0 A1         paired A1 minus A0 on per-ticket majority scores (win vs sp), bootstrap CI

Arms: sp = Superpowers (rival, generated once per ticket), v0 = origin/main SKILL.md, ship = the branch SKILL.md.
The key comes from PCSS_KEY (never printed). Unlike round 1 there is no tune split: ids and output dirs are all new.
"""
import json, os, random, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = os.path.dirname(os.path.abspath(__file__))
OLD = D + "/../delivery-1017"  # reused verbatim: writer brief, generation task, Superpowers text
sys.path.insert(0, D + "/../../../scripts")
import rival_eval as R  # judge v2: JUDGE_SYSTEM, neutral labels, verdict parser

URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
GEN = "Qwen3.5-397B-A17B"  # generator and ticket writer; never a judge
JUDGES = {"ds": ("DeepSeek-V4-Flash", True), "glm": ("GLM-5.2", False), "j3": (os.environ.get("J3", "gpt-oss_120b"), False)}
LOCK = threading.Lock()


def call(model, system, user, max_tokens, temp, think):
    body = {"model": model, "max_tokens": max_tokens, "temperature": temp, "chat_template_kwargs": {"enable_thinking": think},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    err = None
    for a in range(3):
        try:
            r = urllib.request.Request(URL, json.dumps(body).encode(), {"Authorization": "Bearer " + os.environ["PCSS_KEY"], "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(r, timeout=300))
            t = re.sub(r"<think>.*?</think>", "", j["choices"][0]["message"].get("content") or "", flags=re.S).strip()
            if not t:
                raise ValueError("empty")
            with LOCK, open(D + "/ledger.jsonl", "a") as f:
                f.write(json.dumps({"model": model, "usage": j.get("usage"), "ts": int(time.time())}) + "\n")
            return t
        except Exception as e:
            err = type(e).__name__ + " " + str(e)[:100]
            time.sleep(5 * (a + 1))
    with LOCK, open(D + "/ledger.jsonl", "a") as f:
        f.write(json.dumps({"model": model, "error": err, "ts": int(time.time())}) + "\n")
    raise RuntimeError(err)


def tickets():
    return json.load(open(D + "/tickets.json"))


def make_tickets():
    brief = open(OLD + "/prompts/writer_brief.txt").read()
    seeds = [l.rstrip("\n").split("|", 1) for l in open(D + "/prompts/seeds.txt") if l.strip()]

    def one(s):
        n, a = s
        for _ in range(3):
            t = call(GEN, brief, f"Archetype: {a}", 900, 0.9, False)
            try:
                o = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
                return {"id": f"h2-{int(n):02d}", "archetype": a, **{k: o[k] for k in ("title", "ticket", "repo_context")}}
            except Exception:
                pass
        raise RuntimeError("ticket " + n)

    with ThreadPoolExecutor(6) as ex:
        out = sorted(ex.map(one, seeds), key=lambda t: t["id"])
    json.dump(out, open(D + "/tickets.json", "w"), indent=1)


def gen(arm):
    sysmsg = open(OLD + "/prompts/sp.txt" if arm == "sp" else f"{D}/prompts/{arm}.txt").read()
    task = open(OLD + "/prompts/gen_task.txt").read()
    os.makedirs(f"{D}/outputs/{arm}", exist_ok=True)

    def one(t):
        p = f"{D}/outputs/{arm}/{t['id']}.txt"
        if os.path.exists(p):
            return
        txt = call(GEN, sysmsg, task + f"{t['title']}\n\n{t['ticket']}\n\nREPOSITORY FACTS:\n{t['repo_context']}", 2500, 0.7, False)
        open(p, "x").write(txt)  # call first: a failed call must not leave an empty plan file behind

    with ThreadPoolExecutor(int(os.environ.get("PAR", "6"))) as ex:
        list(ex.map(one, tickets()))


def judge(a, b):
    def one(job):
        t, tag, order = job
        model, think = JUDGES[tag]
        f = f"{D}/judge/{tag}/{a}__{b}/{order}/{t['id']}.json"
        if os.path.exists(f):  # write-once: never overwrite or re-judge a record
            return
        ra, rb = (open(f"{D}/outputs/{x}/{t['id']}.txt").read() for x in (a, b))
        r1, r2 = (ra, rb) if order == "AB" else (rb, ra)
        x, y = R.labels(t, r1, r2)
        u = f"REQUEST:\nTICKET: {t['title']}\n{t['ticket']}\n\nREPOSITORY FACTS:\n{t['repo_context']}\n\n=== Response {x} ===\n{r1}\n\n=== Response {y} ===\n{r2}\n"
        try:
            v = R.parse_verdict(call(model, R.JUDGE_SYSTEM.format(a=x, b=y), u, 12000 if think else 3000, 0.0, think), x, y)
            assert v
        except Exception:  # failed call/parse: write nothing, the pass can be re-run
            return
        os.makedirs(os.path.dirname(f), exist_ok=True)
        try:
            with open(f, "x") as fh:
                json.dump({"verdict": v, "model": model}, fh)
        except FileExistsError:
            pass

    jobs = [(t, tag, o) for t in tickets() for tag in JUDGES for o in ("AB", "BA")]
    with ThreadPoolExecutor(int(os.environ.get("PAR", "6"))) as ex:
        list(ex.map(one, jobs))


def pick(a, b, tag, order, i):  # 1 = A (arm under test) preferred
    v = json.load(open(f"{D}/judge/{tag}/{a}__{b}/{order}/{i}.json"))["verdict"]
    return 0.5 if v == "tie" else float((v == "1") == (order == "AB"))


def boot(xs, n=10000):
    r = random.Random(1)
    m = sorted(sum(r.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return m[int(.025 * n)], m[int(.975 * n) - 1]


def summ(xs):
    lo, hi = boot(xs)
    return {"win_rate": sum(xs) / len(xs), "ci95": [lo, hi], "W": sum(x == 1 for x in xs), "L": sum(x == 0 for x in xs), "mixed": sum(x not in (0, 1) for x in xs)}


def score(a, b):
    ids = [t["id"] for t in tickets()]
    miss = [f"{tag}/{o}/{i}" for i in ids for tag in JUDGES for o in ("AB", "BA") if not os.path.exists(f"{D}/judge/{tag}/{a}__{b}/{o}/{i}.json")]
    if miss:
        sys.exit(f"INCOMPLETE ({len(miss)} records missing, e.g. {miss[:3]}): re-run judge")
    per = {tag: {i: sum(pick(a, b, tag, o, i) for o in ("AB", "BA")) / 2 for i in ids} for tag in JUDGES}  # strict: both orders must agree, else 0.5
    maj = {}
    for i in ids:
        w = sum(per[t][i] == 1 for t in JUDGES)
        l = sum(per[t][i] == 0 for t in JUDGES)
        maj[i] = 1.0 if w >= 2 else 0.0 if l >= 2 else 0.5
    slot = {}
    for tag in JUDGES:
        v = [json.load(open(f"{D}/judge/{tag}/{a}__{b}/{o}/{i}.json"))["verdict"] for i in ids for o in ("AB", "BA")]
        slot[tag] = sum(x == "1" for x in v) / len(v)
    res = {"n": len(ids), "majority": summ(list(maj.values())), "per_judge": {t: summ(list(per[t].values())) for t in JUDGES}, "slot1": slot, "scenarios": maj}
    os.makedirs(D + "/results", exist_ok=True)
    json.dump(res, open(f"{D}/results/{a}__{b}.json", "w"), indent=1)
    m = res["majority"]
    print(a, "vs", b, f"n={res['n']} win={m['win_rate']:.3f} CI=[{m['ci95'][0]:.3f},{m['ci95'][1]:.3f}] W/L/mixed={m['W']}/{m['L']}/{m['mixed']}",
          {t: round(v["win_rate"], 3) for t, v in res["per_judge"].items()}, "slot1", {t: round(v, 2) for t, v in slot.items()})


def paired(a0, a1):
    s0, s1 = (json.load(open(f"{D}/results/{x}__sp.json"))["scenarios"] for x in (a0, a1))
    d = [s1[i] - s0[i] for i in s0]
    lo, hi = boot(d)
    print(f"paired {a1}-{a0} n={len(d)} diff={sum(d) / len(d):+.3f} CI=[{lo:+.3f},{hi:+.3f}] up/down={sum(x > 0 for x in d)}/{sum(x < 0 for x in d)}")


if __name__ == "__main__":
    c, *a = sys.argv[1:]
    {"tickets": make_tickets, "gen": gen, "judge": judge, "score": score, "paired": paired}[c](*a)
