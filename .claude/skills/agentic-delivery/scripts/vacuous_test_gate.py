#!/usr/bin/env python3
"""vacuous_test_gate.py [REPORT] (--changed PATH... | --base REF) — a changed test file must really run and assert.

WHY: a spec that asserts nothing, or skips itself when fixture data is missing, reads green. Two checks.
STATIC (always, no report needed, stdlib only, zero cost): read each changed .py/.js/.jsx/.ts/.tsx/.mjs/.cjs test
file and print `VACUOUS <path>:<line>: <pattern>` for a test that runs but cannot fail: no assert/expect, constant
or tuple assert, tautology (x == x), a mock asserted after the test itself called it, an assertion swallowed by
try/except, an early return before the asserts, assertions in a nested function/callback that never fires or is
never awaited, expect() with no matcher, a skipped body. Python is an AST walk; JS/TS is conservative text
heuristics. A file that will not parse is COULD_NOT_CHECK. Omit REPORT to run only this check.
REPORT: for every changed or added test file, look it up in a test report and print one line:
  FAIL <path>: 0 tests executed | all N tests skipped | 0 assertions
  OK <path>: N executed
  COULD_NOT_CHECK <path>: not in report / report unreadable   (never green: the file may not have run at all)
REPORT formats (auto-detected): JUnit XML (`<testcase file|classname>`; optional `assertions` attr, e.g. Playwright
and PHPUnit emit counts, pytest does not), Jest JSON (`testResults[].name/assertionResults[].status`), and the
pytest-json-report shape (`tests[].nodeid/outcome`). Assertion counts are only checked when the report carries them.
--changed takes paths; --base REF takes added/changed/renamed files from `git diff --name-only --diff-filter=ACMR
REF...HEAD` filtered to test-looking names (test_*, *_test.*, *.test.*, *.spec.*, or under test/tests/__tests__).
Exit: 0 all OK (or no changed test files), 1 any FAIL or VACUOUS, 3 any COULD_NOT_CHECK and no FAIL, 2 usage error.
Limits: path matching is by suffix/dotted-classname, so two files with one basename in different dirs can be
conflated when the report has no directory; this errs toward OK only if one of them really ran. The static pass
cannot see assertions hidden in imported helpers whose names carry no assert/check/verify/expect word (those read
as "no assertion"), and a deliberate smoke test with no assertion is flagged by design.
"""
import argparse, ast, json, os, re, subprocess, sys, tempfile
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


# ---- static pass: a test that runs but cannot fail (reads the source, not the report) ----
JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
ASSERTY = re.compile(r"assert|fail|raises|warns|check|verify|expect|validate|ensure|should", re.I)
CALL_INFO = {"called", "call_count", "call_args", "call_args_list", "method_calls", "mock_calls"}
MOCKS = {"Mock", "MagicMock", "AsyncMock", "NonCallableMock"}
DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _name(n):
    """Last identifier of a call/attribute target ('' when it is not a plain name or attribute)."""
    f = n.func if isinstance(n, ast.Call) else n
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""


