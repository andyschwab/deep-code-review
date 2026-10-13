#!/usr/bin/env python3
"""vacuous_test_gate.py REPORT (--changed PATH... | --base REF) — a changed test file must really run.

WHY: a spec that asserts nothing, or skips itself when fixture data is missing, reads green. For every changed
or added test file, look it up in a test report and print one line:
  FAIL <path>: 0 tests executed | all N tests skipped | 0 assertions
  OK <path>: N executed
  COULD_NOT_CHECK <path>: not in report / report unreadable   (never green: the file may not have run at all)
REPORT formats (auto-detected): JUnit XML (`<testcase file|classname>`; optional `assertions` attr, e.g. Playwright
and PHPUnit emit counts, pytest does not), Jest JSON (`testResults[].name/assertionResults[].status`), and the
pytest-json-report shape (`tests[].nodeid/outcome`). Assertion counts are only checked when the report carries them.
--changed takes paths; --base REF takes added/changed/renamed files from `git diff --name-only --diff-filter=ACMR
REF...HEAD` filtered to test-looking names (test_*, *_test.*, *.test.*, *.spec.*, or under test/tests/__tests__).
Exit: 0 all OK (or no changed test files), 1 any FAIL, 3 any COULD_NOT_CHECK and no FAIL, 2 usage error.
Limits: path matching is by suffix/dotted-classname, so two files with one basename in different dirs can be
conflated when the report has no directory; this errs toward OK only if one of them really ran.
"""
import argparse, json, os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

SKIP = {"skipped", "pending", "todo", "disabled", "skip"}
TESTY = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.(py|go)|[^/]*Test\.java|[^/]*Tests\.cs|[^/]*_spec\.rb"
                   r"|[^/]*\.(test|spec|tests)\.[^/]*)$|(^|/)(tests?|__tests__)/")
DATA = re.compile(r"\.(json|ya?ml|snap|md|txt|csv|xml|png|svg)$|(^|/)(fixtures?|__snapshots__|snapshots)/")


def is_test_file(p):
    """True for a source test file; fixtures, data and snapshots are not tests."""
    return bool(TESTY.search(p)) and not DATA.search(p)


def _rec(d, key, skipped, asserts=None):
    r = d.setdefault(key, {"n": 0, "skip": 0, "asserts": None})
    if skipped is not None:
        r["n"] += 1
        r["skip"] += bool(skipped)
    if asserts is not None:
        r["asserts"] = (r["asserts"] or 0) + asserts


def parse(text):
    """Return {report-key: {n, skip, asserts|None}}; raise ValueError if the format is unknown."""
    d = {}
    s = text.lstrip()
    if re.search(r"<!(DOCTYPE|ENTITY)", s, re.I):
        raise ValueError("report contains DOCTYPE/ENTITY (refused)")
    if s.startswith("<"):
        for el in ET.fromstring(s).iter():
            if el.tag == "testsuite" and el.get("tests") == "0" and (el.get("file") or el.get("name")):
                _rec(d, el.get("file") or el.get("name"), None)
            if el.tag == "testcase":
                a = el.get("assertions")
                _rec(d, el.get("file") or el.get("classname") or "", any(c.tag == "skipped" for c in el),
                     int(a) if a and a.isdigit() else None)
    else:
        j = json.loads(s)
        if not isinstance(j, dict):
            raise ValueError("JSON report is not an object")
        if "testResults" in j:  # Jest
            for f in j["testResults"]:
                _rec(d, f.get("name", ""), None)
                for t in f.get("assertionResults", []):
                    _rec(d, f.get("name", ""), t.get("status") in SKIP)
        elif "tests" in j:  # pytest-json-report
            for t in j["tests"]:
                _rec(d, t.get("nodeid", "").split("::")[0], t.get("outcome") in SKIP)
        else:
            raise ValueError("unknown JSON report shape")
    return d


