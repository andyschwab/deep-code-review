#!/usr/bin/env python3
"""CF vs TK driver. usage: drive.py smoke|run|verify|report. Everything lands under this dir. See PREREGISTERED.md."""
import concurrent.futures as cf, json, random, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]  # repo root; the original run used a checkout copy under src/
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / ".claude/skills/deep-code-review/scripts"))
import bench_corpus as bc  # noqa: E402
import score_review as sr  # noqa: E402

CORPUS = ROOT / "scripts/eval-fixtures/bench"
CAP, JOBS = 20.0, 4
RESERVE = {"claude-sonnet-5-5": 0.60, "claude-opus-5-5": 1.00}
SYS = {"CF": (D / "prompts/cf_system.md").read_text(), "TK": (D / "prompts/tk_system.md").read_text()}
FLAGS = ["-p", "--setting-sources", "project,local", "--strict-mcp-config", "--tools", "Read,Grep,Glob",
         "--allowedTools", "Read", "Grep", "Glob", "--output-format", "json", "--no-session-persistence"]
LOCK = threading.Lock(); INFLIGHT = {"n": 0.0}


class Cap(Exception): pass


def spent():
    p = D / "ledger.jsonl"
    return sum(json.loads(l)["cost"] for l in p.read_text().splitlines()) if p.exists() else 0.0


def call(prompt, cwd, model, system, tag):
    """One claude -p call; cost ledgered; cap checked (with in-flight reserve) before the call. -> (text, err)"""
    r = RESERVE[model]
    with LOCK:
        if spent() + INFLIGHT["n"] + r > CAP:
            raise Cap(f"cap ${CAP} would be exceeded: spent {spent():.3f}")
        INFLIGHT["n"] += r
    cost, txt, err, t = 0.0, "", "", time.time()
    try:
        cmd = ["claude", *FLAGS[:1], "--model", model, *FLAGS[1:]] + (["--system-prompt", system] if system else [])
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, timeout=1500)
        try:
            j = json.loads(p.stdout)
            txt, cost = j.get("result") or "", float(j.get("total_cost_usd") or 0)
            err = "claude error" if (j.get("is_error") or p.returncode) else "" if txt.strip() else "empty output"
        except ValueError:
            err = f"exit {p.returncode}, unparsable: {p.stderr[:200]}"
    except (subprocess.TimeoutExpired, OSError) as e:
        err = type(e).__name__
    finally:
        with LOCK:
            INFLIGHT["n"] -= r
            with open(D / "ledger.jsonl", "a") as f:
                f.write(json.dumps(dict(ts=time.strftime("%FT%TZ", time.gmtime()), tag=tag, model=model, cost=cost, sec=round(time.time() - t, 1), err=err)) + "\n")
    return txt, err


def ws(cid):
    w = Path(tempfile.mkdtemp(prefix="bench-"))
    shutil.copy(CORPUS / "train" / cid / "change.patch", w)
    return w


def ids():
    man = json.loads((CORPUS / "manifest.json").read_text())
    return sorted(m["id"] for m in man if m["split"] == "train" and (CORPUS / "train" / m["id"]).is_dir())


def review(cid, arm):
    p = D / "outputs" / arm / f"{cid}.json"
    if p.exists() and not json.loads(p.read_text()).get("error"):
        return cid, "cached"
    p.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        w = ws(cid)
        try:
            txt, err = call(bc.PRODUCER, w, "claude-sonnet-5-5", SYS[arm], f"review/{arm}/{cid}/{attempt}")
        finally:
            shutil.rmtree(w, ignore_errors=True)
        f = None if err else bc.parse_array(txt)
        err = err or ("" if f is not None else "no JSON array in output")
        rec = dict(id=cid, arm=arm, findings=f or [], raw=txt, error=err, attempts=attempt)
        p.write_text(json.dumps(rec, indent=1))
        if not err:
            break
    return cid, rec["error"] or len(rec["findings"])


def verify(cid, arm):
    p = D / "outputs" / arm / f"{cid}.json"
    rec = json.loads(p.read_text())
    if rec.get("error") or "verdicts" in rec and not rec.get("verify_error"):
        return cid, "skip"
    truth = json.loads((CORPUS / "train" / cid / "ground-truth.json").read_text())
    rec["matched"] = [bool(sr.score(truth, [f])["hit"]) for f in rec["findings"]]
    rec["verdicts"] = {}; rec["verify_error"] = ""
    un = [(i, f) for i, f in enumerate(rec["findings"]) if not rec["matched"][i]]
    for attempt in (1, 2):
        if not un:
            break
        w = ws(cid)
        try:
            bug = "; ".join(b["bug"] for b in truth["bugs"])
            listing = "\n".join(f"{i}. [{f.get('file')}:{f.get('line')}] {f.get('text')}" for i, f in un)
            txt, err = call(bc.VERIFY.format(bug=bug, findings=listing), w, "claude-opus-5-5", None, f"verify/{arm}/{cid}/{attempt}")
        finally:
            shutil.rmtree(w, ignore_errors=True)
        vs = None if err else bc.parse_array(txt, "verdict")
        rec["verify_error"] = err or ("" if vs is not None else "no JSON array in verifier output")
        rec["verdicts"] = {str(v.get("i")): {"verdict": v.get("verdict"), "reason": v.get("reason")} for v in vs or []}
        if not rec["verify_error"]:
            break
    p.write_text(json.dumps(rec, indent=1))
    return cid, rec["verify_error"] or len(un)


