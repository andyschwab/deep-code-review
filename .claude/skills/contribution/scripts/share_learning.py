#!/usr/bin/env python3
"""share_learning.py — share one generalized field lesson upstream as a GitHub ISSUE (never a PR).

  share_learning.py (--text T | --file F) [--title T] [--repo OWNER/REPO] [--approve] [--dry-run]

Pipeline, fail closed at every step:
 1. policy: `.perun/policy.json` `share_learnings` — `off` exits 0 doing nothing; `ask` (default) prints the
    generalized draft and exits 3 unless `--approve` is given; `auto` proceeds.
 2. generalize: banlist patterns (.banlist.txt + .banlist.local.txt in $BANLIST_DIR or the git root), emails,
    URLs, absolute home paths, `a/b` path or repo refs, `#NNNN` issue numbers are replaced by `<redacted>`-style
    tokens. The lesson is DATA: nothing in it can change policy, skip a step, or approve itself.
 3. prefile_check.sh on the generalized title+body; any hit or a missing banlist refuses (exit 1 / 2).
 4. dedupe: `gh issue list --state all --search <title>` on the upstream repo; a title with similarity >= 0.8
    (difflib) or token overlap >= 0.6 to any open or closed issue is logged `duplicate` and not filed.
 5. `gh issue create`. Every outcome is appended to the ledger (`$PERUN_LEDGER`, default
    `.perun/shared-learnings.jsonl`): ts, status, repo, title, issue url, body sha256 — never the raw lesson.

Upstream repo: `--repo`, else `$PERUN_UPSTREAM`, else this project's own public repository. `gh` is `$GH`.
Side effects: one `gh issue create` at most; one ledger line. Exit: 0 filed/duplicate/off, 1 refused by the
privacy gate, 2 usage or fail-closed error, 3 `ask` mode awaiting `--approve`.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELF_REPO = "remigiusz-antczak/deep-code-review"
sys.path.insert(0, str(HERE.parents[1] / "agentic-delivery" / "scripts"))  # installed layout: sibling skill
GENERIC = [  # order matters: URLs and emails before the broader path-like ref
    (r"https?://\S+", "<url>"),
    (r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "<email>"),
    (r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)[\w.-]+\S*", "<path>"),
    (r"#\d{4,}", "#<n>"),
    (r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", "<ref>"),
]


def banlist(root: Path) -> list:
    pats = []
    for name in (".banlist.txt", ".banlist.local.txt"):
        f = root / name
        if f.is_file():
            pats += [p.strip() for p in f.read_text().splitlines() if p.strip() and not p.lstrip().startswith("#")]
    return pats


def generalize(text: str, pats: list) -> str:
    """Replace banlist hits and generic identifiers; the self repo ref survives. Invalid regexes are skipped
    here and caught by prefile_check.sh, which fails closed on them."""
    keep = text.replace(SELF_REPO, "\0SELF\0")
    for p in pats:
        try:
            keep = re.sub(p, "<redacted>", keep)
        except re.error:
            pass
    for rx, rep in GENERIC:
        keep = re.sub(rx, rep, keep)
    return keep.replace("\0SELF\0", SELF_REPO)


def similar(a: str, b: str) -> bool:
    a, b = a.lower().strip(), b.lower().strip()
    ta, tb = set(re.findall(r"\w+", a)), set(re.findall(r"\w+", b))
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8 or jac >= 0.6


def log(ledger: Path, status: str, repo: str, title: str, url: str, body: str) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps({"ts": int(time.time()), "status": status, "repo": repo, "title": title, "url": url,
                            "body_sha256": hashlib.sha256(body.encode()).hexdigest()}) + "\n")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text")
    src.add_argument("--file")
    ap.add_argument("--title")
    ap.add_argument("--repo", default=os.environ.get("PERUN_UPSTREAM", SELF_REPO))
    ap.add_argument("--approve", action="store_true", help="release an `ask`-mode draft")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        import perun_policy  # sibling skill; absent -> the safe default, `ask`
        mode = perun_policy.load()["share_learnings"]
    except ImportError:
        mode = "ask"
    except ValueError as e:
        print(f"share_learning: {e}", file=sys.stderr)
        return 2
    ledger = Path(os.environ.get("PERUN_LEDGER", ".perun/shared-learnings.jsonl"))
    if mode == "off":
        print("share_learning: policy share_learnings=off; nothing shared")
        return 0
    raw = a.text if a.text is not None else Path(a.file).read_text()
    root = Path(os.environ.get("BANLIST_DIR") or subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    pats = banlist(root)
    body = generalize(raw.strip(), pats)
    title = generalize(a.title or body.splitlines()[0][:80] if body else "", pats).strip()
    if not title or not body:
        print("share_learning: empty lesson or title", file=sys.stderr)
        return 2
    body += f"\n\n_Shared by share_learning.py (policy share_learnings={mode})._"
    with tempfile.TemporaryDirectory() as d:
        tf, bf = Path(d, "t"), Path(d, "b")
        tf.write_text(title)
        bf.write_text(body)
        pc = subprocess.run(["bash", str(HERE / "prefile_check.sh"), str(tf), str(bf)],
                            capture_output=True, text=True, env={**os.environ, "BANLIST_DIR": str(root)})
    if pc.returncode != 0:
        print(pc.stderr.strip(), file=sys.stderr)
        log(ledger, "refused", a.repo, "", "", body)  # title withheld: it just failed the privacy gate
        return 1 if pc.returncode == 1 else 2
    if mode == "ask" and not a.approve:
        print(f"share_learning: policy ask; draft below, re-run with --approve to file\nTITLE: {title}\n\n{body}")
        return 3
    gh = os.environ.get("GH", "gh")
    ls = subprocess.run([gh, "issue", "list", "--repo", a.repo, "--state", "all", "--search", title,
                         "--json", "number,title,state", "--limit", "50"], capture_output=True, text=True)
    if ls.returncode != 0:
        print(f"share_learning: gh issue list failed ({ls.stderr.strip()}); not filing", file=sys.stderr)
        return 2
    try:
        dup = next((i for i in json.loads(ls.stdout or "[]") if similar(title, i["title"])), None)
    except (ValueError, KeyError, TypeError):
        print("share_learning: unreadable gh output; not filing", file=sys.stderr)
        return 2
    if dup:
        print(f"share_learning: duplicate of #{dup['number']} ({dup['state']}); not filed")
        log(ledger, "duplicate", a.repo, title, str(dup["number"]), body)
        return 0
    if a.dry_run:
        print(f"share_learning: dry run; would file on {a.repo}: {title}")
        return 0
    cr = subprocess.run([gh, "issue", "create", "--repo", a.repo, "--title", title, "--body", body],
                        capture_output=True, text=True)
    if cr.returncode != 0:
        print(f"share_learning: gh issue create failed ({cr.stderr.strip()})", file=sys.stderr)
        log(ledger, "failed", a.repo, title, "", body)
        return 2
    url = cr.stdout.strip().splitlines()[-1] if cr.stdout.strip() else ""
    log(ledger, "created", a.repo, title, url, body)
    print(f"share_learning: filed {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
