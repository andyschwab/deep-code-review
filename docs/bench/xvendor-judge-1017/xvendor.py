#!/usr/bin/env python3
"""Cross-vendor re-judge of the committed rival benches (2026-10-17). usage: xvendor.py smoke|judge|review|tiebreak|report

Re-judges the committed raw outputs under docs/bench/ with Qwen3.5-397B-A17B (PCSS, OpenAI-compatible), blind and
with the original judge prompt. Pairwise benches: every original (first, second) order is re-judged; the arm
labels are hidden (Response 1/2 only) and job order is shuffled with a fixed seed. Review benches (H7, H7b): the
per-finding verifier of scripts/bench_corpus.VERIFY is re-run with the patch inlined (no tools). Where Qwen and
the original judge disagree, GLM-5.2 re-judges the same item and the median of the three is the tiebreak result. Judgments with no original verdict (e.g. 5 of 10 scenarios of H1e new vs rival) keep Qwen's score alone, so a tiebreak column mixes medians and Qwen-only scores.
Raw verdicts go to verdicts-qwen.jsonl / verdicts-glm52.jsonl (append-only cache, rerun resumes); report writes results.json.
Key: env PCSS_KEY, else PCSS_KEY= in the nearest .env above this file. Never printed. Spend: $0 (no claude -p call).
"""
import concurrent.futures as cf, json, os, random, re, statistics, sys, threading, time, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
B = D.parent  # docs/bench
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / ".claude/skills/deep-code-review/scripts"))
import bench_corpus as bc  # noqa: E402
import score_review as sr  # noqa: E402

URL = "https://llm.hpc.psnc.pl/v1/chat/completions"
QWEN, GLM = "Qwen3.5-397B-A17B", "GLM-5.2"
CORPUS = ROOT / "scripts/eval-fixtures/bench/train"
LOCK = threading.Lock()


def key():
    if os.environ.get("PCSS_KEY"):
        return os.environ["PCSS_KEY"]
    for p in D.parents:
        e = p / ".env"
        if e.exists():
            for l in e.read_text().splitlines():
                if l.startswith("PCSS_KEY="):
                    return l.split("=", 1)[1].strip().strip("\"'")
    sys.exit("no PCSS_KEY")


KEY = key()


def chat(model, system, user, temp=0.0, mx=6000):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    extra = {"chat_template_kwargs": {"enable_thinking": False}} if model == GLM else {}  # GLM-5.2 thinks by default: 200+ s per call and the answer is often cut off
    body = json.dumps({"model": model, "messages": msgs, "temperature": temp, "max_tokens": mx, **extra}).encode()
    for i in range(4):
        try:
            r = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            ch = json.load(urllib.request.urlopen(r, timeout=900))["choices"][0]
            if ch.get("finish_reason") == "length" and mx < 30000:  # truncated (reasoning ate the budget): retry once with a bigger cap
                return chat(model, system, user, temp, 30000)
            return re.sub(r"<think>.*?</think>", "", ch["message"].get("content") or "", flags=re.S).strip()
        except Exception as e:  # noqa: BLE001 - network/HTTP; retry then give up
            time.sleep(5 * (i + 1)); err = type(e).__name__
    return "ERR " + err


def jobj(txt):
    for m in re.finditer(r"\{.*\}", txt, re.S):
        try:
            return json.loads(m.group(0))
        except ValueError:
            continue


class Cache:
    def __init__(self, name):
        self.p = D / name; self.d = {}
        if self.p.exists():
            for l in self.p.read_text().splitlines():
                r = json.loads(l); self.d[r["key"]] = r

    def put(self, k, **v):
        with LOCK:
            self.d[k] = dict(key=k, **v)
            with open(self.p, "a") as f:
                f.write(json.dumps(self.d[k]) + "\n")


CACHE = {QWEN: Cache("verdicts-qwen.jsonl"), GLM: Cache("verdicts-glm52.jsonl")}