def _py_fn(f, helpers, cls_skip=None):
    """[(lineno, pattern)] for one Python test function."""
    hits = []
    hit = lambda n, msg: hits.append((n.lineno, msg))
    for d in f.decorator_list:
        if _name(d.func if isinstance(d, ast.Call) else d) == "skip":
            hit(f, "skipped test (unconditional skip decorator)")
    if cls_skip:
        hit(cls_skip, "skipped test (unconditional skip decorator on the class)")
    refs = {n.id for n in ast.walk(f) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    dead = [n for n in ast.walk(f) if isinstance(n, DEFS) and n is not f and n.name not in refs and not n.decorator_list]
    deadset = {id(x) for d in dead for x in ast.walk(d)}
    is_assert = lambda x: isinstance(x, ast.Assert) or (isinstance(x, ast.Call) and (
        ASSERTY.search(_name(x)) is not None or _name(x) in helpers))
    for d in dead:
        if any(is_assert(x) for x in ast.walk(d)):
            hit(d, "assertions in a nested function that is never called")
    nodes = [x for x in ast.walk(f) if id(x) not in deadset]
    if not any(is_assert(x) for x in nodes):
        hit(f, "no assertion in test body")
    alias = {t.id: a.value for a in nodes if isinstance(a, ast.Assign) and isinstance(a.value, ast.Call)
             and isinstance(a.value.func, ast.Name) and a.value.func.id != "next"
             and all(isinstance(g, ast.Constant) for g in a.value.args)
             for t in a.targets if isinstance(t, ast.Name)}
    res = lambda e: alias.get(e.id, e) if isinstance(e, ast.Name) else e

    def same(l, r):
        if ast.dump(l) == ast.dump(r):
            return not any(isinstance(x, ast.Call) for x in ast.walk(l))  # f() == f() may be a determinism check
        return (isinstance(l, ast.Name) or isinstance(r, ast.Name)) and ast.dump(res(l)) == ast.dump(res(r))

    truthy = lambda e: isinstance(e, ast.Constant) and bool(e.value)
    for n in nodes:
        if isinstance(n, ast.Assert):
            t = n.test
            if truthy(t):
                hit(n, "constant assert (always true)")
            elif isinstance(t, ast.Tuple) and t.elts:
                hit(n, "assert on a non-empty tuple (always true)")
            elif isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], (ast.Eq, ast.Is, ast.LtE, ast.GtE)) \
                    and same(t.left, t.comparators[0]):
                hit(n, "tautology (both sides are the same expression)")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            a = n.func.attr
            if a == "assertTrue" and n.args and truthy(n.args[0]):
                hit(n, "constant assert (always true)")
            elif a in ("assertEqual", "assertEquals", "assertIs") and len(n.args) >= 2 and same(n.args[0], n.args[1]):
                hit(n, "tautology (both sides are the same expression)")
        elif isinstance(n, ast.Try) and any(is_assert(x) for s in n.body for x in ast.walk(s)):
            for h in n.handlers:
                ty = [_name(e) for e in (h.type.elts if isinstance(h.type, ast.Tuple) else [h.type])] if h.type else ["Exception"]
                if {"AssertionError", "Exception", "BaseException"} & set(ty) and not any(
                        isinstance(x, ast.Raise) or is_assert(x) for s in h.body for x in ast.walk(s)):
                    hit(n, "assertion inside try whose except swallows AssertionError")
    parent = {id(c): p for p in nodes for c in ast.iter_child_nodes(p)}
    for m in {t.id for a in nodes if isinstance(a, ast.Assign) and isinstance(a.value, ast.Call) and _name(a.value) in MOCKS
              for t in a.targets if isinstance(t, ast.Name)}:
        kinds = set()
        for u in (x for x in nodes if isinstance(x, ast.Name) and x.id == m and isinstance(x.ctx, ast.Load)):
            p = parent[id(u)]
            if isinstance(p, ast.Call) and p.func is u:
                kinds.add("call")
            elif isinstance(p, ast.Attribute) and p.value is u:
                chk = p.attr.startswith("assert") or p.attr in CALL_INFO
                kinds.add("check" if chk else "call" if isinstance(parent.get(id(p)), ast.Call) else "cfg")
            else:
                kinds.add("other")  # passed on, returned, aliased: the code under test may be what calls it
        if {"call", "check"} <= kinds and "other" not in kinds:
            hit(f, f"mock '{m}' is called by the test and then asserted on (checks itself)")
    for i, s in enumerate(f.body):
        later = any(is_assert(x) for r in f.body[i + 1:] for x in ast.walk(r))
        if later and isinstance(s, ast.Return):
            hit(s, "return before assertions")
        elif later and isinstance(s, ast.If) and not s.orelse and isinstance(s.body[-1], ast.Return) \
                and s.body[-1].value is None and not any(is_assert(x) for r in s.body for x in ast.walk(r)):
            hit(s, "early return before assertions")
    return hits


def py_static(src):
    """Static hits for a Python test file: sorted [(line, pattern)]. Raises SyntaxError on unparseable source."""
    tree = ast.parse(src)
    helpers = {f.name for f in ast.walk(tree) if isinstance(f, DEFS) and any(isinstance(x, ast.Assert) for x in ast.walk(f))}
    hits = []
    for top in tree.body:
        if isinstance(top, DEFS) and top.name.startswith("test"):
            hits += _py_fn(top, helpers)
        elif isinstance(top, ast.ClassDef):
            sk = next((d for d in top.decorator_list if _name(d.func if isinstance(d, ast.Call) else d) == "skip"), None)
            for f in top.body:
                if isinstance(f, DEFS) and f.name.startswith("test"):
                    hits += _py_fn(f, helpers, sk)
    return sorted(set(hits))


