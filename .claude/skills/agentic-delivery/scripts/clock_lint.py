#!/usr/bin/env python3
"""clock_lint.py [--base REF [--head REF]] [--root DIR] [FILES...] | --selftest -- flag tests that read the real clock.

WHY: tests that read the real clock or timezone pass for weeks, then turn the development branch red at a
week, month or DST rollover. Flagged reads: py `datetime/dt/timezone/arrow/pendulum .now/.utcnow/.today`,
`date.today`, `time.time` (and `import ... as` aliases); js/ts `Date.now()`, `new Date()` with no args,
`moment()`/`dayjs()` with no args, `DateTime.now()`; go `time.Now()` (and an aliased time import); sh `date`
(a `-d`/`-r` date that is not relative to now is deterministic and allowed). Not flagged: elapsed-time
deltas (`t - start`, `start = time.time()`, `time.Since`), `perf_counter`/`monotonic`, text in strings or
comments.
A read is exempt only where a REAL fake clock is in scope: freezegun/freeze_time, time_machine, libfaketime/
faketime, jest/vi `useFakeTimers`/`setSystemTime`, MockDate, or a `now=`/`clock=` keyword argument that is not
itself a real read. Scope is the enclosing test function/block; a marker in the file preamble (not a bare
import), a fixture/setUp/beforeEach/describe block, or `TestMain` covers the whole file.
Files: explicit FILES (a non-test path prints `SKIP file: not a test file`), else changed vs `--base REF`
(git diff REF...HEAD or REF...--head, added/modified, paths resolved from the repo top), else every tracked
file. Test files: test_*.py, *_test.py, *.test.*/*.spec.* (js/ts/mjs/cjs), __tests__/, tests/, *_test.go,
test*.sh, *.bats.
Output: `file:line: real clock in test; pin a fake clock or inject now`. Escape: `clock-lint: allow` in a comment
on the same line or on a comment-only line above. Exit 0 clean, 1 findings, 2 COULD_NOT_CHECK (unreadable file
or git failure; printed, never silent; 2 only when there are no findings).
Limits: line regexes and indentation/keyword block detection, not a parser; a clock read built by string
concatenation is not seen; a fake clock anywhere in a test block exempts that whole block. Read-only.
"""
import os
import re
import subprocess
import sys

TEST_RE = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.(py|go)|[^/]*\.(test|spec)\.[cm]?[jt]sx?|test[^/]*\.sh|[^/]*\.bats"
                     r"|(__tests__|tests?)/[^/]*\.(py|[cm]?[jt]sx?|go|sh))$")
EXT = {"py": "py", "js": "js", "jsx": "js", "ts": "js", "tsx": "js", "mjs": "js", "cjs": "js", "mts": "js",
       "cts": "js", "go": "go", "sh": "sh", "bats": "sh"}
READS = {
    "py": r"\b(datetime|dt|timezone|arrow|pendulum)\.(now|utcnow|today)\s*\(|\bdate\.today\s*\(|\btime\.time(_ns)?\s*\(",
    "js": r"\bDate\.now\s*\(\s*\)|\bnew\s+Date\s*\(\s*\)|\b(moment|dayjs)\s*\(\s*\)|\bDateTime\.(now|local)\s*\(",
    "go": r"\btime\.Now\s*\(\s*\)",
    "sh": r"(^|[\s$(`;|&])date(?![\w-])(?!\s+(-d|--date=?|-r|--reference=?)\s*(?!now|yesterday|tomorrow|next|last|[+-]\d|\S*ago\b)\S)",
}
ELAPSED = re.compile(r"\b(start|t0|t1|tic|begin|before|started|deadline)\w*\s*(:=|=)\s*|\)\s*-|-\s*\w*\s*$|time\.Since")
FAKE = re.compile(r"freezegun|freeze_time|time_machine|time-machine|libfaketime|faketime|useFakeTimers|setSystemTime|"
                  r"[Mm]ock[Dd]ate|[(,]\s*(now|clock|now_fn|nowFn)\s*=(?!=)(?!\s*\w*\.?(datetime\.|dt\.)?(now|utcnow|today)\b)"
                  r"(?!\s*(time\.|Date\.now|new Date\(\s*\)))")
BLOCK = {  # block start (a decorator line also starts one for py)
    "py": r"^\s*(@|(async\s+)?def\s|class\s)", "js": r"^\s*(it|test|describe|beforeEach|beforeAll|afterEach|afterAll)\b",
    "go": r"^func\s", "sh": r"^\s*(function\s+\w+|\w+\s*\(\)\s*\{|@test\b)"}
