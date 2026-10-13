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
TESTY = re.compile(r"(^|/)(test_[^/]*|[^/]*_test\.[^/]*|[^/]*\.(test|spec)\.[^/]*)$|(^|/)(tests?|__tests__)/")


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


def lookup(rep, path):
    """Merge every report entry that names `path` (path suffix, or dotted classname); None if absent."""
    p = path.replace("\\", "/").lstrip("./")
    dotted = re.sub(r"\.[^./]+$", "", p).replace("/", ".")
    hit = [v for k, v in rep.items() if k and (
        p == k or p.endswith("/" + k) or k.endswith("/" + p)
        or k == dotted or k.startswith(dotted + ".") or k.endswith("." + dotted) or ("." + dotted + ".") in k)]
    if not hit:
        return None
    m = {"n": sum(h["n"] for h in hit), "skip": sum(h["skip"] for h in hit), "asserts": None}
    a = [h["asserts"] for h in hit if h["asserts"] is not None]
    if a:
        m["asserts"] = sum(a)
    return m


def verdict(m):
    if m is None:
        return "COULD_NOT_CHECK", "not in report (did it run?)"
    if m["n"] == 0:
        return "FAIL", "0 tests executed"
    if m["skip"] == m["n"]:
        return "FAIL", f"all {m['n']} tests skipped"
    if m["asserts"] == 0:
        return "FAIL", "0 assertions"
    return "OK", f"{m['n'] - m['skip']} executed"


def check(report_text, paths):
    """[(status, path, why)] per path."""
    try:
        rep = parse(report_text)
    except (ValueError, ET.ParseError) as e:
        return [("COULD_NOT_CHECK", p, f"report unreadable: {e}") for p in paths]
    out = []
    for p in paths:
        v = verdict(lookup(rep, p))
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
        o = subprocess.run(["git", "diff", "--name-only", "--diff-filter=ACMR", f"{a.base}...HEAD"],
                           capture_output=True, text=True)
        if o.returncode:
            print(f"COULD_NOT_CHECK: git diff failed: {o.stderr.strip()}")
            return 3
        paths = [p for p in o.stdout.split() if TESTY.search(p)]
    try:
        text = open(a.report, encoding="utf-8").read()
    except OSError as e:
        text = f"unreadable {e}"
    res = check(text, paths)
    for s, p, why in res:
        print(f"{s} {p}: {why}")
    st = {s for s, _, _ in res}
    return 1 if "FAIL" in st else 3 if "COULD_NOT_CHECK" in st else 0


if __name__ == "__main__":
    sys.exit(main())
