#!/usr/bin/env python3
"""derived_numbers.py — a number in a doc may be bound to the counter that derives it.

WHY THIS EXISTS
A doc that says "11 skills" or "412 tests" is true the day it is written and
stale the day the count moves. This gate binds such a claim to a counter with an
inline marker, so CI fails when the claim drifts and `--fix` rewrites it.

MARKER (in any tracked *.md file)
  Perun ships <!-- derived: files .claude/skills/*/SKILL.md -->11 skills
The marker is an HTML comment `<!-- derived: COUNTER ARGS -->` followed
immediately by the claimed integer (digits, optional thousands commas; a
trailing comma, period or decimal part is not part of the number).

COUNTERS (a fixed allowlist, computed in Python; no shell, no subprocess of doc
text, no network)
  files GLOB              tracked files matching GLOB (`*` and `?` stay inside a
                          directory, `**` crosses directories; a run of `*` is one
                          wildcard; at most 200 characters and 4 wildcards, matched
                          without backtracking)
  lines PATH              lines in PATH
  grep-count PATTERN PATH lines of PATH containing PATTERN (a literal substring,
                          not a regex; PATTERN may hold spaces, PATH is the last word)
  json-len PATH KEY       length of the list or object at KEY (dotted; a list
                          index is a number) in the JSON file PATH
Every PATH is repo-relative, with no `..`, and neither it nor any directory on
the way may be a symlink. An unknown counter or bad arguments is a finding and
nothing runs. `\\|` in a marker stands for `|`.
Markers in fenced code, indented code and inline code spans are ignored, so a
doc can show the syntax. Files without `<!--`, symlinks and vendored directories
(node_modules, vendor, dist, build, venv, ...) are skipped.

FINDINGS (each exits 1; none are silently skipped)
  drift          claimed number differs from the counter's result
  bad marker     unknown counter, bad arguments, unsafe or unreadable path
  no number      a marker with no integer right after it
Zero markers is a pass (a fresh install has none).

SIDE EFFECTS
Reads files; runs only `git ls-files` to list tracked files. `--fix` rewrites only
the claimed number, byte-for-byte otherwise (line endings and encoding kept),
via a temp file and an atomic replace, and never when the marker is a finding.

USAGE
  python3 derived_numbers.py [--fix] [--selftest] [ROOT]
Exit codes: 0 ok (or fixed); 1 drift or bad marker; 2 usage or selftest failure.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MARK = re.compile(r"<!--\s*derived:\s*(.+?)\s*-->(?:(\d{1,3}(?:,\d{3})+|\d+)(?![\d]|[.,]\d))?")
CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`).+?(?<!`)\1(?!`)")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
INDENT = re.compile(r"^(?: {4}|\t)")
VENDORED = {"node_modules", "vendor", "third_party", "dist", "build", "venv", ".venv", "site-packages", ".git"}
MAX_BYTES = 10_000_000
COUNTERS = ("files", "lines", "grep-count", "json-len")


def tracked(root):
    """Repo-relative posix paths of tracked files; a plain walk (no symlink follow) outside git."""
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
        return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        found = []
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d != ".git"]
            found += [os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/") for f in fns]
        return found


def safe_file(root, rel):
    """Resolve a repo-relative PATH to a regular file; ValueError if unsafe."""
    parts = rel.split("/")
    if not rel or "\\" in rel or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"unsafe path {rel!r}")
    cur = root
    for p in parts:
        cur = cur / p
        if cur.is_symlink():
            raise ValueError(f"path {rel!r} goes through a symlink")
    if not cur.is_file():
        raise ValueError(f"{rel!r} is not a file")
    if cur.stat().st_size > MAX_BYTES:
        raise ValueError(f"{rel!r} is over {MAX_BYTES} bytes")
    return cur


MAX_GLOB, MAX_WILDCARDS = 200, 4


def glob_tokens(g):
    """Tokenize a GLOB: a run of `*` collapses to one token, `**` (two or more) crosses `/`. ValueError over the caps."""
    if len(g) > MAX_GLOB:
        raise ValueError(f"glob is over {MAX_GLOB} characters")
    toks = []
    for ch in g:
        if ch == "*" and toks and toks[-1] in ("*", "**"):
            toks[-1] = "**"
        elif ch == "*":
            toks.append("*")
        else:
            toks.append("?" if ch == "?" else ch)
    wild = [t for t in toks if t in ("*", "**", "?")]
    if len(wild) > MAX_WILDCARDS:
        raise ValueError(f"glob has {len(wild)} wildcards (at most {MAX_WILDCARDS})")
    return toks


def glob_match(toks, s):
    """Match s against glob_tokens output by tracking the set of live token positions: O(len(s) * wildcards), no backtracking."""
    def close(states):
        out = set(states)
        for i in sorted(states):
            while i < len(toks) and toks[i] in ("*", "**"):  # a star may match nothing
                i += 1
                out.add(i)
        return out

    cur = close({0})
    for ch in s:
        nxt = set()
        for i in cur:
            if i == len(toks):
                continue
            t = toks[i]
            if t == "**":
                nxt.add(i)
            elif t == "*":
                if ch != "/":
                    nxt.add(i)
            elif t == "?":
                if ch != "/":
                    nxt.add(i + 1)
            elif ch == t:
                nxt.add(i + 1)
        cur = close(nxt)
        if not cur:
            return False
    return len(toks) in cur


def count(spec, root, files):
    """Evaluate one counter spec to an int; ValueError on an unknown counter or bad arguments."""
    toks = spec.split(None, 1)
    name, rest = (toks[0], toks[1] if len(toks) > 1 else "") if toks else ("", "")
    if name not in COUNTERS:
        raise ValueError(f"unknown counter {name!r} (allowed: {', '.join(COUNTERS)}); nothing was run")
    if name == "files":
        if not rest or " " in rest or rest.startswith("/") or ".." in rest.split("/"):
            raise ValueError("files takes one repo-relative GLOB")
        toks = glob_tokens(rest)
        return sum(1 for f in files if glob_match(toks, f) and not (root / f).is_symlink())
    if name == "lines":
        if not rest or " " in rest:
            raise ValueError("lines takes one PATH")
        return len(safe_file(root, rest).read_bytes().splitlines())
    if name == "grep-count":
        if len(rest.split()) < 2:
            raise ValueError("grep-count takes PATTERN PATH")
        pattern, path = rest.rsplit(None, 1)
        text = safe_file(root, path).read_bytes().decode("utf-8", "surrogateescape")
        return sum(1 for ln in text.splitlines() if pattern in ln)
    if len(rest.split()) != 2:
        raise ValueError("json-len takes PATH KEY")
    path, key = rest.split()
    try:
        node = json.loads(safe_file(root, path).read_bytes())
        for k in key.split("."):
            node = node[int(k)] if isinstance(node, list) else node[k]
    except (ValueError, KeyError, IndexError, TypeError, RecursionError) as e:
        raise ValueError(f"json-len: cannot read {key!r} in {path!r} ({type(e).__name__})")
    if not isinstance(node, (list, dict)):
        raise ValueError(f"json-len: {key!r} is not a list or object")
    return len(node)


def md_files(root, files):
    for rel in files:
        p = root / rel
        if rel.endswith(".md") and not VENDORED & set(rel.split("/")) and not p.is_symlink() and p.is_file():
            yield rel, p


def scan(root, fix=False):
    """Return (findings, claims). With fix, rewrite drifted numbers in place."""
    files = tracked(root)
    bad, n = [], 0
    for rel, path in md_files(root, files):
        data = path.read_bytes()
        if b"<!--" not in data:
            continue
        text = data.decode("utf-8", "surrogateescape")
        lines = text.split("\n")  # a CRLF keeps its \r at the line end, so it round-trips
        fence, prev_indented, prev_blank, changed = None, False, True, False
        for i, line in enumerate(lines):
            stripped = line.rstrip("\r")
            f = FENCE.match(stripped)
            if fence:
                if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= fence[1] and not f.group(2).strip():
                    fence = None
                continue
            if f and not (f.group(1)[0] == "`" and "`" in f.group(2)):
                fence = (f.group(1)[0], len(f.group(1)))
                continue
            # ponytail: a 4-space line after a blank or code line is code; an indented list continuation
            # is skipped too (upgrade to a real list parser if a marker is ever needed there)
            indented = bool(INDENT.match(stripped)) and (prev_blank or prev_indented)
            prev_blank, prev_indented = not stripped.strip(), indented
            if indented or "<!--" not in line:
                continue
            blank = CODE_SPAN.sub(lambda m: " " * len(m.group()), line)  # same offsets, spans hidden
            for m in reversed(list(MARK.finditer(blank))):
                n += 1
                where = f"{rel}:{i + 1}"
                spec = line[m.start(1):m.end(1)].replace("\\|", "|")
                if m.group(2) is None:
                    bad.append(f"{where}: no number right after the marker for `{spec}`")
                    continue
                try:
                    want = count(spec, root, files)
                except ValueError as e:
                    bad.append(f"{where}: bad marker `{spec}`: {e}")
                    continue
                got = int(m.group(2).replace(",", ""))
                if got == want:
                    continue
                if fix:
                    new = f"{want:,}" if "," in m.group(2) else str(want)
                    lines[i] = line = line[:m.start(2)] + new + line[m.end(2):]
                    changed = True
                else:
                    bad.append(f"{where}: drift: doc says {got}, `{spec}` gives {want}")
        if changed:
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".derived-")
            try:
                with os.fdopen(fd, "wb") as fh:
                    fh.write("\n".join(lines).encode("utf-8", "surrogateescape"))
                shutil.copymode(path, tmp)
                os.replace(tmp, path)
            except BaseException:
                os.unlink(tmp)
                raise
    return bad, n


def selftest():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for name in ("a.txt", "b.txt"):
            (root / name).write_text("x\ny\n")
        (root / "data.json").write_text('{"k": {"items": [1, 2, 3]}}')
        doc = root / "a.md"

        def run(text, fix=False):
            doc.write_bytes(text if isinstance(text, bytes) else text.encode())
            return scan(root, fix)

        ok = "<!-- derived: files *.txt -->2 things\n"
        assert run(ok) == ([], 1), "matching claim passes"
        bad, _ = run("<!-- derived: files *.txt -->5 things\n")
        assert len(bad) == 1 and "drift: doc says 5" in bad[0], bad
        assert run("<!-- derived: files *.txt -->5 x\n", fix=True)[0] == [] and doc.read_text() == ok.replace("things", "x"), "fix rewrites"
        assert run("<!-- derived: lines a.txt -->0 | <!-- derived: json-len data.json k.items -->0\n", fix=True)[0] == []
        assert doc.read_text() == "<!-- derived: lines a.txt -->2 | <!-- derived: json-len data.json k.items -->3\n"
        assert run("<!-- derived: grep-count y a.txt -->0\n", fix=True)[0] == [] and "-->1\n" in doc.read_text()
        assert run("<!-- derived: files *.txt -->2, and 3.5 more\n")[0] == [], "trailing comma is not the number"
        assert "no number" in run("<!-- derived: files *.txt -->3.5 more\n")[0][0], "a decimal is not an integer claim"
        assert run("<!-- derived: lines a.txt -->1,000\n", fix=True)[0] == [] and "-->2\n" in doc.read_text()
        crlf = run(b"a\r\n<!-- derived: files *.txt -->9\r\nb\r\n", fix=True)
        assert crlf[0] == [] and doc.read_bytes() == b"a\r\n<!-- derived: files *.txt -->2\r\nb\r\n", "CRLF kept"
        assert run(b"caf\xe9 <!-- derived: files *.txt -->9\n", fix=True)[0] == [] and doc.read_bytes() == b"caf\xe9 <!-- derived: files *.txt -->2\n", "non-UTF-8 kept"
        for evil in ("touch PWNED", "files *.txt; touch PWNED", "$(touch PWNED)", "lines ../a.txt", "lines /etc/passwd", "grep-count x"):
            b, _ = run(f"<!-- derived: {evil} -->1\n")
            assert len(b) == 1 and "bad marker" in b[0], (evil, b)
        assert not (root / "PWNED").exists() and not Path("PWNED").exists(), "nothing was executed"
        (root / "link.txt").symlink_to(root / "a.txt")
        assert "symlink" in run("<!-- derived: lines link.txt -->2\n")[0][0], "symlink refused"
        assert run("```\n<!-- derived: files *.txt -->9\n```\n````md\n```\n<!-- derived: files *.txt -->9\n```\n````\n"
                   "`<!-- derived: files *.txt -->9`\n``a ` <!-- derived: files *.txt -->9 ``\n\n    <!-- derived: files *.txt -->9\n") == ([], 0), "code ignored"
        assert run("no markers\n") == ([], 0), "zero markers pass"
        m = lambda g, s: glob_match(glob_tokens(g), s)  # noqa: E731
        assert m(".claude/skills/*/SKILL.md", ".claude/skills/a/SKILL.md") and not m(".claude/skills/*/SKILL.md", ".claude/skills/a/b/SKILL.md")
        assert m("docs/**.md", "docs/a/b.md") and m("a***b", "a/x/b") and m("a?c", "abc") and not m("a?c", "a/c") and m("*", "") and not m("*", "a/b")
        pathological = "**a" * 8 + "**Z"  # 9 wildcards: over the cap, so it never reaches the matcher
        b, _ = run(f"<!-- derived: files {pathological} -->1\n")
        assert len(b) == 1 and "bad marker" in b[0] and "wildcards" in b[0], b
        assert "200 characters" in run(f"<!-- derived: files {'a' * 201} -->1\n")[0][0]
        paths = ["a" * 100 + str(i) for i in range(1000)]
        t0 = time.monotonic()
        assert sum(glob_match(glob_tokens("**a**a**a**Z"), p) for p in paths) == 0  # at the cap: linear, not exponential
        assert time.monotonic() - t0 < 1, "glob matching must not backtrack"
        (root / "deep.json").write_text("[" * 200000)
        assert "bad marker" in run("<!-- derived: json-len deep.json 0 -->1\n")[0][0], "RecursionError is a finding"
    print("derived_numbers selftest ok")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--selftest" in argv:
        try:
            selftest()
        except AssertionError as e:
            print(f"selftest FAILED: {e}", file=sys.stderr)
            return 2
        return 0
    if len(args) > 1 or any(a not in ("--fix", "--selftest") for a in argv if a.startswith("--")):
        print(__doc__.split("USAGE")[1].strip(), file=sys.stderr)
        return 2
    root = Path(args[0] if args else ".").resolve()
    bad, n = scan(root, "--fix" in argv)
    for b in bad:
        print(b, file=sys.stderr)
    print(f"derived_numbers: {n} claim(s), {len(bad)} finding(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
