#!/usr/bin/env python3
"""Warn-only scope-creep report for a git range: scope_creep_check.py BASE HEAD [--repo DIR].

Reports, against the touched scope: (1) new files, (2) new dependencies in
package.json, requirements*.txt, pyproject.toml, go.mod, Cargo.toml, (3) new
classes/interfaces with exactly one implementation in HEAD. Heuristic
regexes (python/TS/Java-style `class`/`interface`; Go interfaces are not
resolved): a lead for a reviewer, never a verdict. ALWAYS exits 0 (warn-only);
errors print a note and still exit 0. Stdlib only.
"""
import json
import os
import re
import subprocess
import sys

DEPS = re.compile(r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|go\.mod|Cargo\.toml)$")
META = {"name", "version", "edition", "description", "license", "authors", "readme", "repository",
        "homepage", "keywords", "categories", "requires-python", "module", "go", "rust-version"}
TYPE = re.compile(r"^\+\s*(?:export\s+)?(?:abstract\s+)?(?:class|interface)\s+(\w+)")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout


def added(repo, rng, path):
    return [l[1:] for l in git(repo, "diff", "-U0", rng, "--", path).splitlines()
            if l.startswith("+") and not l.startswith("+++")]


def json_deps(repo, ref, path):
    try:
        d = json.loads(git(repo, "show", f"{ref}:{path}"))
    except Exception:
        return set()
    return {k for s in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
            for k in (d.get(s) or {})}


def dep_name(path, line):
    s = line.strip()
    if path.endswith("go.mod"):
        m = re.match(r"(?:require\s+)?([\w.\-]+/[\w./\-]+)\s+v\S+", s)
    elif path.endswith("Cargo.toml"):
        m = re.match(r"([A-Za-z0-9_\-]+)\s*=\s*(?:\"|\{)", s)
    elif path.endswith("pyproject.toml"):
        m = re.match(r"\"([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(?:[<>=!~;].*)?\",?$", s) or \
            re.match(r"([A-Za-z0-9_\-]+)\s*=\s*(?:\"|\{)", s)
    else:  # requirements*.txt
        m = re.match(r"([A-Za-z0-9_.\-]+)\s*(?:[<>=!~;\[].*)?$", s) if not s.startswith(("#", "-")) else None
    return m.group(1) if m and m.group(1) not in META else None


def report(repo, base, head):
    rng = f"{base}..{head}"
    out = []
    status = [l.split("\t") for l in git(repo, "diff", "--name-status", rng).splitlines()]
    new = [p[-1] for p in status if p[0] == "A"]
    out.append(f"scope: {len(status)} files touched, {len(new)} new")
    out += [f"WARN new file: {p}" for p in new]
    for p in (p[-1] for p in status if DEPS.search(p[-1]) and p[0] != "D"):
        if p.endswith("package.json"):
            old = json_deps(repo, base, p)
            names = sorted(json_deps(repo, head, p) - old)
        else:
            names = sorted({n for n in (dep_name(p, l) for l in added(repo, rng, p)) if n})
        out += [f"WARN new dependency: {n} ({p})" for n in names]
    types = {}
    for p in new + [p[-1] for p in status if p[0] == "M"]:
        if re.search(r"\.(py|ts|tsx|js|java|kt|cs)$", p):
            for l in added(repo, rng, p):
                m = TYPE.match("+" + l)
                if m:
                    types[m.group(1)] = p
    for name, p in sorted(types.items()):
        pat = rf"(class|interface)[[:space:]]+[[:alnum:]_]+[^{{]*[^[:alnum:]_]{name}([^[:alnum:]_]|$)"  # POSIX ERE: macOS git grep lacks \s \b
        try:
            hits = [h for h in git(repo, "grep", "-nE", pat, head).splitlines() if f"class {name}" not in h and f"interface {name}" not in h]
        except subprocess.CalledProcessError:
            hits = []
        if len(hits) == 1:
            out.append(f"WARN {name} ({p}) has exactly one implementation: {hits[0].split(':', 3)[1]}")
    return out


def main(argv):
    try:
        repo = argv[argv.index("--repo") + 1] if "--repo" in argv else "."
        pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--repo")]
        print("\n".join(report(repo, pos[0], pos[1])))
    except Exception as e:  # warn-only: never block
        print(f"scope_creep_check: skipped ({e})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