GLOBAL = {  # block headers whose fake clock covers the file
    "py": r"fixture|\bdef\s+(setUp\w*|setup_?\w*|\w*conftest\w*)\b", "js": r"^\s*(describe|beforeEach|beforeAll)\b",
    "go": r"TestMain", "sh": r"\bsetup\b"}
IMPORT = re.compile(r"^\s*(import\b|from\s+\S+\s+import\b|.*\brequire\()")
ALLOW = "clock-lint: allow"
COMMENT = re.compile(r"^\s*(#|//|\*|/\*)")
MSG = "real clock in test; pin a fake clock or inject now"


def code(lang, line, st):
    """`line` without string literals and trailing comments; st = [in_triple_quote] for py docstrings."""
    if lang == "py":
        if line.count('"""') % 2 or line.count("'''") % 2:
            st[0] = not st[0]
            return ""
        if st[0]:
            return ""
    if lang == "sh":
        line = re.sub(r"(-d|--date=?|-r)\s*(['\"])([^'\"]*)\2", lambda m: m.group(1) + " " + m.group(3).replace(" ", "~"), line)
        line = re.sub(r"'[^']*'|\"(?![^\"]*(\$\(|`))[^\"]*\"", "''", line)
    else:
        line = re.sub(r"'(\\.|[^'\\])*'|\"(\\.|[^\"\\])*\"", "''", line)
    return re.split(r"\s#.*|^#.*" if lang in ("py", "sh") else r"\s//.*|^//.*", line)[0]


def aliases(lang, text):
    """Extra read regex for `import time as t` / `from datetime import datetime as d` (py) and `import t "time"` (go)."""
    if lang == "py":
        a = re.findall(r"import\s+time\s+as\s+(\w+)", text)
        b = re.findall(r"import\s+(?:datetime|date)\s+as\s+(\w+)", text)
        return [r"\b%s\.time(_ns)?\s*\(" % x for x in a] + [r"\b%s\.(now|utcnow|today)\s*\(" % x for x in b]
    if lang == "go":
        return [r"\b%s\.Now\s*\(\s*\)" % x for x in re.findall(r"^\s*import\s+(\w+)\s+\"time\"|^\s*(\w+)\s+\"time\"", text, re.M)
                for x in x if x]
    return []


def scan(path, text):
    """Return [(line_no, line)] of unpinned real-clock reads in `text`."""
    lang = EXT[path.rsplit(".", 1)[-1]]
    rx = re.compile("|".join([READS[lang]] + aliases(lang, text)))
    lines, st = text.split("\n"), [False]
    cl = [code(lang, l, st) for l in lines]
    starts = [i for i, l in enumerate(lines) if re.search(BLOCK[lang], l)]
    if lang == "py":  # a decorator run belongs to the def below it: drop starts that continue a decorator run
        starts = [i for i in starts if not (i and re.match(r"^\s*@", lines[i - 1]))]
    bounds = sorted(set([0] + starts + [len(lines)]))
    spans = list(zip(bounds, bounds[1:]))
    first = starts[0] if starts else len(lines)
    glob, ok = False, set()
    for k, (a, b) in enumerate(spans):
        if any(FAKE.search(cl[i]) and not IMPORT.match(lines[i]) for i in range(a, b)):
            ok.add(k)
            glob = glob or b <= first or bool(re.search(GLOBAL[lang], "\n".join(lines[a:min(b, a + 4)])))
    if glob:
        return []
    out = []
    for k, (a, b) in enumerate(spans):
        if k in ok:
            continue
        for i in range(a, b):
            if not rx.search(cl[i]) or ELAPSED.search(cl[i]) or COMMENT.match(lines[i]) or ALLOW in lines[i] \
                    or (i and ALLOW in lines[i - 1] and COMMENT.match(lines[i - 1])):
                continue
            out.append((i + 1, lines[i]))
    return out


def files(root, base, head, args):
    if args:
        return args
    top = root
    if base:
        p = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        top = p.stdout.strip() if not p.returncode else root
    cmd = ["diff", "--name-only", "--diff-filter=AM", "%s...%s" % (base, head)] if base else ["ls-files"]
    p = subprocess.run(["git", "-C", root, *cmd], capture_output=True, text=True)
    if p.returncode:
        raise OSError("git %s failed: %s" % (cmd[0], p.stderr.strip()))
    return [os.path.join(top, f) for f in p.stdout.split("\n") if f]


def run(root, base, args, head="HEAD"):
    bad = cant = 0
    try:
        paths = files(root, base, head, args)
    except OSError as e:
        print("COULD_NOT_CHECK %s" % e)
        return 2
    for f in paths:
        rel = f if args else os.path.relpath(os.path.realpath(f), os.path.realpath(root))
        if not TEST_RE.search(f.replace(os.sep, "/")) or f.rsplit(".", 1)[-1] not in EXT:
            if args:
                print("SKIP %s: not a test file" % f)
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            print("COULD_NOT_CHECK %s: %s" % (rel, e.strerror or e))
            cant += 1
            continue
        for n, _ in scan(f, text):
            print("%s:%d: %s" % (rel, n, MSG))
            bad += 1
    return 1 if bad else 2 if cant else 0