def _scrub(src):
    """(code, bare): `src` with comments blanked, and with string bodies blanked too; same length, newlines kept."""
    a, b, i, n = list(src), list(src), 0, len(src)

    def blank(buf, lo, hi):
        for k in range(lo, hi):
            if buf[k] != "\n":
                buf[k] = " "
    while i < n:
        c, d = src[i], src[i:i + 2]
        if d in ("//", "/*"):
            j = src.find("\n" if d == "//" else "*/", i + 2)
            j = n if j < 0 else j if d == "//" else j + 2
            blank(a, i, j), blank(b, i, j)
            i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and src[j] != c and (c == "`" or src[j] != "\n"):
                j += 2 if src[j] == "\\" else 1
            blank(b, i + 1, min(j, n))
            i = j + 1
        else:
            i += 1
    return "".join(a), "".join(b)


def _close(s, i):
    """Index of the bracket closing s[i] (all bracket kinds counted together), or -1."""
    d = 0
    for k in range(i, len(s)):
        d += s[k] in "([{"
        d -= s[k] in ")]}"
        if d == 0:
            return k
    return -1


JS_TEST = re.compile(r"(?<![\w$.])(x?(?:test|it))((?:\.\w+)*)\s*\(")
JS_ASSERTY = re.compile(r"\b(?:expect|assert\w*|should|fail|verify\w*|check\w*|cy|getBy\w*|getAllBy\w*|findBy\w*|findAllBy\w*)\b"
                        r"|\.expect\s*\(|\bt\.\w+\s*\(")
JS_SYNC = {"forEach", "map", "filter", "reduce", "some", "every", "find", "findIndex", "flatMap", "each", "sort", "act"}
JS_SELF = re.compile(r"expect\(\s*(-?[\w$.]+|'[^'\n]*'|\"[^\"\n]*\")\s*\)\s*\.\s*(?:toBe|toEqual|toStrictEqual)\(\s*\1\s*\)"
                     r"|expect\(\s*true\s*\)\s*\.\s*toBeTruthy\(\)|expect\(\s*false\s*\)\s*\.\s*toBeFalsy\(\)")
JS_MOCK = re.compile(r"(?:const|let|var)\s+([\w$]+)\s*=\s*(?:(?:jest|vi)\.fn|sinon\.(?:stub|spy))\s*\(")


def _js_body(bare, o, c):
    """(body_lo, body_hi, expression_bodied) of the first function argument of the call opening at o, or None."""
    d, k = 0, o + 1
    while k < c:
        d += bare[k] in "([{"
        d -= bare[k] in ")]}"
        if d == 0 and bare.startswith("=>", k):
            j = k + 2
            while bare[j].isspace():
                j += 1
            return (j + 1, _close(bare, j), False) if bare[j] == "{" else (j, c, True)
        if d == 0 and bare.startswith("function", k):
            j = _close(bare, bare.find("(", k)) + 1
            while bare[j].isspace():
                j += 1
            return j + 1, _close(bare, j), False
        k += 1
    return None


def _js_callbacks(bare, lo, hi):
    """[(start, end, callee)] for each arrow callback in bare[lo:hi]; callee is the call it is an argument of."""
    out = []
    for m in re.finditer(r"=>", bare[lo:hi]):
        p = lo + m.start()
        j = p + 2
        while j < hi and bare[j].isspace():
            j += 1
        if j < hi and bare[j] == "{":
            end = _close(bare, j)
        else:
            d, end = 0, j
            while end < hi and not (d == 0 and bare[end] in ",)]}"):
                d += bare[end] in "([{"
                d -= bare[end] in ")]}"
                end += 1
        d, k = 0, p - 1
        while k >= lo:
            d += bare[k] in ")]}"
            if bare[k] in "([{":
                if d == 0:
                    break
                d -= 1
            k -= 1
        mm = re.search(r"([\w$]+)\s*$", bare[lo:k]) if k >= lo and bare[k] == "(" else None
        out.append((p, end, mm.group(1) if mm else ""))
    return out


