#!/usr/bin/env python3
"""impact_map.py [--base REF] [--repo DIR] [--cap N] — map a diff's changed symbols to callers and callees.

Purpose: a reviewer reading only the hunks misses bugs in code the diff does not touch (a caller that
relied on the old contract, a callee whose precondition the change now violates). This lists, per changed
symbol, the OUT-OF-DIFF files that reference it (callers) and the symbols the changed body calls that
are defined elsewhere (callees), so those files can be opened.

Output (stdout, JSON): {"base","changed_files":[...],"contract_change":bool,"symbols":[{"name","file",
"callers":[{"file","line","text"}],"callees":[{"name","file","line"}]}],"out_of_diff_files":[...],
"truncated":bool}. Edge cases: no diff -> empty lists; names under 3 chars or common keywords skipped;
per-symbol caps (--cap, default 8) bound the output and set "truncated". Heuristic and regex-based
(def/function/class/fn/func/const-arrow): a LEAD generator, not a call graph; dynamic dispatch and
reflection are invisible. Side effects: none (read-only git subprocesses).
"""
import argparse
import json
import re
import subprocess
import sys

KW = r"(?:def|function|class|fn|func|interface|type|struct|enum)"
DEF_RE = re.compile(r"^[+-]?\s*(?:export\s+|public\s+|private\s+|static\s+|async\s+|pub(?:\([a-z]+\))?\s+)*"
                    + KW + r"\s+([A-Za-z_][A-Za-z0-9_]*)"
                    r"|^[+-]?\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(")
HUNK_RE = re.compile(r"^@@ .*?" + KW + r"\s+([A-Za-z_][A-Za-z0-9_]*)")
SKIP = {"main", "init", "test", "self", "this", "new", "get", "set", "run"}


def sh(args, cwd):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.stdout if r.returncode in (0, 1) else ""


def parse_diff(diff):
    """Return ({file: set(symbols)}, contract_change). A def line added/removed marks a contract change."""
    files, cur, contract = {}, None, False
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
            if cur:
                files.setdefault(cur, set())
        elif cur is None or ln.startswith("--- "):
            continue
        else:
            is_change = ln[:1] in "+-"
            m = HUNK_RE.match(ln) if ln.startswith("@@") else (DEF_RE.match(ln) if is_change else None)
            if m:
                name = next(g for g in m.groups() if g)
                if len(name) >= 3 and name not in SKIP:
                    files[cur].add(name)
                contract = contract or is_change
    return files, contract


def callers(sym, changed, repo, cap):
    res = []
    for ln in sh(["git", "grep", "-nIw", "--", sym], repo).splitlines():
        f, _, rest = ln.partition(":")
        if f in changed:
            continue
        n, _, text = rest.partition(":")
        res.append({"file": f, "line": int(n) if n.isdigit() else 0, "text": text.strip()[:160]})
    return res[: cap + 1]


def callees(file, sym, repo, cap):
    """Call-shaped names in sym's body that are defined in some other tracked file."""
    try:
        with open(f"{repo}/{file}", encoding="utf-8", errors="replace") as fh:
            src = fh.read().splitlines()
    except OSError:
        return []
    start = next((i for i, l in enumerate(src) if DEF_RE.match(l) and re.search(rf"\b{re.escape(sym)}\b", l)), None)
    if start is None:
        return []
    ind = len(src[start]) - len(src[start].lstrip())
    body = []
    for l in src[start + 1: start + 200]:
        if l.strip() and len(l) - len(l.lstrip()) <= ind and not l.lstrip().startswith((")", "}", "]")):
            break
        body.append(l)
    names = {n for n in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\(", "\n".join(body))
             if len(n) >= 3 and n not in SKIP and n != sym}
    res = []
    for n in sorted(names):
        d = sh(["git", "grep", "-nIEw", rf"{KW.replace('?:', '')}[[:space:]]+{n}", "--", ".", ":!" + file], repo).splitlines()
        if d:
            f, _, rest = d[0].partition(":")
            ln = rest.split(":")[0]
            res.append({"name": n, "file": f, "line": int(ln) if ln.isdigit() else 0})
        if len(res) > cap:
            break
    return res[: cap + 1]


def build(base, repo, cap):
    diff = sh(["git", "diff", "--unified=0", "--no-color", f"{base}...HEAD"], repo)
    files, contract = parse_diff(diff)
    changed = set(files)
    syms, out_files, trunc = [], set(), False
    for f, names in sorted(files.items()):
        for s in sorted(names):
            cs, ce = callers(s, changed, repo, cap), callees(f, s, repo, cap)
            trunc = trunc or len(cs) > cap or len(ce) > cap
            syms.append({"name": s, "file": f, "callers": cs[:cap], "callees": ce[:cap]})
            out_files.update(c["file"] for c in cs[:cap] + ce[:cap] if c["file"] not in changed)
    return {"base": base, "changed_files": sorted(changed), "contract_change": contract, "symbols": syms,
            "out_of_diff_files": sorted(out_files), "truncated": trunc}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--cap", type=int, default=8)
    a = ap.parse_args()
    json.dump(build(a.base, a.repo, a.cap), sys.stdout, indent=1)
    print()
