#!/usr/bin/env python3
"""Evil-twin bench R2: harder planted flaws, controls with minor fixable issues, a precise kill definition. Free PCSS, preregistered.

R1 (docs/bench/evil-twin-r1-1021) was INCONCLUSIVE: the no-skill arm caught 24/24 flaws. R2 keeps R1's arms, models, prompts and bootstrap
(imported from scripts/evil_twin_bench.py) and changes the corpus (36 fresh cases: 24 subtle flawed, 12 controls with 1-2 minor issues),
the judge rubric (KILLED = abandon or reject only; revise is not a kill) and the verdict() rule. A separate 8-case calibration set, tuned
until the no-skill arm sat at or below 0.70 recall, is never scored in R2. Rules: docs/bench/evil-twin-r2-1021/PREREGISTERED.md.

  evil_twin_bench_r2.py [--cache-only] [--write] [--jobs N]            score the R2 corpus (cache under the R2 dir)
  evil_twin_bench_r2.py --calibrate [--cache-only]                     no-skill arm only on calibration/cases.txt (cache under calibration/)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evil_twin_bench as E  # noqa: E402  (parse_cases, cached, mean, boot, prompts, ARMS, models)

ROOT = E.ROOT
D1, D = ROOT / "docs/bench/evil-twin-r1-1021", ROOT / "docs/bench/evil-twin-r2-1021"
ARMS = E.ARMS
MIN_NONE_HEADROOM = 0.85  # preregistered: no-skill recall at or above this -> INCONCLUSIVE
MAX_UNPARSED = 2  # preregistered
FK_MARGIN = 1 / 12  # preregistered: one control of twelve
_FLAW, _KILL, _BLOCK = (re.compile(rf"{k}:\s*([01])") for k in ("FLAW_CAUGHT", "KILLED", "BLOCKED"))


def arm_text(arm):
    """Guidance for an arm: '' for none, the R1 frozen snapshots (same bytes as R1) otherwise."""
    f = {"none": None, "perun": "skill-arm.txt", "brainstorm": "brainstorm-arm.txt"}[arm]
    return (D1 / f).read_text() if f else ""


def system(arm):
    t = arm_text(arm)
    return E.BASE + (f"\n\nFollow this guidance:\n\n{t}" if t else "")


def judge_prompt(c, response):
    return (f"Proposal:\n{c['proposal']}\n\nHidden answer key (the planted fatal flaw, or 'none ...' for a sound proposal with only minor issues):\n"
            f"{c['key']}\n\nReviewer response:\n{response}\n\nGrade three things.\n"
            "FLAW_CAUGHT = 1 only if the response specifically identifies the flaw in the answer key (the same underlying problem, reached by "
            "the same inference, not just a generic risk or a minor issue) AND treats it as serious: something that must be fixed or resolved "
            "before the proposal can proceed. A passing mention among minor caveats, or a different problem, is 0. For a sound proposal (key "
            "starts with 'none') always 0.\n"
            "KILLED = 1 only if the response's final recommendation is to abandon, reject or cancel the proposal: drop the idea, do not do it "
            "at all, or revising it is not worthwhile. KILLED = 0 for everything else, including: proceed, proceed with changes, conditional "
            "approval, 'fix X and resubmit', 'hold until Y is resolved', 'do not approve yet', 'revise', or a request for more information. "
            "Asking for revision is NOT a kill.\n"
            "BLOCKED = 1 if the response does not approve the proposal as written (it asks for any required change, hold or rejection); "
            "0 if it approves as written or with only optional suggestions.\n\n"
            "Answer in exactly this form:\nREASON: <one or two sentences>\nFLAW_CAUGHT: <0 or 1>\nKILLED: <0 or 1>\nBLOCKED: <0 or 1>")


def parse_judge(text):
    """Last FLAW_CAUGHT / KILLED / BLOCKED -> (caught, killed, blocked) ints, or None if any is missing."""
    v = [p.findall(text) for p in (_FLAW, _KILL, _BLOCK)]
    return tuple(int(x[-1]) for x in v) if all(v) else None


def run_one(arm, c, cache_only):
    resp = E.cached("gen", E.GEN_MODEL, system(arm), E.user_prompt(c), cache_only, 2500)
    j = E.cached("judge", E.JUDGE_MODEL, E.JUDGE_SYSTEM, judge_prompt(c, resp), cache_only, 800)
    p = parse_judge(j)
    return {"id": c["id"], "kind": c["kind"], "arm": arm, "caught": p and p[0], "killed": p and p[1], "blocked": p and p[2]}


def build_results(rows_by_arm):
    """Per-arm recall, false-kill, blocked-control rate (descriptive), CIs, unparsed counts, paired recall contrasts, verdict."""
    out = {"model": E.GEN_MODEL, "judge": E.JUDGE_MODEL, "arms": {}, "contrasts": {}}
    for a, rs in rows_by_arm.items():
        one = {a: rs}
        out["arms"][a] = {
            "recall": E.mean(rs, "caught", "flawed"), "recall_ci": E.boot(one, lambda x: E.mean(x[a], "caught", "flawed")),
            "false_kill": E.mean(rs, "killed", "control"), "false_kill_ci": E.boot(one, lambda x: E.mean(x[a], "killed", "control")),
            "control_blocked": E.mean(rs, "blocked", "control"), "kill_on_flawed": E.mean(rs, "killed", "flawed"),
            "unparsed": sum(1 for r in rs if r["caught"] is None)}
    for x, y in (("perun", "none"), ("perun", "brainstorm"), ("brainstorm", "none")):
        d = lambda r: E.mean(r[x], "caught", "flawed") - E.mean(r[y], "caught", "flawed")  # noqa: E731
        lo, hi = E.boot({x: rows_by_arm[x], y: rows_by_arm[y]}, d)
        out["contrasts"][f"{x}-{y}"] = {"diff": d(rows_by_arm), "lo": lo, "hi": hi}
    out["verdict"] = verdict(out["arms"], out["contrasts"])
    return out


def verdict(arms, contrasts):
    """Preregistered verdict. INVALID: any arm has > MAX_UNPARSED unparsed judge outputs. INCONCLUSIVE: none recall >= MIN_NONE_HEADROOM.
    Keep rule: perun recall CI lower bound > none recall point AND perun false-kill <= none false-kill + FK_MARGIN (one control).
    WIN iff keep rule and the paired perun-brainstorm recall CI lower bound > 0; TIE iff keep rule only; else REVERT."""
    p, n = arms["perun"], arms["none"]
    if any(a["unparsed"] > MAX_UNPARSED for a in arms.values()):
        return "INVALID"
    if n["recall"] >= MIN_NONE_HEADROOM:
        return "INCONCLUSIVE"
    if p["recall_ci"][0] > n["recall"] and p["false_kill"] <= n["false_kill"] + FK_MARGIN + 1e-9:
        return "WIN" if contrasts["perun-brainstorm"]["lo"] > 0 else "TIE"
    return "REVERT"


def evaluate(cache_only=False, jobs=4, cases_file=None, cache=None, arms=ARMS):
    E.CACHE = cache or D / "cache"  # E.cached reads this module global
    cases = E.parse_cases((cases_file or D / "cases.txt").read_text())
    with cf.ThreadPoolExecutor(jobs) as ex:
        return {a: list(ex.map(lambda c, a=a: run_one(a, c, cache_only), cases)) for a in arms}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-only", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    if a.calibrate:
        rows = evaluate(a.cache_only, a.jobs, D / "calibration/cases.txt", D / "calibration/cache", ("none",))["none"]
        print("calibration none recall", E.mean(rows, "caught", "flawed"), "unparsed", sum(r["caught"] is None for r in rows),
              [(r["id"], r["caught"]) for r in rows])
        return
    rows = evaluate(a.cache_only, a.jobs)
    res = build_results(rows)
    for arm, s in res["arms"].items():
        print(f"{arm:11s} recall {s['recall']:.3f} {tuple(round(x, 3) for x in s['recall_ci'])}  false-kill {s['false_kill']:.3f} "
              f"{tuple(round(x, 3) for x in s['false_kill_ci'])}  control-blocked {s['control_blocked']:.3f}  kill-on-flawed "
              f"{s['kill_on_flawed']:.3f}  unparsed {s['unparsed']}")
    for k, c in res["contrasts"].items():
        print(f"{k}: {c['diff']:+.3f} [{c['lo']:+.3f}, {c['hi']:+.3f}]")
    print("verdict", res["verdict"])
    if a.write:
        text = json.dumps({"results": res, "rows": rows}, indent=1)
        (D / "results.json").write_text(text)
        cols = [f"{x}_{f}" for x in ARMS for f in ("caught", "killed", "blocked")]
        (D / "per-case-scores.tsv").write_text("case\tkind\t" + "\t".join(cols) + "\n" + "\n".join(
            f"{rows['none'][i]['id']}\t{rows['none'][i]['kind']}\t"
            + "\t".join(str(rows[x][i][f]) for x in ARMS for f in ("caught", "killed", "blocked")) for i in range(len(rows["none"]))) + "\n")
        now = int(time.time())
        with (D / "ledger.jsonl").open("a") as f:
            f.write(json.dumps({"ts": now, "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "event": "result", "model": E.GEN_MODEL,
                                "file": "results.json", "sha256": hashlib.sha256(text.encode()).hexdigest()}) + "\n")


if __name__ == "__main__":
    main()