def selftest():
    cases = [
        ("test_a.py", "import datetime\nx = datetime.datetime.now()\n", 1),
        ("test_a.py", "now = datetime.now()\n", 1),
        ("test_a.py", "def test_x():\n    t = dt.now()\n", 1),
        ("test_a.py", "def test_x():\n    t = timezone.now()\n", 1),
        ("test_a.py", "import time as tm\ndef test_x():\n    a = tm.time()\n", 1),
        ("test_a.py", "from freezegun import freeze_time\nx = datetime.now()\n", 1),  # bare import is no marker
        ("test_a.py", "@freeze_time('2020-01-01')\ndef test_x():\n    datetime.now()\n", 0),
        ("test_a.py", "@freeze_time('2020-01-01')\ndef test_x():\n    datetime.now()\ndef test_y():\n    datetime.now()\n", 1),
        ("test_a.py", "pytestmark = freeze_time('2020-01-01')\ndef test_x():\n    datetime.now()\n", 0),
        ("test_a.py", "@pytest.fixture(autouse=True)\ndef clock():\n    with freeze_time('2020-01-01'):\n        yield\ndef test_x():\n    datetime.now()\n", 0),
        ("test_a.py", "@mock.patch('time.sleep')\ndef test_x(s):\n    datetime.now()\n", 1),
        ("test_a.py", "def test_x():\n    f(now=datetime.now())\n", 1),
        ("test_a.py", "def test_x():\n    f(now=FIXED)\n    datetime.now()\n", 0),
        ("test_a.py", "def test_x():\n    start = time.time()\n    e = time.time() - start\n    p = time.perf_counter()\n", 0),
        ("test_a.py", "def test_x():\n    s = 'datetime.now()'  # datetime.now()\n    \"\"\"\n    time.time()\n    \"\"\"\n", 0),
        ("test_c.py", "x = time.time()  # clock-lint: allow\ny = time.time()\n", 1),
        ("test_c.py", "# clock-lint: allow\ny = time.time()\n", 0),
        ("a.test.ts", "const t = Date.now();\nconst u = new Date('2020-01-01');\nconst v = new Date();\n", 2),
        ("a.test.mjs", "it('a', () => { moment(); });\n", 1),
        ("a.test.ts", "it('a', () => {\n  const start = Date.now();\n  const d = Date.now() - start;\n});\n", 0),
        ("b.spec.js", "beforeEach(() => { jest.useFakeTimers(); });\nit('a', () => { Date.now(); });\n", 0),
        ("b.spec.js", "it('a', () => { vi.setSystemTime(1); Date.now(); });\nit('b', () => { Date.now(); });\n", 1),
        ("b.spec.js", "it('a', () => { jest.advanceTimersByTime(1); Date.now(); });\n", 1),
        ("x_test.go", "func TestA(t *testing.T) {\n\tn := time.Now()\n\t// time.Now()\n}\n", 1),
        ("x_test.go", "import t \"time\"\nfunc TestA() {\n\tn := t.Now()\n}\n", 1),
        ("x_test.go", "func TestA() {\n\tstart := time.Now()\n\td := time.Since(start)\n}\n", 0),
        ("test-r.sh", "d=$(date +%F)\ne=$(date -d @0 +%F)\nf=$(date)\n", 2),
        ("test-r.sh", "e=$(date -d '2020-01-01' +%F)\ng=$(date -d 'yesterday' +%F)\necho \"date is fixed\"\n", 1),
        ("test-r.sh", "g=$(date -d '3 days ago' +%F)\nh=$(date -r 5 +%F)\n", 1),
        ("app.py", "datetime.now()\n", 0),
    ]
    for name, src, want in cases:
        got = len(scan(name, src)) if TEST_RE.search(name) else 0
        assert got == want, (name, src, got, want)
    print("clock_lint selftest ok")


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    root, base, head = ".", None, "HEAD"
    for opt in ("--root", "--base", "--head"):
        if opt in argv:
            i = argv.index(opt)
            if i + 1 >= len(argv):
                sys.exit("usage: clock_lint.py [--base REF [--head REF]] [--root DIR] [FILES...] | --selftest")
            v = argv[i + 1]
            del argv[i:i + 2]
            if opt == "--root": root = v
            elif opt == "--base": base = v
            else: head = v
    return run(root, base, argv, head)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
