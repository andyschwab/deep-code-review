#!/usr/bin/env python3
"""derived_numbers.py — a number in a doc may be bound to the command that derives it.

WHY THIS EXISTS
A doc that says "11 skills" or "412 tests" is true the day it is written and
stale the day the count moves. This gate binds such a claim to a deterministic
source command with an inline marker, so CI fails when the claim drifts and
`--fix` rewrites it.

MARKER (in any tracked *.md file)
  Perun ships <!-- derived: ls -d .claude/skills/*/SKILL.md \\| wc -l -->11 skills
The marker is an HTML comment `<!-- derived: COMMAND -->` followed immediately
by the claimed integer (digits, optional thousands commas). COMMAND runs with
`sh -c` from the repo root (stdin closed, 60 s timeout). Its trimmed stdout must
be one integer. Write `\\|` for `|` so the command survives inside a markdown
table cell (it is unescaped before running). Markers inside fenced code blocks
and inline `code` spans are ignored, so a doc can show the syntax.

FINDINGS (each exit 1; none are silently skipped)
  drift          claimed number differs from the command's output
  command failed non-zero exit, timeout, or output that is not one integer
  no number      a marker with no integer right after it
Zero markers is a pass (a fresh install has none).

SIDE EFFECTS / TRUST
Runs the commands written in the repo's own docs, with the caller's
privileges. Review marker commands in a PR like any CI script. `--fix` edits
only the claimed number in place, and only when the command succeeded.

USAGE
  python3 derived_numbers.py [--fix] [--selftest] [ROOT]
Exit codes: 0 ok (or fixed); 1 drift or failing marker; 2 usage or selftest failure.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MARK = re.compile(r"<!--\s*derived:\s*(.+?)\s*-->(\d[\d,]*)?")
CODE_SPAN = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^\s*(```|~~~)")


def md_files(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "*.md"], capture_output=True, text=True, check=True).stdout
        return [root / p for p in out.splitlines()]
    except (OSError, subprocess.CalledProcessError):  # not a git checkout
        return [p for p in root.rglob("*.md") if ".git" not in p.parts]


def derive(cmd, root, cache):
    """Return (int, None) or (None, reason); one run per distinct command."""
    if cmd not in cache:
        try:
            r = subprocess.run(["sh", "-c", cmd], cwd=root, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
            out = r.stdout.strip()
            if r.returncode:
                cache[cmd] = (None, f"command failed (exit {r.returncode})")
            elif not re.fullmatch(r"\d+", out):
                cache[cmd] = (None, f"output is not one integer: {out[:40]!r}")
            else:
                cache[cmd] = (int(out), None)
        except (OSError, subprocess.TimeoutExpired) as e:
            cache[cmd] = (None, f"command failed ({type(e).__name__})")
    return cache[cmd]


def scan(root, fix=False):
    """Return (findings, claims). With fix, rewrite drifted numbers in place."""
    cache, bad, n = {}, [], 0
    for path in md_files(root):
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        fenced, changed = False, False
        for i, line in enumerate(lines):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if fenced or "<!--" not in line:
                continue
            blank = CODE_SPAN.sub(lambda m: " " * len(m.group()), line)  # same offsets, spans hidden
            for m in reversed(list(MARK.finditer(blank))):
                n += 1
                where = f"{path.relative_to(root)}:{i + 1}"
                cmd = line[m.start(1):m.end(1)].replace("\\|", "|")
                if m.group(2) is None:
                    bad.append(f"{where}: no number right after the marker for `{cmd}`")
                    continue
                want, why = derive(cmd, root, cache)
                if why:
                    bad.append(f"{where}: `{cmd}`: {why}")
                    continue
                got = int(m.group(2).replace(",", ""))
                if got == want:
                    continue
                if fix:
                    new = f"{want:,}" if "," in m.group(2) else str(want)
                    line = line[:m.start(2)] + new + line[m.end(2):]
                    lines[i], changed = line, True
                else:
                    bad.append(f"{where}: drift: doc says {got}, `{cmd}` prints {want}")
        if changed:
            path.write_text("\n".join(lines), encoding="utf-8")
    return bad, n


def selftest():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        doc = root / "a.md"

        def run(text, fix=False):
            doc.write_text(text, encoding="utf-8")
            return scan(root, fix)

        ok = "<!-- derived: echo 3 -->3 things\n"
        assert run(ok) == ([], 1), "matching claim passes"
        bad, _ = run("<!-- derived: echo 3 -->2 things\n")
        assert len(bad) == 1 and "drift: doc says 2" in bad[0], bad
        assert run("<!-- derived: echo 3 -->2 x\n", fix=True)[0] == [] and doc.read_text() == "<!-- derived: echo 3 -->3 x\n", "fix rewrites"
        assert run("| <!-- derived: echo 3 \\| cat -->9 |\n", fix=True)[0] == [] and "-->3 |" in doc.read_text(), "escaped pipe in table"
        assert run("<!-- derived: echo 1234 -->9\n", fix=True)[0] == [] and "-->1234\n" in doc.read_text()
        assert run("<!-- derived: echo 1234 -->1,000\n", fix=True)[0] == [] and "-->1,234\n" in doc.read_text(), "commas kept"
        assert "failed" in run("<!-- derived: exit 4 -->3\n")[0][0], "failing command"
        assert "not one integer" in run("<!-- derived: echo hi -->3\n")[0][0], "non-integer output"
        assert "no number" in run("<!-- derived: echo 3 --> things\n")[0][0], "marker without number"
        failed, _ = run("<!-- derived: exit 4 -->3\n", fix=True)
        assert failed and doc.read_text() == "<!-- derived: exit 4 -->3\n", "fix never edits on command failure"
        assert run("`<!-- derived: echo 3 -->9`\n```\n<!-- derived: echo 3 -->9\n```\n") == ([], 0), "code is ignored"
        assert run("no markers\n") == ([], 0), "zero markers pass"
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
