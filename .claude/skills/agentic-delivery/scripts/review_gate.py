#!/usr/bin/env python3
"""review_gate.py — pre-merge gate: every PR needs an independent deep-code-review DIFF pass plus an evil-twin check.

  review_gate.py check <pr> [--head SHA] [--repo R]   exit 0 ok / off / warn-only; exit 1 only in enforce mode
  review_gate.py receipt <pr> --reviewer R --author A --head SHA   write the receipt file

Evidence, either of:
  1. receipt file `$REVIEW_DIR/<pr>.json` (default `.perun/reviews/`) with reviewer, author, head, diff_pass and
     evil_twin all set; written by `receipt` after the reviewer agent finishes both passes.
  2. a PR comment holding `<!-- perun-review reviewer=R author=A head=SHA diff=pass evil-twin=pass -->`.
The reviewer must be non-empty and differ (case-insensitive) from the author (and from the GitHub PR author when
the comment path is used), and `head` must match the PR head being merged (prefix match, 7+ chars), so a review
of an older push never covers a newer one. This is an honest-process receipt, not a forgery-proof signature.

Policy `review_gate` (`.perun/policy.json`): `warn` (default, this release: prints WARN, never blocks),
`enforce` (a PR with no evidence exits 1), `off` (opt out; silent). A malformed policy or a failing `gh` is
treated as no evidence, never a crash. Side effects: `receipt` writes one file; `check` runs `gh pr view` only
when no valid receipt exists. Env: GH (default gh), REVIEW_DIR.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perun_policy  # noqa: E402

MARKER = re.compile(r"<!--\s*perun-review\s+reviewer=(\S+)\s+author=(\S+)\s+head=([0-9a-f]{7,40})\s+diff=pass\s+evil-twin=pass\s*-->")


def _same_head(a: str, b: str) -> bool:
    return bool(a) and bool(b) and len(a) >= 7 and len(b) >= 7 and (a.startswith(b) or b.startswith(a))


def valid(reviewer: str, author: str, head: str, want_head: str, gh_author: str = "") -> bool:
    """Independent (reviewer != author, != GitHub PR author) and covering the head being merged."""
    r = (reviewer or "").strip().lower()
    return bool(r) and r != (author or "").strip().lower() and r != gh_author.lower() \
        and (not want_head or _same_head(head, want_head))


def has_evidence(pr: str, head: str = "", repo: str = "", review_dir: Path | None = None) -> bool:
    d = review_dir or Path(os.environ.get("REVIEW_DIR", ".perun/reviews"))
    try:
        r = json.loads((d / f"{pr}.json").read_text())
        if r.get("diff_pass") is True and r.get("evil_twin") is True and valid(
                str(r.get("reviewer", "")), str(r.get("author", "")), str(r.get("head", "")), head):
            return True
    except (OSError, ValueError, AttributeError):
        pass
    cmd = [os.environ.get("GH", "gh"), "pr", "view", pr, "--json", "author,comments"] + (["--repo", repo] if repo else [])
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        data = json.loads(out.stdout) if out.returncode == 0 else {}
        gh_author = ((data.get("author") or {}).get("login")) or ""
        return any(valid(m[0], m[1], m[2], head, gh_author)
                   for c in data.get("comments") or [] for m in MARKER.findall(c.get("body") or ""))
    except (OSError, ValueError, subprocess.SubprocessError, AttributeError):
        return False


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(prog="review_gate.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("pr")
    c.add_argument("--head", default="")
    c.add_argument("--repo", default="")
    r = sub.add_parser("receipt")
    r.add_argument("pr")
    r.add_argument("--reviewer", required=True)
    r.add_argument("--author", required=True)
    r.add_argument("--head", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "receipt":
        if not valid(a.reviewer, a.author, a.head, a.head):
            print("review_gate: reviewer must be non-empty and differ from the author", file=sys.stderr)
            return 2
        d = Path(os.environ.get("REVIEW_DIR", ".perun/reviews"))
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{a.pr}.json").write_text(json.dumps(
            {"pr": a.pr, "reviewer": a.reviewer, "author": a.author, "head": a.head, "diff_pass": True, "evil_twin": True}) + "\n")
        return 0
    try:
        mode = perun_policy.load()["review_gate"]
    except ValueError:
        mode = "warn"
    if mode == "off" or has_evidence(a.pr, a.head, a.repo):
        return 0
    msg = (f"#{a.pr} has no independent deep-code-review DIFF pass + evil-twin receipt "
           f"(.perun/reviews/{a.pr}.json or a perun-review PR comment from a non-author reviewer)")
    if mode == "enforce":
        print(f"REVIEW GATE: {msg}; not merged", file=sys.stderr)
        return 1
    print(f"WARN review_gate: {msg}; warn-only this release, review_gate=enforce blocks, review_gate=off opts out", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