def lookup(rep, path, repo_files=()):
    """Merge report entries naming `path`. None = absent; "AMBIGUOUS" = several distinct files could match."""
    p = path.replace("\\", "/").lstrip("./")
    base = p.rsplit("/", 1)[-1]
    dotted = re.sub(r"\.[^./]+$", "", p).replace("/", ".")
    hit, ids = [], set()
    for k, v in rep.items():
        if not k:
            continue
        kn = k.replace("\\", "/")
        ident = None
        if kn == p or p.endswith("/" + kn) or kn.endswith("/" + p):
            ident = kn
            if "/" not in kn and kn != p and sum(1 for r in repo_files if r.rsplit("/", 1)[-1] == base) > 1:
                ident = "bare:" + kn  # basename-only match while another repo file shares the name
                ids.add("other-file")
        elif "." in dotted:  # a single token (e.g. "test") is never a dotted match
            m = re.search(r"(^|\.)" + re.escape(dotted) + r"(\.|$)", k)
            if m:
                ident = k[:m.end(0)].rstrip(".")
        if ident:
            hit.append(v)
            ids.add(ident)
    if not hit:
        return None
    if len(ids) > 1:
        return "AMBIGUOUS"
    m = {"n": sum(h["n"] for h in hit), "skip": sum(h["skip"] for h in hit), "asserts": None}
    a = [h["asserts"] for h in hit if h["asserts"] is not None]
    if a:
        m["asserts"] = sum(a)
    return m


def verdict(m):
    if m is None:
        return "COULD_NOT_CHECK", "not in report (did it run?)"
    if m == "AMBIGUOUS":
        return "COULD_NOT_CHECK", "ambiguous: several report entries or repo files could be this file"
    if m["n"] == 0:
        return "FAIL", "0 tests executed"
    if m["skip"] == m["n"]:
        return "FAIL", f"all {m['n']} tests skipped"
    if m["asserts"] == 0:
        return "FAIL", "0 assertions"
    return "OK", f"{m['n'] - m['skip']} executed"


def check(report_text, paths, repo_files=()):
    """[(status, path, why)] per path. Any report problem = COULD_NOT_CHECK, never a traceback."""
    try:
        rep = parse(report_text)
    except Exception as e:  # malformed XML/JSON, wrong shape, recursion: all unverifiable
        return [("COULD_NOT_CHECK", p, f"report unreadable: {type(e).__name__}: {str(e)[:80]}") for p in paths]
    out = []
    for p in paths:
        v = verdict(lookup(rep, p, repo_files))
        out.append((v[0], p, v[1]))
    return out