T0 = time.time()


def stage(fn):
    """Run fn over (case, arm); stop starting new jobs after 480s so a foreground call fits the tool timeout. Rerun to resume."""
    fn0 = fn
    fn = lambda c, a: fn0(c, a) if time.time() - T0 < 480 else (c, "deferred")
    jobs = [(c, a) for c in ids() for a in ("CF", "TK")]
    try:
        with cf.ThreadPoolExecutor(JOBS) as ex:
            for r in ex.map(lambda ca: fn(*ca), jobs):
                print(*r, f"spent={spent():.3f}", flush=True)
    except Cap as e:
        print("CAP STOP:", e, flush=True); (D / "INCOMPLETE").write_text(str(e))


def tally(cid, arm):
    rec = json.loads((D / "outputs" / arm / f"{cid}.json").read_text())
    if rec.get("error") or rec.get("verify_error") or "verdicts" not in rec:
        return None
    truth = json.loads((CORPUS / "train" / cid / "ground-truth.json").read_text())
    vd = rec["verdicts"]; un = [i for i, m in enumerate(rec["matched"]) if not m]
    gts = any(vd.get(str(i), {}).get("verdict") == "gt_same" for i in un)
    good = sum(rec["matched"]) + sum(vd.get(str(i), {}).get("verdict") in ("real", "gt_same") for i in un)
    n_hit = len(sr.score(truth, rec["findings"])["hit"])
    nb = len(truth["bugs"])
    return dict(n=len(rec["findings"]), good=good, bugs=nb, hit=n_hit, cred=nb if gts else n_hit)  # one bug per case: gt_same credits it


def pci(rows, num, den, B=10000, seed=1):
    rng = random.Random(seed); n = len(rows)
    f = lambda rs: (sum(num(r[0]) for r in rs) / max(1, sum(den(r[0]) for r in rs))) - (sum(num(r[1]) for r in rs) / max(1, sum(den(r[1]) for r in rs)))
    ds = sorted(f([rows[rng.randrange(n)] for _ in range(n)]) for _ in range(B))
    return f(rows), ds[int(0.025 * B)], ds[int(0.975 * B) - 1]


def report():
    rows, drops = [], []
    for c in ids():
        a, b = tally(c, "CF"), tally(c, "TK")
        (rows.append((a, b)) if a and b else drops.append(c))
    n = len(rows)
    p, pl, ph = pci(rows, lambda r: r["good"], lambda r: r["n"])
    r_, rl, rh = pci(rows, lambda r: r["cred"], lambda r: r["bugs"])
    s = lambda k, i: sum(r[i][k] for r in rows)
    agg = {arm: dict(findings=s("n", i), good=s("good", i), prec=round(s("good", i) / max(1, s("n", i)), 3), bugs=s("bugs", i),
                     cred=s("cred", i), recall=round(s("cred", i) / max(1, s("bugs", i)), 3)) for i, arm in ((0, "CF"), (1, "TK"))}
    prim, sec = p > 0 and pl > 0, r_ >= -0.03
    w = lambda new, old: round((62 * old + n * new) / (62 + n), 3)
    out = dict(n=n, dropped=drops, arms=agg, precision_diff=dict(d=round(p, 3), ci=[round(pl, 3), round(ph, 3)]),
               recall_diff=dict(d=round(r_, 3), ci=[round(rl, 3), round(rh, 3)]), primary_met=prim, secondary_met=sec,
               verdict="PASS" if prim and sec and not (D / "INCOMPLETE").exists() else "FAIL", spend=round(spent(), 3),
               pooled_approx=dict(note="weighted point values; old raw data lost; no CI", cf_precision=w(agg["CF"]["prec"], .951),
                                  tk_precision=w(agg["TK"]["prec"], .912), cf_recall=w(agg["CF"]["recall"], .258), tk_recall=w(agg["TK"]["recall"], .274)))
    (D / "results.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "smoke":
        w = ws(ids()[0])
        for m in RESERVE:
            print(m, call("Reply with the single word OK.", w, m, None, "smoke"))
        shutil.rmtree(w, ignore_errors=True)
    elif c == "run": stage(review)
    elif c == "verify": stage(verify)
    elif c == "report": report()
