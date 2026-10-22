#!/usr/bin/env python3
"""Offline counter: bytes of skill text a deep-code-review run is *instructed* to load for a commit's diff.

usage: review_load_bytes.py [--skill-rev REV] COMMIT...   (default skill = working tree)

Routing mirrors SKILL.md: a diff of <=300 changed lines takes the DIFF quick-path (SKILL.md + compact-mode.md); a larger diff takes the full DIFF method (SKILL.md + method.md). INDEX.md is added
to either only when SKILL.md lacks the matching skip marker (a pre-skip SKILL.md, e.g. under --skill-rev). Blast-radius flags are NOT detected: a flagged small diff would take the full path.
"real_*" (full route only) = bytes of REAL_FULL, the files one observed full-DIFF run actually opened, so routing-only duplicates in them show up as bytes.
Tokens are chars/4, the repo's own estimate (skill-authoring-and-size.md). A model of the instructed load set,
not a transcript measurement: an agent may read less (or more) than it is told to.
Side effects: none (read-only git). Exit 1 on an unreadable commit or skill file."""
import json
import subprocess
import sys

SKILL = ".claude/skills/deep-code-review"
QUICK_MAX = 300
EXEMPT = "never opens it"  # marker the SKILL.md sentence exempting the quick-path from INDEX.md carries
SKIP = "a match skips `INDEX.md`"  # marker: SKILL.md routes by its own tables, so the full method skips INDEX.md too

# Refs an observed full-DIFF run opened (INDEX.md excluded: a routing match skips it). Update when routing changes.
REAL_FULL = ["SKILL.md"] + [f"references/{n}.md" for n in (
    "method", "branch-and-merge-hygiene", "method-situational", "domain-checklists", "domain-j", "testing-and-evals",
    "language-stack-redflags", "lang-python", "method-report", "report-format", "example-review-report", "security-appsec")]


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def lines_changed(commit):
    n = 0
    for row in git("show", "--format=", "--numstat", commit).splitlines():
        a, d, _ = row.split("\t", 2)
        n += (int(a) if a != "-" else 0) + (int(d) if d != "-" else 0)
    return n


def load_set(skill_text, lines):
    if lines <= QUICK_MAX:
        return "quick", ["SKILL.md", "references/compact-mode.md"] + ([] if EXEMPT in skill_text else ["INDEX.md"])
    return "full", ["SKILL.md"] + ([] if SKIP in skill_text else ["INDEX.md"]) + ["references/method.md"]


def measure(commit, skill_rev=None):
    read = (lambda f: git("show", f"{skill_rev}:{SKILL}/{f}")) if skill_rev else (lambda f: open(f"{SKILL}/{f}", encoding="utf-8").read())
    n = lines_changed(commit)
    route, files = load_set(read("SKILL.md"), n)
    b = sum(len(read(f).encode()) for f in files)
    out = {"commit": commit, "lines": n, "route": route, "files": files, "bytes": b, "tokens_est": b // 4}
    if route == "full":
        rb = sum(len(read(f).encode()) for f in REAL_FULL)
        out.update(real_bytes=rb, real_tokens_est=rb // 4)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    rev = None
    if args[:1] == ["--skill-rev"]:
        rev, args = args[1], args[2:]
    if not args:
        sys.exit(__doc__)
    try:
        print(json.dumps([measure(c, rev) for c in args], indent=1))
    except (subprocess.CalledProcessError, OSError) as e:
        sys.exit(f"review_load_bytes: {e}")