def selftest():
    junit = ('<testsuites><testsuite name="a" tests="4"><testcase classname="tests/ok.spec.ts" assertions="3"/>'
             '<testcase classname="tests/skip.spec.ts"><skipped/></testcase>'
             '<testcase classname="tests/noassert.spec.ts" assertions="0"/>'
             '<testcase classname="pkg.test_mod.TestX" name="t"/></testsuite>'
             '<testsuite name="tests/empty.spec.ts" tests="0"/></testsuites>')
    want = {"tests/ok.spec.ts": "OK", "tests/skip.spec.ts": "FAIL", "tests/noassert.spec.ts": "FAIL",
            "pkg/test_mod.py": "OK", "tests/empty.spec.ts": "FAIL", "tests/gone.spec.ts": "COULD_NOT_CHECK"}
    got = {p: s for s, p, _ in check(junit, list(want))}
    assert got == want, got
    jest = json.dumps({"testResults": [{"name": "/r/a.test.js", "assertionResults": [{"status": "passed"}]},
                                       {"name": "/r/b.test.js", "assertionResults": [{"status": "pending"}]}]})
    assert [s for s, _, _ in check(jest, ["a.test.js", "b.test.js"])] == ["OK", "FAIL"]
    py = json.dumps({"tests": [{"nodeid": "t/test_x.py::t1", "outcome": "skipped"}]})
    assert check(py, ["t/test_x.py"])[0][0] == "FAIL"
    assert check("not a report", ["x.py"])[0][0] == "COULD_NOT_CHECK"
    assert check("<testsuites/>", ["x_test.go"])[0][0] == "COULD_NOT_CHECK"
    with tempfile.TemporaryDirectory() as t:  # end-to-end exit codes
        r = os.path.join(t, "r.xml")
        open(r, "w").write(junit)
        me = [sys.executable, os.path.abspath(__file__), r, "--changed"]
        rc = lambda *p: subprocess.run(me + list(p), capture_output=True).returncode
        assert (rc("tests/ok.spec.ts"), rc("tests/skip.spec.ts"), rc("tests/gone.spec.ts"),
                rc("tests/skip.spec.ts", "tests/gone.spec.ts")) == (0, 1, 3, 1)
    # same-basename conflation: bare-basename report entry + two repo files sharing it = ambiguous; sole file = ok
    bare = '<testsuites><testcase classname="x.spec.ts"/></testsuites>'
    assert check(bare, ["a/x.spec.ts"], ["a/x.spec.ts", "b/x.spec.ts"])[0][0] == "COULD_NOT_CHECK"
    assert check(bare, ["a/x.spec.ts"], ["a/x.spec.ts"])[0][0] == "OK"
    two = '<testsuites><testcase file="a/x.spec.ts"/><testcase file="b/x.spec.ts"/></testsuites>'
    assert check(two, ["x.spec.ts"])[0][0] == "COULD_NOT_CHECK"  # suffix matches two distinct files
    assert check('<testsuites><testcase classname="test"/></testsuites>', ["a/test.py"])[0][0] == "COULD_NOT_CHECK"
    # hostile / malformed reports never traceback
    for bad in ('<!DOCTYPE x [<!ENTITY a "b">]><testsuites/>', "<testsuites>", "[1]", "{"):
        assert check(bad, ["t_test.go"])[0][0] == "COULD_NOT_CHECK", bad
    assert check('{"tests": 5}', ["t_test.go"])[0][0] == "COULD_NOT_CHECK"
    # test-file pattern: widened for common stacks, data/fixtures excluded
    assert all(map(is_test_file, ["A/FooTest.java", "B/BarTests.cs", "s/x_spec.rb", "a.tests.ts", "p/y_test.go", "q/test_z.py"]))
    assert not any(map(is_test_file, ["tests/data.json", "a/fixtures/t.test.ts", "x.spec.ts.snap", "src/app.py"]))
    # --base: paths with spaces and non-ASCII survive git's NUL-separated output
    with tempfile.TemporaryDirectory() as t:
        g = lambda *c: subprocess.run(["git", "-C", t, "-c", "user.email=a@example.com", "-c", "user.name=a", *c],
                                      capture_output=True, check=True)
        g("init", "-q")
        g("commit", "-q", "--allow-empty", "-m", "base")
        os.makedirs(os.path.join(t, "my tests"))
        names = ["my tests/caf\u00e9 one.spec.ts", "my tests/skip two.spec.ts"]
        for n in names:
            open(os.path.join(t, n), "w").write("x")
        g("add", "-A")
        g("commit", "-q", "-m", "add")
        r = os.path.join(t, "r.xml")
        open(r, "w").write('<testsuites><testcase file="my tests/caf\u00e9 one.spec.ts"/>'
                           '<testcase file="my tests/skip two.spec.ts"><skipped/></testcase></testsuites>')
        o = subprocess.run([sys.executable, os.path.abspath(__file__), r, "--base", "HEAD~1"], cwd=t,
                           capture_output=True, text=True)
        assert o.returncode == 1 and o.stdout.count("\n") == 2 and "FAIL my tests/skip two.spec.ts" in o.stdout, o
    print("selftest ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report", nargs="?")
    ap.add_argument("--changed", nargs="*", default=None)
    ap.add_argument("--base")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest() or 0
    if not a.report or (a.changed is None) == (a.base is None):
        ap.error("need REPORT and exactly one of --changed / --base")
    paths = a.changed
    if a.base:
        o = subprocess.run(["git", "diff", "-z", "--name-only", "--diff-filter=ACMR", f"{a.base}...HEAD"],
                           capture_output=True)
        if o.returncode:
            print(f"COULD_NOT_CHECK: git diff failed: {o.stderr.decode(errors='replace').strip()}")
            return 3
        paths = [p for p in o.stdout.decode("utf-8", "surrogateescape").split("\0") if p and is_test_file(p)]
    try:
        text = open(a.report, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        text = f"<!DOCTYPE unreadable {type(e).__name__}"  # forces the COULD_NOT_CHECK path
    ls = subprocess.run(["git", "ls-files", "-z"], capture_output=True)
    files = ls.stdout.decode("utf-8", "surrogateescape").split("\0") if ls.returncode == 0 else []
    res = check(text, paths, files)
    for s, p, why in res:
        print(f"{s} {p}: {why}")
    st = {s for s, _, _ in res}
    return 1 if "FAIL" in st else 3 if "COULD_NOT_CHECK" in st else 0


if __name__ == "__main__":
    sys.exit(main())
