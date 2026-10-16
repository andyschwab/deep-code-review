#!/usr/bin/env python3
"""Mutation testing restricted to the lines a diff changed. Stdlib only, advisory.

Usage: mutation_changed.py [--base origin/main] [--max-seconds 300] [--strict] [--selftest]

Finds changed source lines (`git diff --unified=0 <base>...HEAD`), runs an ALREADY INSTALLED
mutation tool (mutmut 3.x for Python, verified against 3.8.0; Stryker for JS/TS, unverified) on the changed files, and prints
`SURVIVED <file>:<line>: <mutation>` for each surviving mutant on a changed line, i.e. a
mutation of changed code that no test caught. Never installs anything. If no tool is found it
prints COULD_NOT_CHECK with the install hint and exits 0. Exit 1 only with --strict and survivors.
Side effects: the tools write their own caches (.mutmut-cache, .stryker-tmp, reports/mutation).
"""
import argparse, ast, json, os, re, signal, subprocess, sys, tempfile, time

PY = (".py",)
JS = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx")
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)(test_[^/]*|conftest)\.py$|_test\.py$|\.(test|spec)\.[cm]?[jt]sx?$")
HINT = {"python": "pip install mutmut  (3.x; configure [tool.mutmut] source_paths in pyproject.toml)",
        "js": "npm i -D @stryker-mutator/core  (then add your test-runner plugin)"}


def run(cmd, cwd, timeout):
    """-> (returncode, output, timed_out). Kills the whole process group on timeout."""
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=max(timeout, 1))
        return p.returncode, out, False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        return -9, out or "", True
    except FileNotFoundError:
        return 127, "", False


def changed_lines(diff):
    """Parse `git diff --unified=0` -> {path: set(new line numbers)}. Pure deletions add nothing."""
    res, path = {}, None
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            path = ln[4:].split("\t")[0]
            path = path[2:] if path.startswith("b/") else None  # /dev/null -> deleted file
        elif ln.startswith("@@") and path:
            m = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", ln)
            if m:
                s, n = int(m[1]), int(m[2] if m[2] is not None else 1)
                res.setdefault(path, set()).update(range(s, s + n))
    return {p: l for p, l in res.items() if l}


def parse_mutmut_results(text):
    """`mutmut results --all true` (3.x) lines `    pkg.x_func__mutmut_1: survived` -> [(name, status)]."""
    return [(m[1], m[2].strip()) for ln in text.splitlines() if (m := re.match(r"\s+(\S+__mutmut_\d+): (.+)", ln))]


def parse_mutmut_show(text):
    """3.x `mutmut show` diff is relative to the mutated function: -> (offset of first changed line in the
    function, old text, 'old -> new')."""
    old_n, old, off = 0, None, 0
    for ln in text.splitlines():
        if (m := re.match(r"@@ -(\d+)", ln)):
            old_n = int(m[1]); continue
        if not old_n or ln.startswith(("--- ", "+++ ")):
            continue
        if ln.startswith("-") and old is None:
            old, off = ln[1:].strip(), old_n - 1
        elif ln.startswith("+") and old is not None:
            return off, old, f"{old} -> {ln[1:].strip()}"
        if not ln.startswith("+"):
            old_n += 1
    return None


def functions(path):
    """{mutmut function key: (first line, last line)} for top-level functions and methods of top-level classes."""
    try:
        tree = ast.parse(open(path).read())
    except (OSError, SyntaxError):
        return {}
    out = {}
    def add(n, cls=None):
        k = f"x\u01c1{cls}\u01c1{n.name}" if cls else f"x_{n.name}"
        out[k] = (min([n.lineno] + [d.lineno for d in n.decorator_list]), n.end_lineno)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(n)
        elif isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(m, n.name)
    return out


def parse_stryker(report, changed):
    """-> [(file, line, text, "survived")] for Survived/NoCoverage mutants on changed lines."""
    res = []
    for f, d in report.get("files", {}).items():
        lines = changed.get(os.path.relpath(f) if os.path.isabs(f) else f, set())
        for m in d.get("mutants", []):
            ln = m["location"]["start"]["line"]
            if m["status"] in ("Survived", "NoCoverage") and ln in lines:
                res.append((f, ln, f"{m['mutatorName']} -> {str(m.get('replacement', '')).strip()[:80]}", "survived"))
    return res


