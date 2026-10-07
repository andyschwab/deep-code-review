#!/usr/bin/env python3
"""Review benchmark runner: real bug-fix corpus, strict train/test split, reviewer arms, strict + verified precision.

  bench_corpus.py split IDS...                    print the deterministic split for case ids
  bench_corpus.py run    --corpus D --arm A --out O [--split test] [--skill DIR] [--jobs N]
  bench_corpus.py verify --corpus D --arm A --out O [--split test]
  bench_corpus.py report --corpus D --out O [--split test]

Corpus layout (one dir per case): change.patch (what the reviewer sees), ground-truth.json (score_review.py
format: one bug with a `match` regex), meta.json (url, licence, SHAs, label), optional context/ (pre-fix file
the verifier may read). manifest.json at the corpus root lists {id, split}.

Split rule: real cases sorted by sha256(id); the first len//3 are TRAIN, the rest TEST. A case already public
in this repository (the PR #1354 held-out fixture) is TRAIN by rule, never TEST. TEST ground truth must never
reach anyone tuning the skill: only the runner and the verifier read it.

Arms: perun (skill, one pass), perun-gap (the perun pass + a seeded gap-hunt pass, union; needs the perun arm run first), plain (no skill), tools
(shellcheck on shell cases, semgrep elsewhere, when installed). Reviewers are `claude -p` sessions with only
read tools, no user settings, and see change.patch alone. Verifier: a separate session reads the patch and the
pre-fix file and labels each strict-unmatched finding real | gt_same | not_a_bug | unverifiable (gt_same = same bug as
the reference, i.e. a matcher miss). Metrics: strict recall/precision (score_review.py), adjudicated recall
(strict hit or gt_same), verified precision ((matched + real + gt_same) / findings), cost and wall time. Stdlib only.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_review as sr  # noqa: E402

PRODUCER = """Review the change in ./change.patch (a diff of one or more source files; no git history exists, do not search outside this directory). Find real defects the change introduces: wrong behavior, unhandled edge cases, fail-open checks, injection, resource or data-loss bugs. Skip style nits. Write no files.
Your FINAL message must be ONLY a JSON array, no prose and no code fence: [{"file": "<basename>", "line": <int or null>, "severity": "high|medium|low", "text": "<the bug mechanism and a concrete failing input, one or two sentences>"}]. Use [] if you find nothing."""
PERUN = "Load and follow .claude/skills/deep-code-review/SKILL.md and apply its method end to end: read SKILL.md and every reference it routes DIFF-mode reviews to before you review. Review in DIFF mode. " + PRODUCER
GAP = """A first review of ./change.patch already reported these findings:
{seed}
Re-review the same change and hunt ONLY for defects the first pass missed; do not repeat or rephrase anything listed. Verify each candidate against the diff before reporting it. Write no files.
Your FINAL message must be ONLY a JSON array of the NEW findings, same shape as above: [{{"file": "<basename>", "line": <int or null>, "severity": "high|medium|low", "text": "<mechanism and failing input>"}}]. Use [] if nothing new."""
VERIFY = """You verify code-review findings. ./change.patch is the reviewed change; ./context/ holds the pre-fix version of the changed file(s). Write no files.
REFERENCE BUG (known real defect in this change): {bug}
For each finding below decide, by reading the code: "gt_same" if it describes the reference bug (any wording), "real" if it is a different genuine defect you can confirm from the code, "not_a_bug" if the code does not behave as claimed or it is style/by-design, "unverifiable" if the code cannot settle it.
FINDINGS:
{findings}
Your FINAL message must be ONLY a JSON array: [{{"i": <index>, "verdict": "real|gt_same|not_a_bug|unverifiable", "reason": "<one sentence>"}}]."""
GAP_SKILL = "Load and follow .claude/skills/deep-code-review/SKILL.md for method. "
ARMS = ("perun", "perun-gap", "plain", "tools")


def split_ids(real, public=()):
    order = sorted(real, key=lambda i: hashlib.sha256(i.encode()).hexdigest())
    n = len(real) // 3
    return {**{i: "train" for i in order[:n]}, **{i: "test" for i in order[n:]}, **{i: "train" for i in public}}


def claude(prompt, cwd, model="sonnet"):
    """One read-only `claude -p` session; returns (final text, cost usd, seconds, turns). No user settings, no persistence."""
    t = time.time()
    p = subprocess.run(["claude", "-p", "--model", model, "--setting-sources", "project,local", "--output-format", "json",
                        "--no-session-persistence", "--allowedTools", "Read", "Grep", "Glob"],
                       input=prompt, capture_output=True, text=True, cwd=cwd, timeout=1500)
    try:
        j = json.loads(p.stdout)
    except ValueError:
        return "", 0.0, time.time() - t, 0
    return j.get("result", ""), float(j.get("total_cost_usd") or 0), time.time() - t, int(j.get("num_turns") or 0)


def parse_array(text, key="text"):
    """Last top-level JSON array of dicts carrying `key` in text; [] when absent or malformed."""
    for m in reversed([m.start() for m in re.finditer(r"\[", text)]):
        try:
            v = json.loads(text[m:text.rindex("]") + 1])
        except ValueError:
            continue
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict) and key in x]
    return []


def cases(corpus, split):
    man = {m["id"]: m["split"] for m in json.loads((corpus / "manifest.json").read_text())}
    return sorted(i for i, s in man.items() if s == split and (corpus / i).is_dir())


def workspace(corpus, cid, skill):
    w = Path(tempfile.mkdtemp(prefix=f"bench-{cid}-"))
    shutil.copy(corpus / cid / "change.patch", w)
    if skill:
        shutil.copytree(skill, w / ".claude/skills/deep-code-review")
    return w


def tool_findings(corpus, cid):
    meta = json.loads((corpus / cid / "meta.json").read_text())
    out = []
    for f in meta["files"]:
        p = corpus / cid / "context" / Path(f).name
        if meta["lang"] == "shell" and shutil.which("shellcheck"):
            r = subprocess.run(["shellcheck", "-f", "json", str(p)], capture_output=True, text=True)
            out += [{"file": Path(f).name, "line": x["line"], "text": f"SC{x['code']}: {x['message']}"} for x in json.loads(r.stdout or "[]")]
        elif meta["lang"] != "shell" and shutil.which("semgrep"):
            r = subprocess.run(["semgrep", "--config", "p/default", "--metrics", "off", "--json", "--quiet", str(p)], capture_output=True, text=True)
            try:
                out += [{"file": Path(f).name, "line": x["start"]["line"], "text": x["check_id"] + ": " + x["extra"]["message"]} for x in json.loads(r.stdout or "{}").get("results", [])]
            except ValueError:
                pass
    return out


def run_case(corpus, cid, arm, out, skill):
    d = out / arm; d.mkdir(parents=True, exist_ok=True)
    if arm == "tools":
        t = time.time(); f = tool_findings(corpus, cid)
        rec = dict(id=cid, arm=arm, findings=f, cost=0.0, seconds=round(time.time() - t, 2))
    else:
        w = workspace(corpus, cid, skill if arm.startswith("perun") else None)
        try:
            if arm == "perun-gap":  # pass 1 = the perun arm's record for this case; this adds the seeded gap pass
                p1 = json.loads((out / "perun" / f"{cid}.json").read_text())
                txt, f, cost, sec, turns, raw = "", list(p1["findings"]), p1["cost"], p1["seconds"], p1["turns"], p1["raw"]
                txt2, c2, s2, t2 = claude(GAP_SKILL + GAP.format(seed=json.dumps(f, indent=1)), w)
                f += parse_array(txt2); cost += c2; sec += s2; turns += t2; raw += "\n=====GAP=====\n" + txt2
            else:
                txt, cost, sec, turns = claude(PERUN if arm == "perun" else PRODUCER, w)
                f, raw = parse_array(txt), txt
            rec = dict(id=cid, arm=arm, findings=f, cost=round(cost, 4), seconds=round(sec, 1), turns=turns, raw=raw)
        finally:
            shutil.rmtree(w, ignore_errors=True)
    (d / f"{cid}.json").write_text(json.dumps(rec, indent=1))
    return cid, len(rec["findings"]), rec["cost"]


def verify_case(corpus, cid, arm, out):
    p = out / arm / f"{cid}.json"; rec = json.loads(p.read_text())
    truth = json.loads((corpus / cid / "ground-truth.json").read_text())
    extras = [(i, f) for i, f in enumerate(rec["findings"]) if not sr.score(truth, [f])["hit"]]
    rec["verdicts"] = {}
    if extras:
        w = Path(tempfile.mkdtemp(prefix=f"verify-{cid}-"))
        try:
            shutil.copy(corpus / cid / "change.patch", w)
            if (corpus / cid / "context").is_dir():
                shutil.copytree(corpus / cid / "context", w / "context")
            bug = "; ".join(b["bug"] for b in truth["bugs"])
            listing = "\n".join(f"{i}. [{f.get('file')}:{f.get('line')}] {f.get('text')}" for i, f in extras)
            txt, cost, _, _ = claude(VERIFY.format(bug=bug, findings=listing), w)
            rec["verify_cost"] = round(cost, 4)
            for v in parse_array(txt, "verdict"):
                rec["verdicts"][str(v.get("i"))] = {"verdict": v.get("verdict"), "reason": v.get("reason")}
        finally:
            shutil.rmtree(w, ignore_errors=True)
    p.write_text(json.dumps(rec, indent=1))
    return cid, len(extras)


def metrics(corpus, ids, arm, out):
    n_bug = hit = adj = nf = matched = real = 0; cost = sec = vcost = 0.0; k = 0
    for cid in ids:
        p = out / arm / f"{cid}.json"
        if not p.exists():
            continue
        k += 1; rec = json.loads(p.read_text()); truth = json.loads((corpus / cid / "ground-truth.json").read_text())
        s = sr.score(truth, rec["findings"]); v = rec.get("verdicts", {}).values()
        n_bug += s["bugs"]; hit += len(s["hit"]); nf += s["findings"]
        adj += s["bugs"] if (s["hit"] or any(x.get("verdict") == "gt_same" for x in v)) else 0
        matched += sum(1 for f in rec["findings"] if sr.score(truth, [f])["hit"])
        real += sum(1 for x in v if x.get("verdict") in ("real", "gt_same"))
        cost += rec["cost"]; sec += rec["seconds"]; vcost += rec.get("verify_cost", 0)
    r = lambda a, b: round(a / b, 3) if b else None
    return dict(arm=arm, cases=k, bugs=n_bug, findings=nf, recall_strict=r(hit, n_bug), recall_adjudicated=r(adj, n_bug),
                precision_strict=r(matched, nf), precision_verified=r(matched + real, nf), cost_usd=round(cost, 3),
                verify_cost_usd=round(vcost, 3), seconds=round(sec, 1))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("split", "run", "verify", "report"))
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--corpus", type=Path); ap.add_argument("--out", type=Path); ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--split", default="test"); ap.add_argument("--skill", type=Path); ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    if a.cmd == "split":
        print(json.dumps(split_ids(a.ids), indent=1)); return 0
    ids = cases(a.corpus, a.split)
    if a.cmd == "report":
        print(json.dumps([metrics(a.corpus, ids, arm, a.out) for arm in ARMS if (a.out / arm).is_dir()], indent=1)); return 0
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        fn = (lambda c: run_case(a.corpus, c, a.arm, a.out, a.skill)) if a.cmd == "run" else (lambda c: verify_case(a.corpus, c, a.arm, a.out))
        for r in ex.map(fn, ids):
            print(*r, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