def js_static(src):
    """Conservative static hits for a JS/TS test file: sorted [(line, pattern)]. Heuristic, not a parser: it reads
    test/it blocks only, and regex literals or nested template `${}` strings can confuse the bracket matching."""
    code, bare = _scrub(src)
    hits = []
    for m in JS_TEST.finditer(bare):
        mods, o = m.group(2), m.end() - 1
        c = _close(bare, o)
        if c < 0 or ".todo" in mods:
            continue
        if ".each" in mods:  # test.each(table)(name, fn)
            o = bare.find("(", c + 1)
            c = _close(bare, o) if o > 0 and not bare[c + 1:o].strip() else -1
            if c < 0:
                continue

        def hit(off, msg):
            hits.append((src.count("\n", 0, off) + 1, msg))
        if m.group(1).startswith("x") or ".skip" in mods:
            hit(m.start(), "skipped test body")
            continue
        fn = _js_body(bare, o, c)
        if not fn or fn[1] < 0:
            continue
        lo, hi, expr = fn
        done = re.search(r"\bdone\b", bare[o:lo]) is not None or re.search(r"\bdone\s*\(", bare[lo:hi]) is not None
        pos = [x.start() for x in JS_ASSERTY.finditer(bare, lo, hi)]
        if not pos:
            hit(m.start(), "no expect/assert in test body")
        else:
            cbs = _js_callbacks(bare, lo, hi)
            late = [p for p in pos if any(s <= p < e and cl not in JS_SYNC for s, e, cl in cbs)]
            if len(late) == len(pos) and not expr and not done and not re.search(r"\b(?:await|return)\b", bare[lo:hi]):
                hit(late[0], "assertions only inside a callback that is never awaited, returned or signalled")
        for x in JS_SELF.finditer(code, lo, hi):
            hit(x.start(), "expect() compares a value to itself or a constant")
        for x in re.finditer(r"\bexpect\s*\(", bare[lo:hi]):
            q = lo + x.end() - 1
            e = _close(bare, q)
            if e > 0 and re.match(r"\s*(.?)", bare[e + 1:]).group(1) != ".":
                hit(q, "expect() with no matcher")
        for x in re.finditer(r"\btry\s*\{", bare[lo:hi]):
            t0 = lo + x.end() - 1
            t1 = _close(bare, t0)
            cm = re.match(r"\s*catch\s*(?:\([^)]*\))?\s*\{", bare[t1 + 1:]) if t1 > 0 else None
            if cm and JS_ASSERTY.search(bare, t0, t1):
                c0 = t1 + cm.end()
                if not re.search(r"\b(?:throw|expect|assert\w*|fail|done|reject)\b", bare[c0:_close(bare, c0)]):
                    hit(t0, "assertion inside try whose catch swallows the failure")
        for x in JS_MOCK.finditer(bare, lo, hi):
            n, rest = re.escape(x.group(1)), bare[x.end():hi]
            calls = len(re.findall(r"(?<![\w$.])" + n + r"\s*\(", rest))
            exps = len(re.findall(r"expect\(\s*" + n + r"\s*\)", rest))
            if calls and exps and len(re.findall(r"(?<![\w$.])" + n + r"(?![\w$])", rest)) == calls + exps:
                hit(x.start(), f"mock '{x.group(1)}' is called by the test and then asserted on (checks itself)")
    return sorted(set(hits))


