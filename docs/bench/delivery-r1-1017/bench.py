#!/usr/bin/env python3
"""Delivery-plan bench round 1 on PCSS models ($0). Preregistration: PREREGISTERED.md.

  bench.py tickets              write 40 fresh held-out tickets (never edited, never dropped)
  bench.py gen ARM SPLIT        generate one plan per ticket (existing files are never regenerated)
  bench.py judge A B SPLIT      3 judges x 2 orders; an existing record is never overwritten, a failed call writes nothing
  bench.py score A B SPLIT      strict per-judge, majority over judges, bootstrap CI -> results/A__B__SPLIT.json

Arms: v0 = origin/main SKILL.md; e1/e2/e3 = v0 plus one edit; all = v0 plus all three; ship = the SKILL.md as shipped; sp = Superpowers (rival, once per ticket).
The key comes from PCSS_KEY (never printed).
"""
import json, os, random, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = os.path.dirname(os.path.abspath(__file__))
OLD = D + "/../delivery-1017"
URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
GEN = "Qwen3.5-397B-A17B"  # generator and ticket writer; never a judge
JUDGES = {"ds": ("DeepSeek-V4-Flash", True), "glm": ("GLM-5.2", False), "j3": (os.environ.get("J3", "gpt-oss_120b"), False)}
LOCK = threading.Lock()
ANCHOR = "**No files/tools (plain chat)?**"
TUNE_IDS = ["01b", "02a", "03b", "05b", "06b", "09b", "11a", "11b", "12a", "12b"]  # first 10 sorted ids of the old tune split


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


def tickets(split):
    if split == "tune":
        T = {t["id"]: t for t in json.load(open(OLD + "/tickets.json"))}
        return [T[i] for i in TUNE_IDS]
    return json.load(open(D + "/tickets.json"))


def make_tickets():
    brief = open(OLD + "/prompts/writer_brief.txt").read()
    seeds = [l.rstrip("\n").split("|", 1) for l in open(D + "/prompts/seeds_held.txt") if l.strip()]
    jobs = [(f"{int(n):02d}{v}", a, v) for n, a in seeds for v in "ab"]

    def one(j):
        i, a, v = j
        for _ in range(3):
            t = call(GEN, brief, f"Archetype: {a}\nVariant {v.upper()}: choose a different industry and different details from variant {'B' if v == 'a' else 'A'}.", 900, 0.9, False)
            try:
                o = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
                return {"id": i, "archetype": a, **{k: o[k] for k in ("title", "ticket", "repo_context")}}
            except Exception:
                pass
        raise RuntimeError("ticket " + i)

    with ThreadPoolExecutor(6) as ex:
        out = sorted(ex.map(one, jobs), key=lambda t: t["id"])
    json.dump(out, open(D + "/tickets.json", "w"), indent=1)


def arm_text(arm):
    if arm == "sp":
        return open(OLD + "/prompts/sp.txt").read()
    if arm == "ship":  # the exact SKILL.md that ships (e1 plus a small compression to fit the 24000-byte routing cap)
        return open(D + "/prompts/ship.txt").read()
    v0 = open(D + "/prompts/v0.txt").read()
    es = {"v0": [], "e1": ["e1"], "e2": ["e2"], "e3": ["e3"], "all": ["e1", "e2", "e3"]}[arm]
    snip = "".join(open(f"{D}/edits/{e}.txt").read().rstrip("\n") + "\n\n" for e in es)
    assert v0.count(ANCHOR) == 1
    return v0.replace(ANCHOR, snip + ANCHOR) if snip else v0


def gen(arm, split):
    sysmsg, task = arm_text(arm), open(OLD + "/prompts/gen_task.txt").read()
    os.makedirs(f"{D}/outputs/{arm}", exist_ok=True)

    def one(t):
        p = f"{D}/outputs/{arm}/{t['id']}.txt"
        if os.path.exists(p):
            return
        if arm == "sp" and split == "tune":  # rival is generated once per scenario: reuse the round-0 plan
            open(p, "w").write(open(f"{OLD}/outputs/sp/{t['id']}.txt").read())
            return
        txt = call(GEN, sysmsg, task + f"{t['title']}\n\n{t['ticket']}\n\nREPOSITORY FACTS:\n{t['repo_context']}", 2500, 0.7, False)
        open(p, "x").write(txt)  # call first: a failed call must not leave an empty plan file behind

    with ThreadPoolExecutor(int(os.environ.get("PAR", "6"))) as ex:
        list(ex.map(one, tickets(split)))


def judge(a, b, split):
    jp = open(OLD + "/prompts/judge.txt").read()

    def one(job):
        t, tag, order = job
        model, think = JUDGES[tag]
        f = f"{D}/judge/{tag}/{a}__{b}/{order}/{t['id']}.json"
        if os.path.exists(f):  # write-once: never overwrite or re-judge a record
            return
        ra, rb = (open(f"{D}/outputs/{x}/{t['id']}.txt").read() for x in (a, b))
        r1, r2 = (ra, rb) if order == "AB" else (rb, ra)
        u = f"TICKET: {t['title']}\n{t['ticket']}\n\nREPOSITORY FACTS:\n{t['repo_context']}\n\n=== Response 1 ===\n{r1}\n\n=== Response 2 ===\n{r2}"
        try:
            x = call(model, jp, u, 12000 if think else 1500, 0.0, think)
            j = json.loads(re.search(r"\{.*\}", x, re.S).group(0))
            assert str(j["verdict"]) in ("1", "2", "tie")
        except Exception:  # failed call/parse: write nothing, the pass can be re-run
            return
        os.makedirs(os.path.dirname(f), exist_ok=True)
        try:
            with open(f, "x") as fh:
                json.dump({"verdict": str(j["verdict"]), "reason": j.get("reason", ""), "model": model}, fh)
        except FileExistsError:
            pass

    jobs = [(t, tag, o) for t in tickets(split) for tag in JUDGES for o in ("AB", "BA")]
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


def score(a, b, split):
    ids = [t["id"] for t in tickets(split)]
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
    json.dump(res, open(f"{D}/results/{a}__{b}__{split}.json", "w"), indent=1)
    m = res["majority"]
    print(a, "vs", b, split, f"n={res['n']} win={m['win_rate']:.3f} CI=[{m['ci95'][0]:.3f},{m['ci95'][1]:.3f}] W/L/mixed={m['W']}/{m['L']}/{m['mixed']}",
          {t: round(v["win_rate"], 3) for t, v in res["per_judge"].items()}, "slot1", {t: round(v, 2) for t, v in slot.items()})


if __name__ == "__main__":
    c, *a = sys.argv[1:]
    {"tickets": make_tickets, "gen": gen, "judge": judge, "score": score}[c](*a)
