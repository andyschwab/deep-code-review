#!/usr/bin/env python3
"""learning_to_pr.py — turn one downstream field lesson into a LOCAL upstream-PR draft (patch + body). Never pushes or files.

  learning_to_pr.py (--text T | --file F) [--title T] [--target REL] [--skills DIR] [--out DIR]

Opt-in primitive, run by hand or by an agent after a lesson is recorded; it is not called automatically.
Pipeline, fail closed:
 1. policy: `share_learnings=off` exits 0 doing nothing (same switch as share_learning.py).
 2. privacy: prefile_check.sh runs on the RAW title and lesson. Any hit refuses (exit 1) and nothing is written;
    a missing banlist refuses (exit 2). The lesson is not auto-redacted: the author rewrites it generically.
 3. dedupe: the lesson is compared (share_learning.similar: ratio >= 0.8 or token overlap >= 0.6) with every
    line and paragraph of every `SKILL.md` and `references/*.md` under --skills; a near-duplicate exits 0 as
    `duplicate`, drafting nothing.
 4. draft: writes `<out>/<slug>/change.patch` (a `git apply`-able diff appending one bullet to --target,
    default the deep-code-review field-lessons reference) and `<out>/<slug>/body.md` (the PR body, provenance
    footer, no target path). A human reviews, applies in an upstream checkout, runs its gates and opens the PR.
Every outcome is appended to the share_learning ledger (`$PERUN_LEDGER`, default `.perun/shared-learnings.jsonl`),
status `pr-drafted`, `duplicate` or `refused`; the raw lesson is never logged. Side effects: files under --out and
one ledger line. Exit: 0 drafted/duplicate/off, 1 privacy refusal, 2 usage or fail-closed error.
Edge cases: empty lesson -> 2; multi-line lesson is collapsed to one bullet; target absent -> patch creates it.
"""
import argparse
import difflib
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import share_learning as sl  # noqa: E402  reuse: similar, log, perun_version, SELF_REPO

DEFAULT_TARGET = ".claude/skills/deep-code-review/references/field-lessons.md"


def find_duplicate(rule: str, skills: Path) -> str:
    """Return 'file:line' of the first near-duplicate of rule in SKILL.md / references/*.md, else ''."""
    files = sorted(skills.glob("*/SKILL.md")) + sorted(skills.glob("*/references/*.md"))
    for f in files:
        text = f.read_text(errors="replace")
        for ln, line in enumerate(text.splitlines(), 1):
            if len(line.split()) >= 4 and sl.similar(rule, line.lstrip("-*0123456789. ")):
                return f"{f.relative_to(skills)}:{ln}"
        for para in re.split(r"\n\s*\n", text):
            if len(para.split()) >= 4 and sl.similar(rule, " ".join(para.split())):
                return f"{f.relative_to(skills)}:paragraph"
    return ""


def make_patch(target: str, old: str | None, rule: str) -> str:
    base = old if old is not None else "# Field lessons\n\n"
    new = base + ("" if base.endswith("\n") else "\n") + f"- {rule}\n"
    return "".join(difflib.unified_diff(
        base.splitlines(True) if old is not None else [], new.splitlines(True),
        fromfile=f"a/{target}" if old is not None else "/dev/null", tofile=f"b/{target}"))


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text")
    src.add_argument("--file")
    ap.add_argument("--title")
    ap.add_argument("--target", default=DEFAULT_TARGET, help="upstream-relative file the bullet is appended to")
    ap.add_argument("--skills", default=".claude/skills", help="installed skills dir to dedupe against")
    ap.add_argument("--out", default=".perun/upstream-drafts")
    a = ap.parse_args(argv)
    try:
        import perun_policy  # sibling skill; absent -> default, not off
        mode = perun_policy.load()["share_learnings"]
    except ImportError:
        mode = "ask"
    except ValueError as e:
        print(f"learning_to_pr: {e}", file=sys.stderr)
        return 2
    if mode == "off":
        print("learning_to_pr: policy share_learnings=off; nothing drafted")
        return 0
    raw = a.text if a.text is not None else Path(a.file).read_text()
    rule = " ".join(raw.split())
    title = " ".join((a.title or rule[:70]).split())
    if not rule or os.path.isabs(a.target) or ".." in Path(a.target).parts:
        print("learning_to_pr: empty lesson or unsafe --target", file=sys.stderr)
        return 2
    ledger = Path(os.environ.get("PERUN_LEDGER", ".perun/shared-learnings.jsonl"))
    root = Path(os.environ.get("BANLIST_DIR") or subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    with tempfile.TemporaryDirectory() as d:
        Path(d, "t").write_text(title)
        Path(d, "b").write_text(rule)
        pc = subprocess.run(["bash", str(HERE / "prefile_check.sh"), f"{d}/t", f"{d}/b"],
                            capture_output=True, text=True, env={**os.environ, "BANLIST_DIR": str(root)})
    if pc.returncode != 0:
        print(pc.stderr.strip(), file=sys.stderr)
        print("learning_to_pr: refused; rewrite the lesson generically, nothing written", file=sys.stderr)
        sl.log(ledger, "refused", sl.SELF_REPO, "", "", rule)
        return 1 if pc.returncode == 1 else 2
    dup = find_duplicate(rule, Path(a.skills))
    if dup:
        print(f"learning_to_pr: near-duplicate of existing doctrine at {dup}; no draft")
        sl.log(ledger, "duplicate", sl.SELF_REPO, title, dup, rule)
        return 0
    tgt = root / a.target
    patch = make_patch(a.target, tgt.read_text() if tgt.is_file() else None, rule)
    slug = hashlib.sha256(rule.encode()).hexdigest()[:10]
    out = Path(a.out) / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "change.patch").write_text(patch)
    (out / "body.md").write_text(
        f"{title}\n\n## Lesson\n\n{rule}\n\n## Change\n\nAppends this lesson as one bullet; see the patch file "
        f"beside this body. Not yet applied, pushed or filed.\n\n## Before filing\n\nA human applies the patch in "
        f"an upstream checkout, adds an eval or script that fails without it, runs that repo's gates, then opens "
        f"the PR.\n\n_Provenance: Perun {sl.perun_version()}, drafted by learning_to_pr.py._\n")
    sl.log(ledger, "pr-drafted", sl.SELF_REPO, title, str(out), rule)
    print(f"learning_to_pr: draft written to {out} (change.patch, body.md); not pushed or filed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