# ---- pairwise benches: (name, dir, set, judge dir, judge prompt, pairs x,y with x = Perun-side arm)
PW = [
    ("H1d idea-critic", "idea-critic-rubricfree-1016", "", "judge", "judge.txt", [("PERUN", "RIVAL")]),
    ("H1c communication-structure", "comms-rubricfree-1016", "", "judge", "judge.txt", [("PERUN", "RIVAL")]),
    ("H1d product-discovery", "product-discovery-rubricfree-1016", "", "judge", "judge.txt", [("PERUN", "RIVAL")]),
    ("H1d growth-analytics", "growth-analytics-rubricfree-1016", "", "judge", "judge.txt", [("PERUN", "RIVAL")]),
    ("H1e idea-critic v2", "idea-critic-v2-1016", "", "judge", "judge.txt", [("NEW", "OLD"), ("NEW", "RIVAL")]),
    ("H1f communication-structure fix", "comms-quality-1016", "", "judge", "judge.txt", [("PERUN", "RIVAL"), ("PERUN", "PLAIN"), ("PERUN2", "PLAIN")]),
    ("H1b pos set A rubric", "pos-1016", "A", "judge", "judge.txt", [("PERUN_BASE", "RIVAL")]),
    ("H1b pos set A rubric-free", "pos-1016", "A", "judge_neutral", "judge_neutral.txt", [("PERUN_BASE", "RIVAL")]),
    ("H1b pos set B base rubric-free", "pos-1016", "B", "judge_neutral", "judge_neutral.txt", [("PERUN_BASE", "RIVAL")]),
    ("H1b pos set B edit rubric", "pos-1016", "B", "judge", "judge.txt", [("PERUN_FIX", "RIVAL")]),
    ("H1b pos set B edit rubric-free", "pos-1016", "B", "judge_neutral", "judge_neutral.txt", [("PERUN_FIX", "RIVAL")]),
]
SC = {"1": 1.0, "2": 0.0, "tie": 0.5}  # score for Response 1


def items():
    """Every (bench, pair, scenario, order) with both outputs on disk. -> list of dicts; orig = original score for the first-shown arm or None."""
    out = []
    for name, d, st, jd, jp, pairs in PW:
        base = B / d
        scs = json.loads((base / ("scenarios/%s.json" % st if st else "scenarios.json")).read_text())
        for x, y in pairs:
            for sc in scs:
                for f, s in ((x, y), (y, x)):
                    o = [base / "outputs" / st / a / f"{sc['id']}.txt" for a in (f, s)]
                    if not all(p.exists() for p in o):
                        continue
                    op = base / jd / st / f"{f}__{s}" / f"{sc['id']}.json"
                    ov = json.loads(op.read_text())["verdict"] if op.exists() else None
                    out.append(dict(bench=name, x=x, y=y, f=f, s=s, id=sc["id"], orig=SC.get(ov),
                                    key=f"{name}|{x}-{y}|{f}__{s}|{sc['id']}",
                                    system=(base / "prompts" / jp).read_text(),
                                    user=f"REQUEST:\n{sc['prompt']}\n\n=== Response 1 ===\n{o[0].read_text()}\n\n=== Response 2 ===\n{o[1].read_text()}\n"))
    return out


def one_judge(it, model):
    c = CACHE[model]
    if it["key"] in c.d:
        return
    for temp in (0.0, 0.3, 0.3):
        j = jobj(chat(model, it["system"], it["user"], temp))
        if isinstance(j, dict) and j.get("verdict") in SC:
            return c.put(it["key"], verdict=j["verdict"], reason=j.get("reason", ""), model=model)
    print("JUDGE FAIL", it["key"], flush=True)


def pmap(fn, jobs, n=6):
    random.Random(1017).shuffle(jobs)  # fixed-seed shuffle: no arm or bench grouping in call order
    with cf.ThreadPoolExecutor(n) as ex:
        list(ex.map(fn, jobs))


def sx(it, verdict):
    """Score for it['x'] (the Perun-side arm) from a verdict on the shown order."""
    s = SC[verdict]
    return s if it["f"] == it["x"] else 1 - s


