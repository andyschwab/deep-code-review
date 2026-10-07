#!/usr/bin/env python3
"""Weekly value receipt: a one-screen plain-English card from local git plus existing token/spend scripts.

Usage: weekly_receipt.py [--days 7] [--repo DIR] [--session JSONL] [--baseline TOKENS_PER_PR]
                         [--spend EXPORT] [--findings FILE] [--holds FILE]

Every line names its source. Anything not supplied or not readable prints "unknown", never a guess.
Opt-in primitive: nothing calls it automatically and no tool writes the --findings / --holds files
for you (one finding / hold per non-blank line). No network. Exit 0 always except bad arguments.
"""
import argparse
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = ROOT / ".claude/skills/agentic-ceo/scripts/token_report.py"
SPEND = ROOT / ".claude/skills/agentic-delivery/scripts/spend_report.py"
PR_RE = re.compile(r"^Merge pull request #(\d+)\b")


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def prs_landed(repo, days):
    """Count `Merge pull request #N` first-parent subjects in the window, or None if git fails."""
    out = _run(["git", "-C", repo, "log", "--first-parent", f"--since={days} days ago", "--format=%s"])
    return None if out is None else len({m.group(1) for s in out.splitlines() if (m := PR_RE.match(s))})


def count_lines(path):
    try:
        return sum(1 for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip())
    except (OSError, TypeError):
        return None


def session_tokens(session, days):
    """Raw tokens (main + subagents) from token_report.py --json, or None."""
    if not session:
        return None
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    out = _run([sys.executable, str(TOKEN), "--session", session, "--since", since, "--json"])
    try:
        d = json.loads(out)
        return int(d["main"]["raw_tokens"]) + int(d["subagents_totals"]["raw_tokens"])
    except (TypeError, ValueError, KeyError):
        return None


def spend_total(path):
    """Sum of spend_report.py --json totals plus count of unpriced rows, or None."""
    if not path:
        return None
    out = _run([sys.executable, str(SPEND), path, "--json"])
    try:
        d = json.loads(out)
        return sum((Decimal(v["total"]) for v in d.values()), Decimal(0)), sum(v["unpriced_rows"] for v in d.values())
    except (TypeError, ValueError, KeyError):
        return None


def card(a):
    prs = prs_landed(a.repo, a.days)
    toks = session_tokens(a.session, a.days)
    spend = spend_total(a.spend)
    findings, holds = count_lines(a.findings), count_lines(a.holds)
    u = lambda v: "unknown" if v is None else v  # noqa: E731
    if toks is None or not prs:
        per = None
    else:
        per = toks // prs
    if per is None or not a.baseline:
        vs = "unknown (needs session tokens, at least 1 PR and --baseline)"
    else:
        vs = f"{(per - a.baseline) * 100 // a.baseline:+d}% vs baseline {a.baseline:,} (ESTIMATE: one session log, not every session)"
    sp = "unknown" if spend is None else f"${spend[0]} ({spend[1]} unpriced rows excluded)"
    return "\n".join([
        f"Perun weekly receipt - last {a.days} days",
        f"PRs landed:         {u(prs)}   [source: git log --first-parent, merge subjects]",
        f"Review findings:    {u(findings)}   [source: --findings file, one per line]",
        f"Tokens per PR:      {u(per if per is None else f'{per:,}')}; {vs}   [source: token_report.py]",
        f"Spend:              {sp}   [source: spend_report.py on your export]",
        f"Heavy-job holds:    {u(holds)}   [source: --holds file, one per line]",
        "unknown = no data supplied or readable; nothing here is guessed.",
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--session")
    ap.add_argument("--baseline", type=int)
    ap.add_argument("--spend")
    ap.add_argument("--findings")
    ap.add_argument("--holds")
    print(card(ap.parse_args(argv)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
