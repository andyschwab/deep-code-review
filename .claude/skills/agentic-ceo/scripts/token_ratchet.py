#!/usr/bin/env python3
"""token_ratchet.py -- tokens per delivered PR, ratcheted against a baseline file.

Reads every Claude Code session transcript (*.jsonl, subagent transcripts included, found
recursively) under --dir, sums the logged usage via token_report.py (input-equivalent cache
weighting plus output tokens) for turns at/after --since, and divides by the number of
delivered PRs in the same window. PR count is --prs N, else the count of "Merge pull request"
commits in the current git repo since --since.

  token_ratchet.py --dir DIR --baseline FILE --write-baseline   # record the baseline
  token_ratchet.py --dir DIR --baseline FILE [--max-rise-pct 20] [--warn]

Exit 0 ok (or rise but --warn: prints WARN), 1 tokens/PR rose more than --max-rise-pct over the
baseline, 2 usage/unreadable input. Zero PRs or a missing/zero baseline is reported, never
guessed: both exit 2 so an idle window cannot pass as a win. Read-only except the baseline
file. Figures are logged-usage proxies, not a bill (see token_report.py honesty note).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_report as tr  # noqa: E402


def measure(root, since):
    """Return (weighted_tokens, session_files) for all transcripts under root at/after since."""
    total, files = 0.0, 0
    for dirpath, _, names in os.walk(root):
        for n in sorted(names):
            if not n.endswith(".jsonl"):
                continue
            turns = tr.filter_since(tr.extract_turns(list(tr.read_jsonl(os.path.join(dirpath, n)))), since)
            t = tr.sum_turns(turns)
            total += t["input_equivalent"] + t["output_tokens"]
            files += 1
    return total, files


def git_pr_count(since):
    """Merged-PR count in the cwd repo since `since`; None if git fails."""
    out = subprocess.run(["git", "log", "--merges", "--grep=^Merge pull request",
                          f"--since={since.isoformat()}", "--format=%h"],
                         capture_output=True, text=True)
    return len(out.stdout.split()) if out.returncode == 0 else None


def ratchet(per_pr, baseline, max_rise_pct):
    """Return (rise_pct, breached). baseline<=0 raises ValueError (cannot ratchet on nothing)."""
    if baseline <= 0:
        raise ValueError("baseline tokens_per_pr must be > 0")
    rise = (per_pr - baseline) / baseline * 100
    return rise, rise > max_rise_pct


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", required=True, help="directory of session JSONL transcripts")
    ap.add_argument("--baseline", required=True, help="baseline JSON file")
    ap.add_argument("--since", help="ISO-8601 window start (default: 7 days ago)")
    ap.add_argument("--prs", type=int, help="delivered PRs in the window (default: git merge count)")
    ap.add_argument("--max-rise-pct", type=float, default=20.0)
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--warn", action="store_true", help="report a breach but exit 0")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.dir):
        print(f"token_ratchet: not a directory: {a.dir}", file=sys.stderr)
        return 2
    since = tr.parse_timestamp(a.since) if a.since else datetime.now(timezone.utc) - timedelta(days=7)
    if since is None:
        print(f"token_ratchet: bad --since: {a.since}", file=sys.stderr)
        return 2
    prs = a.prs if a.prs is not None else git_pr_count(since)
    if not prs or prs < 0:
        print("token_ratchet: COULD_NOT_CHECK: zero or unknown delivered PRs in window", file=sys.stderr)
        return 2
    tokens, files = measure(a.dir, since)
    per_pr = tokens / prs
    cur = {"tokens_per_pr": round(per_pr, 2), "prs": prs, "weighted_tokens": round(tokens, 2),
           "sessions": files, "since": since.isoformat()}
    if a.write_baseline:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(a.baseline)), suffix=".tmp")
        with os.fdopen(fd, "w") as fh:
            json.dump(cur, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, a.baseline)  # atomic: a crash never leaves a half-written baseline
        print(f"baseline written: {cur['tokens_per_pr']} tokens/PR over {prs} PRs")
        return 0
    try:
        with open(a.baseline, encoding="utf-8") as fh:
            base = float(json.load(fh)["tokens_per_pr"])
        rise, breached = ratchet(per_pr, base, a.max_rise_pct)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"token_ratchet: COULD_NOT_CHECK: baseline unusable ({e})", file=sys.stderr)
        return 2
    print(f"tokens/PR {cur['tokens_per_pr']} vs baseline {base} ({rise:+.1f}%, limit +{a.max_rise_pct:g}%)")
    if breached:
        print(("WARN" if a.warn else "FAIL") + ": tokens per delivered PR rose past the limit")
        return 0 if a.warn else 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