# ---- review benches
REV = [("cf-vs-tk-1016", "CF"), ("cf-vs-tk-1016", "TK"), ("cf-vs-tk-1016", "CFHUNT"), ("review-real-skill-1016", "REAL"), ("review-real-skill-1016", "TK")]
HELD = json.loads((B / "cf-vs-tk-1016/split.json").read_text())["heldout"]
R22 = [l.strip() for l in (B / "review-real-skill-1016/ids.txt").read_text().split() if l.strip()]
CLS = {"gt_same": 2, "real": 1}
VERIFY = bc.VERIFY.replace("./change.patch is the reviewed change; ./context/ holds the pre-fix version of the changed file(s). Write no files.",
                           "The reviewed change is the unified diff below. Reason from it alone.").replace(
    "by reading the code", "by reading the diff").replace("Your FINAL message must be ONLY a JSON array:", "Reply with ONLY a JSON array:")


def recs(src, arm):
    ids = HELD if arm == "CFHUNT" else R22 if src.startswith("review-real") else sorted(p.name for p in CORPUS.iterdir() if p.is_dir())
    for cid in ids:
        p = B / src / "outputs" / arm / f"{cid}.json"
        if p.exists():
            r = json.loads(p.read_text())
            if not r.get("error") and not r.get("verify_error") and "verdicts" in r:
                yield cid, r


def rev_job(job):
    src, arm, cid, rec, model, only = job
    c = CACHE[model]; k = f"rev|{src}|{arm}|{cid}"
    if k in c.d:
        return
    un = [(i, f) for i, f in enumerate(rec["findings"]) if not rec["matched"][i] and (only is None or i in only)]
    if not un:
        return c.put(k, verdicts={}, model=model)
    truth = json.loads((CORPUS / cid / "ground-truth.json").read_text())
    listing = "\n".join(f"{i}. [{f.get('file')}:{f.get('line')}] {f.get('text')}" for i, f in un)
    user = VERIFY.format(bug="; ".join(b["bug"] for b in truth["bugs"]), findings=listing) + "\n\nDIFF:\n" + (CORPUS / cid / "change.patch").read_text()
    for temp in (0.0, 0.3, 0.3):
        vs = bc.parse_array(chat(model, None, user, temp), "verdict")
        if vs is not None and {int(v.get("i", -1)) for v in vs} >= {i for i, _ in un}:
            return c.put(k, verdicts={str(v["i"]): {"verdict": v["verdict"], "reason": v.get("reason", "")} for v in vs}, model=model)
    print("VERIFY FAIL", k, flush=True)


def disagree(src, arm, cid, rec):
    """Unmatched finding indices where Qwen's class differs from the original verifier's."""
    q = CACHE[QWEN].d.get(f"rev|{src}|{arm}|{cid}")
    if not q:
        return set()
    cl = lambda v: CLS.get((v or {}).get("verdict"), 0)
    return {int(i) for i, v in q["verdicts"].items() if cl(v) != cl(rec["verdicts"].get(i))}


