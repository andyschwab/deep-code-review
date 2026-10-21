#!/usr/bin/env python3
"""Free evil-twin bench: does the idea-critic skill catch a planted fatal flaw in a proposal, and does it falsely kill a sound one?

30 fictional proposals (docs/bench/evil-twin-r1-1021/cases.txt): 24 each hide one fatal flaw with a hidden answer key, 6 are sound controls.
Three arms answer the same prompt: none (no skill), perun (the idea-critic SKILL.md snapshot as guidance), brainstorm (a generic
pros/cons-then-recommend prompt written for this bench). A different model than the generator judges each response blind to the arm,
scoring FLAW_CAUGHT (0/1, flawed cases) and KILLED (0/1, the response recommends rejecting or holding the proposal).
Recall = mean FLAW_CAUGHT over flawed cases; false-kill = mean KILLED over controls. Intervals: case-level percentile bootstrap.
Verdict rule: verdict() below, preregistered in docs/bench/evil-twin-r1-1021/PREREGISTERED.md. Free PCSS endpoint, public fictional data only.

  evil_twin_bench.py [--cache-only] [--write] [--jobs N]   generate+judge (cached under the bench dir), score, print; --write saves
                                                           results.json, per-case-scores.tsv and a ledger line
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rival_eval as RE  # noqa: E402  (chat, load_key)

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "docs/bench/evil-twin-r1-1021"
CACHE = D / "cache"
ARMS = ("none", "perun", "brainstorm")
GEN_MODEL, JUDGE_MODEL = "Qwen3.5-397B-A17B", "GLM-5.1"  # preregistered; the judge differs from the generator
BASE = "You are a senior advisor. A decision maker is about to approve a proposal and asks for your review."
ASK = "Review the proposal below and tell the decision maker what to do with it. Keep it under 400 words."
MIN_NONE_HEADROOM = 0.90  # preregistered: a no-skill recall at or above this cannot show a gain -> INCONCLUSIVE
MAX_UNPARSED = 2  # preregistered: more unparsed judge outputs in any arm -> INVALID
FK_MARGIN = 1 / 6  # preregistered: one control of six
JUDGE_SYSTEM = ("You are a strict, impartial grader of proposal reviews. You see a proposal, a hidden answer key and one reviewer's response. "
                "You do not know how the reviewer was prompted. Grade only what the response says.")
_FLAW, _KILL = re.compile(r"FLAW_CAUGHT:\s*([01])"), re.compile(r"KILLED:\s*([01])")


def parse_cases(text):
    """Parse cases.txt -> [{id, kind: flawed|control, proposal, key}]. Raises ValueError on a bad block, kind or duplicate id."""
    cases = []
    for blk in re.split(r"^=== ", text, flags=re.M)[1:]:
        head, _, rest = blk.partition("\n")
        cid, kind = [x.strip() for x in head.split("|")]
        m = re.match(r"PROPOSAL: (.*)\nKEY: (.*)\s*$", rest, re.S)
        if not m or kind not in ("flawed", "control"):
            raise ValueError(f"case {cid}: malformed block")
        cases.append({"id": cid, "kind": kind, "proposal": m.group(1).strip(), "key": m.group(2).strip()})
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("duplicate case id")
    return cases


def arm_text(arm):
    """Guidance text for an arm: '' for none, the frozen snapshots in D otherwise."""
    f = {"none": None, "perun": "skill-arm.txt", "brainstorm": "brainstorm-arm.txt"}[arm]
    return (D / f).read_text() if f else ""


def system(arm):
    t = arm_text(arm)
    return BASE + (f"\n\nFollow this guidance:\n\n{t}" if t else "")


def user_prompt(c):
    return f"{ASK}\n\nProposal:\n{c['proposal']}"


def judge_prompt(c, response):
    return (f"Proposal:\n{c['proposal']}\n\nHidden answer key (the planted fatal flaw, or 'none' for a sound proposal):\n{c['key']}\n\n"
            f"Reviewer response:\n{response}\n\nGrade two things.\n"
            "FLAW_CAUGHT = 1 only if the response specifically identifies the flaw in the answer key (the same underlying problem, not just a "
            "generic risk) AND treats it as serious enough to block or force a change to the proposal. A passing mention among minor caveats, "
            "or a different flaw, is 0. For a sound proposal (key 'none') always 0.\n"
            "KILLED = 1 if the response's overall recommendation is to reject, hold, not proceed, or send the proposal back as unfit. "
            "Recommending to proceed, or to proceed with adjustments or conditions, is 0.\n\n"
            "Answer in exactly this form:\nREASON: <one or two sentences>\nFLAW_CAUGHT: <0 or 1>\nKILLED: <0 or 1>")


def parse_judge(text):
    """Last FLAW_CAUGHT / KILLED values -> (caught, killed) as ints, or None if either is missing."""
    f, k = _FLAW.findall(text), _KILL.findall(text)
    return (int(f[-1]), int(k[-1])) if f and k else None


def cached(kind, model, sys_p, usr, cache_only, max_tokens):
    """Cached completion. Key covers model, system and user prompt. With cache_only a miss raises instead of calling the network."""
    key = hashlib.sha256(f"{model}\0{sys_p}\0{usr}".encode()).hexdigest()[:20]
    f = CACHE / kind / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())["text"]
    if cache_only:
        raise RuntimeError(f"cache miss: {kind}/{key}")
    t = RE.chat(model, sys_p, usr, max_tokens=max_tokens)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"model": model, "text": t}))
    return t


def run_one(arm, c, cache_only):
    resp = cached("gen", GEN_MODEL, system(arm), user_prompt(c), cache_only, 2500)
    j = cached("judge", JUDGE_MODEL, JUDGE_SYSTEM, judge_prompt(c, resp), cache_only, 800)
    p = parse_judge(j)
    return {"id": c["id"], "kind": c["kind"], "arm": arm, "caught": p[0] if p else None, "killed": p[1] if p else None}


def mean(rows, field, kind):
    xs = [r[field] or 0 for r in rows if r["kind"] == kind]  # unparsed counts as 0 for every arm
    return sum(xs) / len(xs)


def boot(rows_by_arm, fn, n=10000, seed=1):
    """Percentile bootstrap (resample case positions within flawed and within control) of fn(resampled rows_by_arm) -> (lo, hi).
    rows_by_arm[arm] lists rows in the same case order, so every arm shares each resample (paired)."""
    rng = random.Random(seed)
    kinds = {k: [i for i, r in enumerate(next(iter(rows_by_arm.values()))) if r["kind"] == k] for k in ("flawed", "control")}
    vals = []
    for _ in range(n):
        ix = [rng.choice(kinds[k]) for k in ("flawed", "control") for _ in kinds[k]]
        vals.append(fn({a: [rs[i] for i in ix] for a, rs in rows_by_arm.items()}))
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def build_results(rows_by_arm):
    """Per-arm recall / false-kill with CIs, unparsed counts and paired recall contrasts -> the results dict."""
    out = {"model": GEN_MODEL, "judge": JUDGE_MODEL, "arms": {}, "contrasts": {}}
    for a, rs in rows_by_arm.items():
        one = {a: rs}
        out["arms"][a] = {
            "recall": mean(rs, "caught", "flawed"), "recall_ci": boot(one, lambda x: mean(x[a], "caught", "flawed")),
            "false_kill": mean(rs, "killed", "control"), "false_kill_ci": boot(one, lambda x: mean(x[a], "killed", "control")),
            "kill_on_flawed": mean(rs, "killed", "flawed"),
            "unparsed": sum(1 for r in rs if r["caught"] is None)}
    for x, y in (("perun", "none"), ("perun", "brainstorm"), ("brainstorm", "none")):
        d = lambda r: mean(r[x], "caught", "flawed") - mean(r[y], "caught", "flawed")  # noqa: E731
        lo, hi = boot({x: rows_by_arm[x], y: rows_by_arm[y]}, d)
        out["contrasts"][f"{x}-{y}"] = {"diff": d(rows_by_arm), "lo": lo, "hi": hi}
    out["verdict"] = verdict(out["arms"], out["contrasts"])
    return out


def verdict(arms, contrasts):
    """Preregistered verdict. INVALID if any arm has > MAX_UNPARSED unparsed judge outputs; INCONCLUSIVE if none-arm recall >= MIN_NONE_HEADROOM.
    Primary: lower bound of perun's recall CI > none's recall point. Guard: perun false-kill <= none's and brainstorm's + FK_MARGIN.
    WIN iff primary and guard and the paired perun-brainstorm recall CI lower bound > 0; TIE iff primary and guard but not that; else REVERT."""
    p, n, b = arms["perun"], arms["none"], arms["brainstorm"]
    if any(a["unparsed"] > MAX_UNPARSED for a in arms.values()):
        return "INVALID"
    if n["recall"] >= MIN_NONE_HEADROOM:
        return "INCONCLUSIVE"
    primary = p["recall_ci"][0] > n["recall"]
    guard = p["false_kill"] <= n["false_kill"] + FK_MARGIN + 1e-9 and p["false_kill"] <= b["false_kill"] + FK_MARGIN + 1e-9
    if primary and guard:
        return "WIN" if contrasts["perun-brainstorm"]["lo"] > 0 else "TIE"
    return "REVERT"


def evaluate(cache_only=False, jobs=4):
    cases = parse_cases((D / "cases.txt").read_text())
    with cf.ThreadPoolExecutor(jobs) as ex:
        rows = {a: list(ex.map(lambda c, a=a: run_one(a, c, cache_only), cases)) for a in ARMS}
    return rows, build_results(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-only", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    rows, res = evaluate(a.cache_only, a.jobs)
    for arm, s in res["arms"].items():
        print(f"{arm:11s} recall {s['recall']:.3f} {tuple(round(x, 3) for x in s['recall_ci'])}  false-kill {s['false_kill']:.3f} "
              f"{tuple(round(x, 3) for x in s['false_kill_ci'])}  kill-on-flawed {s['kill_on_flawed']:.3f}  unparsed {s['unparsed']}")
    for k, c in res["contrasts"].items():
        print(f"{k}: {c['diff']:+.3f} [{c['lo']:+.3f}, {c['hi']:+.3f}]")
    print("verdict", res["verdict"])
    if a.write:
        text = json.dumps({"results": res, "rows": rows}, indent=1)
        (D / "results.json").write_text(text)
        (D / "per-case-scores.tsv").write_text("case\tkind\t" + "\t".join(f"{x}_caught\t{x}_killed" for x in ARMS) + "\n" + "\n".join(
            f"{rows['none'][i]['id']}\t{rows['none'][i]['kind']}\t" + "\t".join(f"{rows[x][i]['caught']}\t{rows[x][i]['killed']}" for x in ARMS)
            for i in range(len(rows["none"]))) + "\n")
        now = int(time.time())
        with (D / "ledger.jsonl").open("a") as f:
            f.write(json.dumps({"ts": now, "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "event": "result", "model": GEN_MODEL,
                                "file": "results.json", "sha256": hashlib.sha256(text.encode()).hexdigest()}) + "\n")


if __name__ == "__main__":
    main()