def check_python(files, changed, cwd, left, mm):
    """mutmut 3.x. Needs the project's own `[tool.mutmut]` / `[mutmut]` config (mutmut cannot even start without it)."""
    rc, out, _ = run(mm + ["--version"], cwd, 60)
    if "Could not figure out where the code to mutate is" in out:
        return ("COULD_NOT_CHECK: mutmut installed but not configured. Add to pyproject.toml: "
                '[tool.mutmut] source_paths = ["<your package or src dir>"]')
    if rc == 127 or "No module named" in out:
        return None
    if rc != 0 or "version 3." not in out:
        return "COULD_NOT_CHECK: needs mutmut 3.x, got: " + out.strip()[-120:]
    funcs = {f: functions(os.path.join(cwd, f)) for f in files}
    pats = sorted({f"*.{k}__mutmut_*" for f in files for k, (a, b) in funcs[f].items() if any(a <= n <= b for n in changed[f])})
    if not pats:
        return ([], False)
    rc, out, to = run(mm + ["run"] + pats, cwd, left)
    if "nothing matches" in out:  # changed lines are not inside any mutable function
        return ([], False)
    rc2, res, _ = run(mm + ["results", "--all", "true"], cwd, 60)
    stat = parse_mutmut_results(res)
    if not stat:
        return f"COULD_NOT_CHECK: mutmut produced no results (rc={rc}): {out.strip()[-300:]}"
    sel = {k for f in files for k, (a, b) in funcs[f].items() if any(a <= n <= b for n in changed[f])}
    key_of = lambda name: name.rpartition(".")[2].split("__mutmut_")[0]
    found, unrun = [], any(st == "not checked" and key_of(n) in sel for n, st in stat)
    for name, st in stat:
        if st not in ("survived", "no tests"):
            continue
        mod, key = name.rpartition(".")[0], key_of(name)
        f = next((f for f in files if key in funcs[f] and f[:-3].replace("/", ".").endswith(mod)), None)
        hit = f and parse_mutmut_show(run(mm + ["show", name], cwd, 60)[1])
        if not hit:
            continue
        off, old, text = hit
        a, b = funcs[f][key]
        src = open(os.path.join(cwd, f)).read().splitlines()
        ln = a + off
        if not (a <= ln <= b and src[ln - 1].strip() == old):  # decorator offset etc: find the line by text
            ln = next((i for i in range(a, b + 1) if src[i - 1].strip() == old), None)
        if ln in changed[f]:
            found.append((f, ln, text, st))
    return (found, to or unrun)


def check_js(files, changed, cwd, left, mm=None):  # UNVERIFIED against a real Stryker run
    if run(["npx", "--no-install", "stryker", "--version"], cwd, 60)[0] != 0:
        return None
    rep = os.path.join(cwd, "reports", "mutation", "mutation.json")
    if os.path.exists(rep):
        os.remove(rep)  # never read a stale report
    cmd = ["npx", "--no-install", "stryker", "run", "--reporters", "json"]
    for f in files:
        for a, b in ranges(sorted(changed[f])):
            cmd += ["--mutate", f"{f}:{a}-{b}"]
    rc, out, to = run(cmd, cwd, left)
    if not os.path.exists(rep):
        return f"COULD_NOT_CHECK: stryker produced no report ({'timeout' if to else out.strip()[-300:]})"
    return (parse_stryker(json.load(open(rep)), changed), to)


