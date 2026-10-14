#!/usr/bin/env python3
"""env_lint.py [--base REF [--head REF]] [--root DIR] [--deadline SECS] [FILES...] | --selftest -- flag tests that read an env var with no default.

WHY: a test that reads `os.environ["X"]` passes in the author's shell, then fails where X differs: the CI or train
runner exports its own class/slot/runner variables, and a repeat guard re-runs the test in a scrubbed environment.
Flagged reads (py/js/ts test files only): py `os.environ[X]`, `os.environ.get(X)` and `os.getenv(X)` with one
argument and no trailing `or`; js/ts `process.env.X` / `process.env[X]` with no `??`/`||` fallback. Assignments and
deletes are not reads; `NODE_ENV` (set by the runner) is exempt.
A read is exempt only where the test sets the environment in scope: monkeypatch.setenv/delenv, patch.dict(os.environ),
an `os.environ[X] = ...` / `process.env.X = ...` write, vi.stubEnv, jest.replaceProperty(process, ...), or
Object.assign(process.env, ...). Scope is the enclosing test function/block; a marker in the file preamble or a
fixture/setUp/beforeEach/describe block covers the whole file. Escape: `env-lint: allow` on the line or on a comment
line above it.
Files, test-file detection and --base/--head/--deadline follow clock_lint.py (which this imports). Output
`file:line: test reads env var X without default; set it in the test or give a default`.
Exit: 0 clean, 1 findings, 2 could not check (printed as COULD_NOT_CHECK).
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clock_lint as cl

ALLOW = "env-lint: allow"
PY = re.compile(r"(?<!del )os\.environ\s*\[[^\]]*\](?!\s*(?:[-+|]?=(?!=)))|\bos\.(?:environ\.get|getenv)\s*\(")
JS = re.compile(r"(?<!delete )process\.env(?:\.(?!NODE_ENV\b)\w+\b|\[[^\]]*\])(?!\s*(?:\?\?|\|\||[-+|]?=(?!=)))")
SET = re.compile(r"monkeypatch\.(?:setenv|delenv)|patch\.dict\(\s*(?:os\.environ|'')|vi\.stubEnv|jest\.replaceProperty\(\s*process"
                 r"|Object\.assign\(\s*process\.env|os\.environ(?:\[[^\]]*\]\s*=(?!=)|\.(?:setdefault|update|pop)\()"
                 r"|process\.env(?:\.\w+|\[[^\]]*\])?\s*=(?!=)")
NAME = re.compile(r"""(?:os\.(?:environ\[|environ\.get\(|getenv\()|process\.env(?:\.|\[))\s*['"]?(\w+)""")


def hit(lang, c):
    """True when code line `c` (strings blanked) reads an env var with no default."""
    if lang == "js":
        return bool(JS.search(c))
    for m in PY.finditer(c):
        if m.group(0).endswith("]"):
            return True
        depth, i = 1, m.end()  # find the call's closing paren; a top-level comma means a default was given
        while i < len(c) and depth:
            depth += (c[i] == "(") - (c[i] == ")")
            if c[i] == "," and depth == 1:
                break
            i += 1
        else:
            if not re.match(r"\s*or\b", c[i:]):
                return True
    return False


def scan(path, text):
    """[(line_no, env var name)] of default-less env reads in a py/js test `text`."""
    lines = text.split("\n")
    return [(n, (NAME.search(lines[n - 1]) or [0, "<expr>"])[1])
            for n, _ in cl.scan(path, text, hit, SET, ALLOW)]


def run(root, base, args, head="HEAD", deadline=None):
    bad = cant = 0
    end = time.monotonic() + deadline if deadline is not None else None
    try:
        paths = cl.files(root, base, head, args)
    except OSError as e:
        print("COULD_NOT_CHECK %s" % e)
        return 2
    for f in paths:
        if end is not None and time.monotonic() > end:
            print("COULD_NOT_CHECK deadline exceeded before %s" % f)
            return 1 if bad else 2
        ext = f.rsplit(".", 1)[-1]
        if not (cl.TEST_RE.search(f.replace(os.sep, "/")) and cl.EXT.get(ext) in ("py", "js")):
            if args:
                print("SKIP %s: not a test file" % f)
            continue
        rel = f if args else os.path.relpath(os.path.realpath(f), os.path.realpath(root))
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            print("COULD_NOT_CHECK %s: %s" % (rel, e.strerror or e))
            cant += 1
            continue
        for n, name in scan(f, text):
            print("%s:%d: test reads env var %s without default; set it in the test or give a default" % (rel, n, name))
            bad += 1
    return 1 if bad else 2 if cant else 0


def selftest():
    cases = [
        ("test_a.py", 'def test_x():\n    v = os.environ["CLASS_SLOT"]\n', 1),
        ("test_a.py", "def test_x():\n    v = os.environ.get('X')\n", 1),
        ("test_a.py", "def test_x():\n    v = os.getenv('X')\n", 1),
        ("test_a.py", "def test_x():\n    v = os.environ.get('X', 'd')\n    w = os.getenv('Y', None)\n", 0),
        ("test_a.py", "def test_x():\n    v = os.environ.get('X') or 'd'\n", 0),
        ("test_a.py", "def test_x():\n    v = os.environ.get(k(1, 2))\n", 1),
        ("test_a.py", "def test_x():\n    os.environ['X'] = '1'\n    del os.environ['Y']\n", 0),
        ("test_a.py", "def test_x():\n    os.environ['X'] = '1'\n    v = os.environ['X']\n", 0),
        ("test_a.py", "def test_x(monkeypatch):\n    monkeypatch.setenv('X', '1')\n    v = os.environ['X']\n", 0),
        ("test_a.py", "def test_x(monkeypatch):\n    monkeypatch.setenv('X', '1')\ndef test_y():\n    os.getenv('X')\n", 1),
        ("test_a.py", "@mock.patch.dict(os.environ, {'X': '1'})\ndef test_x():\n    os.environ['X']\n", 0),
        ("test_a.py", "def test_x():\n    with patch.dict('os.environ', {'X': '1'}):\n        os.environ['X']\n", 0),
        ("test_a.py", "@pytest.fixture(autouse=True)\ndef env(monkeypatch):\n    monkeypatch.setenv('X', '1')\ndef test_x():\n    os.environ['X']\n", 0),
        ("test_a.py", "def test_x():\n    s = 'os.environ[\"X\"]'  # os.getenv('X')\n", 0),
        ("test_a.py", "def test_x():\n    a = os.environ['X']  # env-lint: allow\n    b = os.environ['Y']\n", 1),
        ("test_a.py", "# env-lint: allow\nx = os.getenv('X')\n", 0),
        ("a.test.ts", "it('a', () => { const v = process.env.CLASS_SLOT; });\n", 1),
        ("a.test.ts", "it('a', () => { const v = process.env['X']; });\n", 1),
        ("a.test.ts", "it('a', () => { const v = process.env.X ?? 'd'; const w = process.env.Y || 'e'; });\n", 0),
        ("a.test.ts", "it('a', () => { process.env.X = '1'; const v = process.env.X; });\n", 0),
        ("a.test.ts", "it('a', () => { const v = process.env.NODE_ENV; });\n", 0),
        ("a.test.ts", "it('a', () => { vi.stubEnv('X', '1'); const v = process.env.X; });\nit('b', () => { process.env.X; });\n", 1),
        ("a.spec.js", "beforeEach(() => { process.env = { ...old }; });\nit('a', () => { process.env.X; });\n", 0),
        ("a.spec.js", "it('a', () => { delete process.env.X; if (process.env.X === 'a') {} });\n", 1),
        ("a.test.js", "it('a', () => { log('T', process.env.TERM || '[none]'); });\n", 0),  # fallback after a long name
        ("test_g.go","x := os.Getenv(\"X\")\n", 0),
    ]
    for name, src, want in cases:
        got = len(scan(name, src)) if name.endswith((".py", ".ts", ".js")) else 0
        assert got == want, (name, src, got, want)
    assert scan("test_a.py", 'def test_x():\n    os.environ["CLASS_SLOT"]\n') == [(2, "CLASS_SLOT")]
    print("env_lint selftest ok")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--root", default=".")
    ap.add_argument("--deadline", type=float)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    return run(a.root, a.base, a.files, a.head, a.deadline)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
