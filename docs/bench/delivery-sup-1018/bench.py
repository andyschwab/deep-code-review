#!/usr/bin/env python3
"""Delivery-plan bench, shipped agentic-delivery SKILL.md vs Superpowers, n=150 ($0, PCSS only).

Preregistration: PREREGISTERED.md. No tune split, no edit arm: the only arm under test is the shipped SKILL.md.

  bench.py prereg               first ledger line: sha256 of SHA256-frozen.txt (run once, before seeds exist)
  bench.py seeds                150 fresh archetypes -> prompts/seeds.txt (word-Jaccard gate vs every earlier seeds file)
  bench.py freeze FILE EVENT    append FILE's hash to SHA256-frozen.txt and a ledger event carrying it
  bench.py tickets              150 tickets sup-001..sup-150 -> tickets.json (6-word-shingle disjointness gate)
  bench.py gen ARM              one plan per ticket (ARM = sp | ship; existing files are never regenerated)
  bench.py judge A B            3 judges x 2 orders, judge prompt v2 from scripts/rival_eval.py; write-once records
  bench.py score A B            strict per-judge, majority over judges, bootstrap CI (10000, seed 1) -> results/A__B.json

Judge, generator, rival text, scoring and bootstrap are those of ../delivery-r2-1017 (same code). Key from PCSS_KEY, never printed.
"""
import glob, hashlib, json, os, random, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = os.path.dirname(os.path.abspath(__file__))
OLD = D + "/../delivery-1017"  # reused verbatim: writer brief, generation task, Superpowers text
sys.path.insert(0, D + "/../../../scripts")
import rival_eval as R  # judge v2: JUDGE_SYSTEM, neutral labels, verdict parser
import bench_check as BC  # scenario loader shared with the CI gate

URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
GEN = "Qwen3.5-397B-A17B"  # generator, seed and ticket writer; never a judge
JUDGES = {"ds": ("DeepSeek-V4-Flash", True), "glm": ("GLM-5.2", False), "j3": ("gpt-oss_120b", False)}
LOCK = threading.Lock()
N, MAXSHARE = 150, 0.10  # tickets; max share of a ticket's 6-word shingles found in any earlier bench ticket or earlier new ticket
DOMAINS = ["online retail", "clinic and appointment booking", "consumer payments", "freight and fleet logistics", "online learning",
           "video and audio streaming", "B2B analytics software", "factory and device telemetry", "city and public-sector services",
           "travel and hospitality", "telecom billing", "energy and utilities", "multiplayer games", "donor and charity platforms",
           "internal developer platform"]


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
            led({"model": model, "usage": j.get("usage"), "ts": int(time.time())})
            return t
        except Exception as e:
            err = type(e).__name__ + " " + str(e)[:100]
            time.sleep(5 * (a + 1))
    led({"model": model, "error": err, "ts": int(time.time())})
    raise RuntimeError(err)


def led(o):
    with LOCK, open(D + "/ledger.jsonl", "a") as f:
        f.write(json.dumps(o) + "\n")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def now():
    return {"ts": int(time.time()), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def prereg():
    assert not os.path.exists(D + "/ledger.jsonl"), "ledger exists"
    led({"event": "preregistered", **now(), "sha256": sha(D + "/SHA256-frozen.txt")})


def freeze(name, event):
    h = sha(f"{D}/{name}")
    with open(D + "/SHA256-frozen.txt", "a") as f:
        f.write(f"{h}  {name}\n")
    led({"event": event, **now(), "sha256": h})


def words(s):
    return set(re.findall(r"\w+", s.lower()))


def prior_seeds():
    out = []
    for f in glob.glob(D + "/../**/*seeds.txt", recursive=True):
        if os.path.abspath(f).startswith(D + "/"):
            continue
        out += [l.rstrip("\n").split("|")[-1] for l in open(f) if l.strip()]
    return out


def make_seeds():
    brief = open(D + "/prompts/seed_brief.txt").read()
    prior = [words(s) for s in prior_seeds()]

    def one(dom):
        t = call(GEN, brief, f"Industry for this batch: {dom}. Write 14 archetypes.", 1500, 0.9, False)
        return [l.strip().lstrip("-*0123456789.) ").strip() for l in t.splitlines() if len(l.split()) >= 10]

    with ThreadPoolExecutor(6) as ex:
        cands = list(ex.map(one, DOMAINS))
    acc, accw = [], []
    for i in range(14):  # round robin over domains so no industry dominates
        for c in cands:
            if i < len(c) and len(acc) < N:
                w = words(c[i])
                if all(len(w & p) / len(w | p) <= 0.22 for p in prior + accw):
                    acc.append(c[i])
                    accw.append(w)
    if len(acc) < N:
        sys.exit(f"only {len(acc)} seeds passed the gate: re-run seeds (pre-freeze step)")
    open(D + "/prompts/seeds.txt", "w").write("".join(f"{i + 1}|{a}\n" for i, a in enumerate(acc)))


def tickets():
    return json.load(open(D + "/tickets.json"))


def shingles(t):
    w = re.findall(r"\w+", t.lower())
    return {tuple(w[i:i + 6]) for i in range(len(w) - 5)}


def make_tickets():
    brief = open(OLD + "/prompts/writer_brief.txt").read()
    seeds = [l.rstrip("\n").split("|", 1) for l in open(D + "/prompts/seeds.txt") if l.strip()]
    pool, ids, titles = set(), set(), set()
    for x in sorted(glob.glob(D + "/../*/")):
        if os.path.abspath(x) == D:
            continue
        for _, i, t, _ in BC.scenarios(BC.Path(x)):
            pool |= shingles(t)
            ids.add(i)
        for f in BC.scenario_files(BC.Path(x)):
            titles |= {str(s.get("title", "")).lower() for s in BC.load(f) or []}
    assert not any(i.startswith("sup-") for i in ids), "id namespace collision"
    got, shares = {}, {}

    def one(s):
        try:
            t = call(GEN, brief, f"Archetype: {s[1]}", 900, 0.9, False)
            o = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
            return {"id": f"sup-{int(s[0]):03d}", "archetype": s[1], **{k: o[k] for k in ("title", "ticket", "repo_context")}}
        except Exception:
            return None

    for _ in range(31):  # first draw plus up to 30 redraws (AMENDMENT-1.md; was 6), before any plan exists
        todo = [s for s in seeds if f"sup-{int(s[0]):03d}" not in got]
        if not todo:
            break
        with ThreadPoolExecutor(6) as ex:
            drawn = list(ex.map(one, todo))
        for t in sorted(filter(None, drawn), key=lambda t: t["id"]):
            sh = shingles(" ".join(t[k] for k in ("title", "ticket", "repo_context")))
            share = len(sh & pool) / len(sh) if sh else 1
            if share <= MAXSHARE and t["title"].lower() not in titles:
                got[t["id"]], shares[t["id"]] = t, share
                pool |= sh
                titles.add(t["title"].lower())
    if len(got) < N:
        sys.exit(f"{N - len(got)} tickets still fail the disjointness gate after 30 redraws")
    out = [got[k] for k in sorted(got)]
    json.dump(out, open(D + "/tickets.json", "w"), indent=1)
    print("max shingle share at accept time:", round(max(shares.values()), 3))


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
    print("superiority rule (CI lower bound > 0.5):", "PASS" if m["ci95"][0] > 0.5 else "FAIL")


if __name__ == "__main__":
    c, *a = sys.argv[1:]
    {"prereg": prereg, "seeds": make_seeds, "freeze": freeze, "tickets": make_tickets, "gen": gen, "judge": judge, "score": score}[c](*a)