# ---- stats (same recipes as the original drivers)
def boot(vals, n=10000, seed=1):
    rng, m = random.Random(seed), len(vals)
    bs = sorted(sum(vals[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return round(bs[int(0.025 * n)], 3), round(bs[int(0.975 * n) - 1], 3)


def tb_score(s_o, s_q, s_g):
    """Tiebreak score for one judgment: median of original, Qwen and GLM-5.2 (all as the Perun-side arm's score)."""
    return statistics.median([s_o, s_q, s_g])


def wr(per):
    """per = {scenario: [scores]} -> win rate [CI], verdict, splits. Same rule as the original benches (PASS needs CI lower bound > 0.5)."""
    v = [statistics.mean(s) for s in per.values()]
    lo, hi = boot(v)
    return dict(n=len(v), win=round(statistics.mean(v), 3), ci=[lo, hi], splits=sum(1 for x in v if x == 0.5), wins=sum(1 for x in v if x > 0.5), losses=sum(1 for x in v if x < 0.5),
                verdict="PASS" if lo > 0.5 else "LOSS" if hi < 0.5 else "FAIL")


def prf(rows):
    P = sum(r["good"] for r in rows) / max(1, sum(r["n"] for r in rows)); R = sum(r["cred"] for r in rows) / max(1, sum(r["bugs"] for r in rows))
    return P, R, (2 * P * R / (P + R) if P + R else 0.0)


def pdiff(a, b, n=10000, seed=1):
    rng, m = random.Random(seed), len(a); ds = [[], [], []]
    for _ in range(n):
        ix = [rng.randrange(m) for _ in range(m)]
        for k, (x, y) in enumerate(zip(prf([a[i] for i in ix]), prf([b[i] for i in ix]))):
            ds[k].append(x - y)
    full = [x - y for x, y in zip(prf(a), prf(b))]
    return {nm: dict(d=round(full[k], 3), ci=[round(sorted(ds[k])[int(.025 * n)], 3), round(sorted(ds[k])[int(.975 * n) - 1], 3)]) for k, nm in enumerate(("precision", "recall", "f1"))}


def verdicts_for(src, arm, cid, rec, mode):
    """Per-finding verdict dict for mode orig | qwen | tb (median class of orig, qwen, GLM where Qwen disagrees)."""
    o = rec["verdicts"]
    if mode == "orig":
        return o
    q = CACHE[QWEN].d[f"rev|{src}|{arm}|{cid}"]["verdicts"]
    if mode == "qwen":
        return q
    g = (CACHE[GLM].d.get(f"rev|{src}|{arm}|{cid}") or {}).get("verdicts", {})
    cl = lambda v: CLS.get((v or {}).get("verdict"), 0)
    out = {}
    for i, v in q.items():
        if i in g and cl(v) != cl(o.get(i)):
            trio = sorted([o.get(i), v, g[i]], key=cl); v = trio[1]
        out[i] = v
    return out


def tally(cid, rec, vd):
    truth = json.loads((CORPUS / cid / "ground-truth.json").read_text())
    un = [i for i, m in enumerate(rec["matched"]) if not m]
    gts = any(vd.get(str(i), {}).get("verdict") == "gt_same" for i in un)
    good = sum(rec["matched"]) + sum(vd.get(str(i), {}).get("verdict") in ("real", "gt_same") for i in un)
    nb = len(truth["bugs"])
    return dict(n=len(rec["findings"]), good=good, bugs=nb, cred=nb if gts else len(sr.score(truth, rec["findings"])["hit"]))


COMPARE = [("H7 CF vs TK (43 cases)", ("cf-vs-tk-1016", "CF"), ("cf-vs-tk-1016", "TK"), None),
           ("H7 CFHUNT vs TK (22 held-out)", ("cf-vs-tk-1016", "CFHUNT"), ("cf-vs-tk-1016", "TK"), HELD),
           ("H7b real skill vs TK (22 cases)", ("review-real-skill-1016", "REAL"), ("review-real-skill-1016", "TK"), None),
           ("H7b context: CF vs TK on the 22 cases", ("cf-vs-tk-1016", "CF"), ("cf-vs-tk-1016", "TK"), R22)]


def report():
    res = dict(judge=QWEN, tiebreak=GLM, pairwise=[], review=[])
    its = items()
    # which slot each judge picked, per bench: a value far from the order-neutral 0.5 first-slot share flags position bias
    res["position"], res["position_total"] = {}, {}
    for it in its:
        for who, v in (("original", it["orig"] is not None and {1.0: "1", 0.0: "2", 0.5: "tie"}[it["orig"]]), ("qwen", (CACHE[QWEN].d.get(it["key"]) or {}).get("verdict")),
                       ("glm", (CACHE[GLM].d.get(it["key"]) or {}).get("verdict"))):  # glm: only the tiebreak items (where Qwen differed)
            if v:
                for c in (res["position"].setdefault(it["bench"], {}).setdefault(who, {"1": 0, "2": 0, "tie": 0}), res["position_total"].setdefault(who, {"1": 0, "2": 0, "tie": 0})):
                    c[v] += 1
    for name, _, _, jd, _, pairs in PW:
        for x, y in pairs:
            sel = [i for i in its if i["bench"] == name and i["x"] == x and i["y"] == y]
            ids_ = sorted({i["id"] for i in sel})
            orig, qw, tb, qm = {}, {}, {}, {}
            miss = dis = glm_fail = 0
            for i in sel:
                q = CACHE[QWEN].d.get(i["key"])
                if not q:
                    miss += 1; continue
                s_q = sx(i, q["verdict"]); qw.setdefault(i["id"], []).append(s_q)
                s_t = s_q
                if i["orig"] is not None:
                    s_o = i["orig"] if i["f"] == i["x"] else 1 - i["orig"]
                    orig.setdefault(i["id"], []).append(s_o); qm.setdefault(i["id"], []).append(s_q)
                    if s_o != s_q:
                        dis += 1; g = CACHE[GLM].d.get(i["key"])
                        if g: s_t = tb_score(s_o, s_q, sx(i, g["verdict"]))
                        else: glm_fail += 1
                # no original verdict (H1e new vs rival: 5 of 10 scenarios) -> s_t stays Qwen alone: the tiebreak column is a mix of medians and Qwen-only scores
                tb.setdefault(i["id"], []).append(s_t)
            res["pairwise"].append(dict(row=name, x=x, y=y, judge_dir=jd, items=len(sel), missing_qwen=miss, disagreements=dis, glm_missing=glm_fail,
                                        original=wr(orig) if orig else None, qwen=wr(qw) if qw else None,
                                        qwen_on_original_items=wr(qm) if qm else None, tiebreak=wr(tb) if tb else None,
                                        scenarios_with_original=len(orig), tiebreak_qwen_only_scenarios=len(set(tb) - set(orig))))
    for name, (s1, a1), (s2, a2), only in COMPARE:
        rows = {m: [] for m in ("orig", "qwen", "tb")}; drop = []
        A = dict(recs(s1, a1)); T = dict(recs(s2, a2))
        for cid in sorted(set(A) & set(T)):
            if only is not None and cid not in only:
                continue
            ok = all(f"rev|{s}|{a}|{cid}" in CACHE[QWEN].d for s, a in ((s1, a1), (s2, a2)))
            if not ok:
                drop.append(cid); continue
            for m in rows:
                rows[m].append((tally(cid, A[cid], verdicts_for(s1, a1, cid, A[cid], m)), tally(cid, T[cid], verdicts_for(s2, a2, cid, T[cid], m))))
        row = dict(row=name, n=len(rows["orig"]), dropped=drop)
        for m, rs in rows.items():
            if rs:
                x_, y_ = [r[0] for r in rs], [r[1] for r in rs]
                row[m] = dict(arm=dict(zip(("precision", "recall", "f1"), map(lambda v: round(v, 3), prf(x_)))), tk=dict(zip(("precision", "recall", "f1"), map(lambda v: round(v, 3), prf(y_)))), diff=pdiff(x_, y_))
        dis = sum(len(disagree(s, a, c, r)) for s, a in ((s1, a1), (s2, a2)) for c, r in recs(s, a) if (only is None or c in only))
        row["finding_disagreements"] = dis
        res["review"].append(row)
    (D / "results.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "smoke":
        print(chat(QWEN, 'Output only JSON: {"verdict": "1" or "2"}', "Which is bigger, Response 1: 3 or Response 2: 7?"), flush=True)
        print(chat(GLM, 'Output only JSON: {"verdict": "1" or "2"}', "Which is bigger, Response 1: 3 or Response 2: 7?"))
    elif c == "judge":
        pmap(lambda i: one_judge(i, QWEN), items())
    elif c == "review":
        pmap(rev_job, [(s, a, cid, r, QWEN, None) for s, a in REV for cid, r in recs(s, a)])
    elif c == "tiebreak":
        pmap(lambda i: one_judge(i, GLM), [i for i in items() if i["orig"] is not None and i["key"] in CACHE[QWEN].d and i["orig"] != SC[CACHE[QWEN].d[i["key"]]["verdict"]]])
        pmap(rev_job, [(s, a, cid, r, GLM, ix) for s, a in REV for cid, r in recs(s, a) if (ix := disagree(s, a, cid, r))])
    elif c == "report":
        report()