def ranges(nums):
    out = []
    for n in nums:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def main(argv=None, cwd=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--max-seconds", type=int, default=300)
    ap.add_argument("--strict", action="store_true", help="exit 1 on survivors")
    ap.add_argument("--mutmut", help="path to a mutmut 3.x binary (default: python3 -m mutmut)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cwd = cwd or "."
    rc, diff, _ = run(["git", "diff", "--unified=0", f"{a.base}...HEAD"], cwd, 60)
    if rc:
        print(f"COULD_NOT_CHECK: git diff {a.base}...HEAD failed: {diff.strip()[-200:]}")
        return 0
    changed = {p: l for p, l in changed_lines(diff).items()
               if p.endswith(PY + JS) and not TEST_RE.search(p) and os.path.exists(os.path.join(cwd, p))}
    if not changed:
        print("NO_CHANGED_SOURCE: no changed non-test .py/.js/.ts files")
        return 0
    mm = [a.mutmut] if a.mutmut else [sys.executable, "-m", "mutmut"]
    deadline, found, survivors = time.time() + a.max_seconds, False, []
    for lang, exts, fn in (("python", PY, check_python), ("js", JS, check_js)):
        files = sorted(p for p in changed if p.endswith(exts))
        if not files:
            continue
        r = fn(files, changed, cwd, int(deadline - time.time()), mm)
        if r is None:
            print(f"COULD_NOT_CHECK: no {lang} mutation tool installed. Install (nothing was installed): {HINT[lang]}")
        elif isinstance(r, str):
            print(r)
        else:
            found = True
            survivors += r[0]
            if r[1]:
                print(f"PARTIAL: {lang} run hit --max-seconds={a.max_seconds}; survivors below are from mutants finished in time")
    for f, ln, m, st in sorted(survivors):
        print(f"{'SURVIVED' if st == 'survived' else 'UNCOVERED'} {f}:{ln}: {m}")
    survivors = [x for x in survivors if x[3] == "survived"]
    if found and not survivors:
        print("OK: no surviving mutants on changed lines")
    return 1 if a.strict and survivors else 0


def selftest():
    global run
    real, mutmut_out = run, {
        "--version": (0, "mutmut, version 3.8.0", False),
        "run": (1, "", False),
        "results": (0, "    sut.x_add__mutmut_1: killed\n    sut.x_f__mutmut_1: survived\n    sut.x_f__mutmut_2: no tests\n"
                       "    sut.x_g__mutmut_1: survived\n    sut.x_g__mutmut_2: not checked\n", False),
        # real mutmut 3.8.0 `show` shape: header comment + diff relative to the function
        "show sut.x_f__mutmut_1": (0, "# sut.x_f__mutmut_1: survived\n--- sut.py\n+++ sut.py\n@@ -1,3 +1,3 @@\n def f():\n-    return True\n+    return False\n", False),
        "show sut.x_f__mutmut_2": (0, "# n\n--- sut.py\n+++ sut.py\n@@ -1,3 +1,3 @@\n def f():\n-    return True\n+    return None\n", False),
        "show sut.x_g__mutmut_1": (0, "# n\n--- sut.py\n+++ sut.py\n@@ -1,2 +1,2 @@\n def g():\n-    x = 1\n+    x = 2\n", False)}

    def fake(cmd, cwd, timeout):
        if cmd[:3] == [sys.executable, "-m", "mutmut"]:
            k = " ".join(cmd[3:5]) if cmd[3] == "show" else ("--version" if "--version" in cmd else cmd[3])
            if k == "run":
                assert cmd[4:] == ["*.x_f__mutmut_*"], cmd  # only the function holding changed lines
            return mutmut_out[k]
        if cmd[0] == "npx":
            if "--version" in cmd:
                return 0, "8.0", False
            os.makedirs(os.path.join(cwd, "reports", "mutation"), exist_ok=True)
            json.dump({"files": {"a.js": {"mutants": [
                {"mutatorName": "EqualityOperator", "replacement": "a !== b", "status": "Survived", "location": {"start": {"line": 3}}},
                {"mutatorName": "StringLiteral", "replacement": '""', "status": "Killed", "location": {"start": {"line": 3}}},
                {"mutatorName": "ArithmeticOperator", "replacement": "a - b", "status": "NoCoverage", "location": {"start": {"line": 99}}}]}}},
                open(os.path.join(cwd, "reports", "mutation", "mutation.json"), "w"))
            return 0, "", False
        return real(cmd, cwd, timeout)

    assert changed_lines("+++ b/x.py\n@@ -1 +1,2 @@\n@@ -5,2 +0,0 @@\n+++ /dev/null\n@@ -1 +0,0 @@\n") == {"x.py": {1, 2}}
    assert ranges([1, 2, 3, 7]) == [[1, 3], [7, 7]]
    assert parse_mutmut_show(mutmut_out["show sut.x_f__mutmut_1"][1]) == (1, "return True", "return True -> return False")
    assert not TEST_RE.search("src/calc.py") and TEST_RE.search("tests/x.py") and TEST_RE.search("a.test.js")
    with tempfile.TemporaryDirectory() as d:
        sh = lambda *c: subprocess.run(c, cwd=d, check=True, capture_output=True)
        sh("git", "init", "-q", "-b", "main")
        sh("git", "config", "user.email", "t@example.com"); sh("git", "config", "user.name", "t")
        open(f"{d}/sut.py", "w").write("def g():\n    x = 1\n"); sh("git", "add", "."); sh("git", "commit", "-qm", "a")
        sh("git", "checkout", "-qb", "f")
        open(f"{d}/sut.py", "w").write("def g():\n    x = 1\n\ndef f():\n    return True\n")
        open(f"{d}/a.js", "w").write("a\nb\nc\n"); open(f"{d}/a.test.js", "w").write("t\n")
        sh("git", "add", "."); sh("git", "commit", "-qm", "b")
        import io, contextlib
        def go(args):
            b = io.StringIO()
            with contextlib.redirect_stdout(b):
                rc = main(args, d)
            return rc, b.getvalue()
        run = fake
        rc, o = go(["--base", "main"])
        assert rc == 0 and o.count("SURVIVED") == 2, o
        assert "SURVIVED sut.py:5: return True -> return False" in o and "UNCOVERED sut.py:5: return True -> return None" in o and "SURVIVED a.js:3: EqualityOperator" in o, o
        assert "sut.py:2:" not in o and "a.js:99" not in o and "a.test.js" not in o, o
        assert "PARTIAL" not in o and go(["--base", "main", "--strict"])[0] == 1
        run = lambda c, cwd, t: real(c, cwd, t) if c[0] == "git" else (127, "", False)  # no tool anywhere
        rc, o = go(["--base", "main", "--strict"])
        assert rc == 0 and o.count("COULD_NOT_CHECK") == 2 and "pip install mutmut" in o and "SURVIVED" not in o, o
        run = real
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