def static_check(path):
    """[(status, where, why)] for one source file: VACUOUS per `path:line`, COULD_NOT_CHECK if it will not parse.
    Missing files and other languages yield nothing (the report check covers them)."""
    py = path.endswith(".py")
    if not (py or path.endswith(JS_EXT)) or not os.path.isfile(path):
        return []
    try:
        src = open(path, encoding="utf-8").read()
        hits = py_static(src) if py else js_static(src)
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError, RecursionError, IndexError) as e:
        return [("COULD_NOT_CHECK", path, f"static pass failed: {type(e).__name__}")]
    return [("VACUOUS", f"{path}:{ln}", why) for ln, why in hits]


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
    # static pass: each planted vacuous pattern is caught; each genuine twin is clean
    pys = {
        "no assertion": "def test_a():\n    add(1, 2)\n",
        "constant assert": "def test_a():\n    assert True\n",
        "tuple": "def test_a():\n    assert (f() == 1, 'msg')\n",
        "tautology": "def test_a():\n    x = 1\n    assert x == x\n",
        "checks itself": "def test_a():\n    m = Mock()\n    m('x')\n    m.assert_called_once()\n",
        "swallows": "def test_a():\n    try:\n        assert f() == 1\n    except AssertionError:\n        pass\n",
        "early return": "def test_a():\n    if not ENV:\n        return\n    assert f()\n",
        "never called": "def test_a():\n    def chk():\n        assert f()\n",
        "skipped": "@pytest.mark.skip\ndef test_a():\n    assert f()\n",
    }
    for want, src in pys.items():
        assert any(want in w for _, w in py_static(src)), want
    for ok in ("def test_a():\n    assert f() == 1\n", "def test_a():\n    m = Mock()\n    run(m)\n    m.assert_called()\n",
               "def test_a():\n    try:\n        f()\n    except ValueError as e:\n        assert 'x' in str(e)\n    else:\n        pytest.fail('no')\n",
               "def chk(x):\n    assert x\n\ndef test_a():\n    chk(f())\n", "def helper():\n    pass\n"):
        assert py_static(ok) == [], ok
    jss = {
        "no expect": "test('a', () => { add(1, 2); });\n",
        "itself": "it('a', () => { expect(true).toBe(true); });\n",
        "no matcher": "it('a', () => { expect(add(1, 2)); });\n",
        "checks itself": "it('a', () => { const f = jest.fn(); f(1); expect(f).toHaveBeenCalled(); });\n",
        "swallows": "it('a', () => { try { expect(f()).toBe(1); } catch (e) { } });\n",
        "never awaited": "it('a', () => { f().then((r) => expect(r).toBe(1)); });\n",
        "skipped": "test.skip('a', () => { expect(f()).toBe(1); });\n",
    }
    for want, src in jss.items():
        assert any(want in w for _, w in js_static(src)), want
    for ok in ("it('a', async () => { await expect(f()).rejects.toThrow('x'); });\n",
               "it('a', (done) => { f((m) => { expect(m).toBe(1); done(); }); });\n",
               "it('a', () => { return f().then((r) => expect(r).toBe(1)); });\n",
               "it('a', () => { [1].forEach((x) => { expect(x).toBe(1); }); });\n",
               "it('a', () => { const f = jest.fn(); run(f); expect(f).toHaveBeenCalled(); });\n",
               "it.todo('a');\n// it('b', () => {});\n"):
        assert js_static(ok) == [], ok
    with tempfile.TemporaryDirectory() as t:  # wiring: static-only run (no REPORT) exits 1 on a vacuous file, 3 on unparseable
        bad, ok_, junk = (os.path.join(t, n) for n in ("test_bad.py", "test_ok.py", "test_junk.py"))
        open(bad, "w").write(pys["no assertion"])
        open(ok_, "w").write("def test_a():\n    assert 1 + 1 == 2\n")
        open(junk, "w").write("def (:\n")
        me = [sys.executable, os.path.abspath(__file__), "--changed"]
        rc = lambda *p: subprocess.run(me + list(p), capture_output=True).returncode
        assert (rc(ok_), rc(bad), rc(junk)) == (0, 1, 3)
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
    if (a.changed is None) == (a.base is None):
        ap.error("need exactly one of --changed / --base (REPORT optional: omit for the static check only)")
    paths = a.changed
    if a.base:
        o = subprocess.run(["git", "diff", "-z", "--name-only", "--diff-filter=ACMR", f"{a.base}...HEAD"],
                           capture_output=True)
        if o.returncode:
            print(f"COULD_NOT_CHECK: git diff failed: {o.stderr.decode(errors='replace').strip()}")
            return 3
        paths = [p for p in o.stdout.decode("utf-8", "surrogateescape").split("\0") if p and is_test_file(p)]
    res = [r for p in paths for r in static_check(p)]
    if a.report:
        try:
            text = open(a.report, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            text = f"<!DOCTYPE unreadable {type(e).__name__}"  # forces the COULD_NOT_CHECK path
        ls = subprocess.run(["git", "ls-files", "-z"], capture_output=True)
        files = ls.stdout.decode("utf-8", "surrogateescape").split("\0") if ls.returncode == 0 else []
        res += check(text, paths, files)
    for s, p, why in res:
        print(f"{s} {p}: {why}")
    st = {s for s, _, _ in res}
    return 1 if st & {"FAIL", "VACUOUS"} else 3 if "COULD_NOT_CHECK" in st else 0


if __name__ == "__main__":
    sys.exit(main())
