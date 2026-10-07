#!/usr/bin/env python3
"""finding_ground_check.py <findings.json> [--root DIR] [--ref GITREF] — mark each gap finding grounded or not.

Purpose: cut review noise. A finding is grounded only when its first evidence ref is "path:line" (or
"path:start-end"), the file exists under the root (read at --ref via `git show` when given, else the
working tree), the line is within the file, and its quoted `snippet` (whitespace-normalized) appears
within +-5 lines of the cited line(s). Anything else is ungrounded with a `ground_reason`.
Edge cases: absolute or `..` paths are ungrounded (no reads outside the root); a missing or empty
snippet is ungrounded (nothing to corroborate); strength rows are passed through untouched.
Output: the input JSON on stdout with `grounded` (bool) and `ground_reason` set on every gap row.
Exit 0 on valid input, 2 on usage or unreadable input. Side effects: none (read-only).
"""
import json, os, re, subprocess, sys

WINDOW = 5


def _read(root, path, ref):
    if ref:
        r = subprocess.run(["git", "-C", root, "show", f"{ref}:{path}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    p = os.path.realpath(os.path.join(root, path))
    if not p.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def check(f, root, ref=None):
    """Return (grounded, reason) for one finding row."""
    ev = (f.get("evidence") or [""])[0]
    m = re.match(r"^(.+?):(\d+)(?:-(\d+))?$", ev)
    if not m:
        return False, "no path:line evidence"
    path, a = m[1], int(m[2])
    b = int(m[3] or a)
    if os.path.isabs(path) or ".." in path.split("/"):
        return False, "path outside root"
    text = _read(root, path, ref)
    if text is None:
        return False, "file not found"
    lines = text.splitlines()
    if not (1 <= a <= b <= len(lines)):
        return False, "line out of range"
    snip = _norm(f.get("snippet") or "")
    if not snip:
        return False, "no snippet quoted"
    near = _norm(" ".join(lines[max(0, a - 1 - WINDOW):b + WINDOW]))
    return (True, "ok") if snip in near else (False, "snippet not within +-5 lines")


def ground(d, root, ref=None):
    for f in d["findings"]:
        if f.get("polarity", "gap") == "gap":
            f["grounded"], f["ground_reason"] = check(f, root, ref)
    return d


def usage():
    print("usage: finding_ground_check.py <findings.json> [--root DIR] [--ref GITREF]", file=sys.stderr)
    return 2


def main(argv):
    args, root, ref = argv[1:], os.getcwd(), None
    for flag in ("--root", "--ref"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                return usage()
            val = args[i + 1]
            del args[i:i + 2]
            if flag == "--root":
                root = val
            else:
                ref = val
    if len(args) != 1:
        return usage()
    try:
        with open(args[0], encoding="utf-8") as fh:
            out = ground(json.load(fh), root, ref)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"finding_ground_check: cannot read findings: {type(e).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
