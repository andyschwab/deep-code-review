#!/usr/bin/env python3
"""partition_diff.py - split a unified diff into whole-file review chunks, deterministically.

A big diff hides bugs from a single review pass; reviewing it in file-sized chunks restores recall.
This script only does the split, so any agent or orchestrator can fan out over the chunks.

Usage:
  partition_diff.py [--diff FILE | --base REF] [--max-lines N] [--split-hunks]
                    [--skip-glob GLOB ...] [--out-dir DIR]
  partition_diff.py --selftest

Input: a unified diff from --diff FILE, stdin, or --base REF (runs `git diff REF...HEAD`, renames off).
Files stay whole and in original order. Consecutive files pack into chunks of at most --max-lines changed
lines (added + removed, headers not counted, default 150). One file over the limit is its own chunk;
with --split-hunks its hunks are packed instead (file header repeated, each chunk a valid patch).
Binary files, lockfiles, minified/map and generated files are never dropped silently: they go in the
manifest `skipped` array with a reason. --skip-glob (repeatable) REPLACES the default skip globs; `*` stops at `/`, `**` crosses it.

Output: manifest JSON on stdout {total_changed_lines, chunks:[{id, file, files, changed_lines}],
skipped:[{path, reason, changed_lines}]}. With --out-dir, also writes chunk-001.patch... and manifest.json
(refuses a non-empty dir unless --force; manifest written last). Concatenating the chunk patches reproduces every
non-skipped file diff byte for byte (CRLF kept). `partition: not needed` goes to stderr when everything
fits in one chunk. Exit 0 ok, 2 on bad input/usage (one stderr line, never a traceback).
"""
import argparse
import fnmatch
import io
import json
import os
import re
import subprocess
import sys
import tempfile

DEFAULT_SKIP = [(n, "lockfile") for n in (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "go.sum",
    "composer.lock", "Gemfile.lock")] + [
    ("*.min.js", "minified"), ("*.min.css", "minified"), ("*.map", "minified"),
    ("*.pb.go", "generated"), ("*_pb2.py", "generated")]
# header lines git may emit between `diff --git` and the first hunk; anything else is malformed
HDR_OK = (b"index ", b"old mode ", b"new mode ", b"deleted file mode ", b"new file mode ", b"similarity index ",
          b"dissimilarity index ", b"rename from ", b"rename to ", b"copy from ", b"copy to ", b"--- ", b"+++ ")
HUNK = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class Bad(Exception):
    pass


def _unq(tok):
    if len(tok) >= 2 and tok[:1] == b'"' and tok[-1:] == b'"':
        esc = {b"n": b"\n", b"t": b"\t", b'"': b'"', b"\\": b"\\"}
        return re.sub(rb"\\([0-7]{3}|.)", lambda m: bytes([int(m.group(1), 8)]) if len(m.group(1)) == 3
                      else esc.get(m.group(1), m.group(1)), tok[1:-1])
    return tok


def _strip(p):
    return p[2:] if p[:2] in (b"a/", b"b/") else p


def _path(header):
    """File path from header lines: rename to > +++ > --- > the diff --git line."""
    for pre in (b"rename to ", b"copy to ", b"+++ ", b"--- "):
        for ln in header[1:]:
            if ln.startswith(pre):
                v = ln[len(pre):].rstrip(b"\r\n").rstrip(b"\t")
                if v == b"/dev/null":
                    continue
                return _strip(_unq(v)) if pre[:1] not in (b"r", b"c") else _unq(v)
    rest = header[0][len(b"diff --git "):].rstrip(b"\r\n")
    if rest[:1] == b'"':
        j = 1
        while j < len(rest) and rest[j:j + 1] != b'"':
            j += 2 if rest[j:j + 1] == b"\\" else 1
        second = rest[j + 2:]
    elif rest[-1:] == b'"':
        second = rest[rest.rfind(b' "') + 1:]
    elif len(rest) % 2 == 1:
        second = rest[len(rest) // 2 + 1:]
    else:
        second = rest[rest.rfind(b" b/") + 1:]
    if not second:
        raise Bad("cannot read path from: " + rest.decode("utf-8", "replace"))
    return _strip(_unq(second))


def parse(data):
    """Bytes -> ordered units {path, header, hunks:[(bytes, changed)], binary, raw, changed}."""
    lines = io.BytesIO(data).readlines()  # splits on \n only, so CRLF stays attached
    units, i, n = [], 0, len(lines)
    if n and not lines[0].startswith(b"diff --git "):
        raise Bad("not a unified diff (expected 'diff --git' at line 1)")
    while i < n:
        start = i
        header = [lines[i]]
        i += 1
        binary = False
        while i < n and not lines[i].startswith((b"@@", b"diff --git ")):
            ln = lines[i]
            if ln.startswith((b"Binary files ", b"GIT binary patch")):
                binary = True
            elif binary and ln.startswith(b"diff --"):
                raise Bad("unsupported diff format at line %d" % (i + 1))
            elif not binary and not ln.startswith(HDR_OK):
                raise Bad("unrecognized line %d in file header" % (i + 1))
            header.append(ln)
            i += 1
        hunks = []
        while i < n and lines[i].startswith(b"@@") and not binary:
            m = HUNK.match(lines[i])
            if not m:
                raise Bad("bad hunk header at line %d" % (i + 1))
            old = int(m.group(2) if m.group(2) is not None else 1)
            new = int(m.group(4) if m.group(4) is not None else 1)
            hs, ch = i, 0
            i += 1
            while old > 0 or new > 0:
                if i >= n:
                    raise Bad("truncated hunk at end of input")
                c = lines[i][:1]
                if c in (b" ", b"\n", b"\r"):
                    old, new = old - 1, new - 1
                elif c == b"-":
                    old, ch = old - 1, ch + 1
                elif c == b"+":
                    new, ch = new - 1, ch + 1
                elif c != b"\\":
                    raise Bad("bad hunk body at line %d" % (i + 1))
                i += 1
            if old < 0 or new < 0:
                raise Bad("hunk line counts overrun at line %d" % i)
            while i < n and lines[i].startswith(b"\\"):
                i += 1
            hunks.append((b"".join(lines[hs:i]), ch))
        if binary:
            pass
        elif i < n and not lines[i].startswith(b"diff --git "):
            raise Bad("unexpected line %d after hunk" % (i + 1))
        units.append({"path": _path(header).decode("utf-8", "surrogateescape"), "header": b"".join(header),
                      "hunks": hunks, "binary": binary, "raw": b"".join(lines[start:i]),
                      "changed": sum(h[1] for h in hunks)})
    return units


def _rx(g):
    """Glob -> regex: `*` and `?` stop at `/`; `**` crosses it."""
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif g.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            out += {"*": "[^/]*", "?": "[^/]"}.get(g[i]) or re.escape(g[i])
            i += 1
    return re.compile(out + r"\Z", re.S)


def _skip_reason(u, globs):
    if u["binary"]:
        return "binary"
    for g, why in globs:  # a glob without `/` matches the basename, otherwise the whole path
        if _rx(g).match(u["path"] if "/" in g else u["path"].rsplit("/", 1)[-1]):
            return why
    return None


def _pack(items, limit):
    """items: [(path, bytes, changed)] -> greedy consecutive chunks; an oversize item stands alone."""
    out, cur, cl = [], [], 0
    for it in items:
        if cur and cl + it[2] > limit:
            out.append(cur)
            cur, cl = [], 0
        cur.append(it)
        cl += it[2]
    if cur:
        out.append(cur)
    return out


def partition(data, limit, split_hunks=False, globs=None):
    """Return (manifest, [patch bytes]). globs: [(glob, reason)], default DEFAULT_SKIP."""
    globs = DEFAULT_SKIP if globs is None else globs
    units, skipped, keep = parse(data), [], []
    for u in units:
        why = _skip_reason(u, globs)
        if why:
            skipped.append({"path": u["path"], "reason": why, "changed_lines": u["changed"]})
        else:
            keep.append(u)
    items = []
    for u in keep:
        if split_hunks and u["changed"] > limit and len(u["hunks"]) > 1:
            # ponytail: a single hunk over the limit stays whole; split it by hand if that matters
            for grp in _pack([(u["path"], h, c) for h, c in u["hunks"]], limit):
                items.append((u["path"], u["header"] + b"".join(g[1] for g in grp), sum(g[2] for g in grp)))
        else:
            items.append((u["path"], u["raw"], u["changed"]))
    chunks, patches = [], []
    for k, grp in enumerate(_pack(items, limit), 1):
        files = []
        for it in grp:
            if it[0] not in files:
                files.append(it[0])
        chunks.append({"id": "chunk-%03d" % k, "file": files[0], "files": files,
                       "changed_lines": sum(g[2] for g in grp)})
        patches.append(b"".join(g[1] for g in grp))
    total = sum(u["changed"] for u in units)
    return {"total_changed_lines": total, "chunks": chunks, "skipped": skipped}, patches


def _git_diff(ref):
    if not ref or ref.startswith("-"):
        raise Bad("bad --base ref: " + ref)
    p = subprocess.run(["git", "diff", "--no-renames", "--no-color", "--no-ext-diff", "--no-textconv", "--src-prefix=a/",
                        "--dst-prefix=b/", ref + "...HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise Bad("git diff failed: " + (p.stderr.decode("utf-8", "replace").strip().splitlines() or ["?"])[0])
    return p.stdout


def run(args):
    if args.base is not None:
        data = _git_diff(args.base)
        if not data:
            print("partition_diff: no changes against " + args.base, file=sys.stderr)
    elif args.diff:
        with open(args.diff, "rb") as f:
            data = f.read()
    else:
        data = sys.stdin.buffer.read()
    if args.max_lines < 1:
        raise Bad("--max-lines must be >= 1")
    globs = DEFAULT_SKIP if args.skip_glob is None else [(g, "skip-glob") for g in args.skip_glob]
    man, patches = partition(data, args.max_lines, args.split_hunks, globs)
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        if os.listdir(args.out_dir) and not args.force:
            raise Bad("--out-dir is not empty (use --force to overwrite): " + args.out_dir)
        for c, p in zip(man["chunks"], patches):
            with open(os.path.join(args.out_dir, c["id"] + ".patch"), "wb") as f:
                f.write(p)
        tmp = os.path.join(args.out_dir, "manifest.json.tmp")
        with open(tmp, "w") as f:
            json.dump(man, f, indent=2)
        os.replace(tmp, os.path.join(args.out_dir, "manifest.json"))
    sk = [x for x in man["skipped"] if x["changed_lines"]]
    if sk:
        print("partition_diff: WARN: skipped %d files with %d changed lines: review them separately"
              % (len(sk), sum(x["changed_lines"] for x in sk)), file=sys.stderr)
    print(json.dumps(man, indent=2))
    if sum(c["changed_lines"] for c in man["chunks"]) <= args.max_lines and man["chunks"]:
        print("partition: not needed", file=sys.stderr)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("partition_diff: " + message, file=sys.stderr)
        sys.exit(2)


def main(argv=None):
    ap = _Parser(description=__doc__.split("\n")[0])
    ap.add_argument("--diff")
    ap.add_argument("--base")
    ap.add_argument("--max-lines", type=int, default=150)
    ap.add_argument("--split-hunks", action="store_true")
    ap.add_argument("--skip-glob", action="append")
    ap.add_argument("--out-dir")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    if args.selftest:
        return selftest()
    try:
        run(args)
        return 0
    except Exception as e:  # one line, never a traceback
        print("partition_diff: " + (str(e).splitlines() or [type(e).__name__])[0], file=sys.stderr)
        return 2


# ---------------------------------------------------------------- selftest
def _file(path, lines, hdr_extra=b""):
    body = b"".join(lines)
    adds = sum(1 for x in lines if x[:1] == b"+")
    dels = sum(1 for x in lines if x[:1] == b"-")
    ctx = sum(1 for x in lines if x[:1] == b" ")
    h = b"diff --git a/%s b/%s\n%s--- a/%s\n+++ b/%s\n@@ -1,%d +1,%d @@\n" % (
        path, path, hdr_extra, path, path, dels + ctx, adds + ctx)
    return h + body, adds + dels


def _cli(*a, stdin=b""):
    p = subprocess.run([sys.executable, os.path.abspath(__file__)] + list(a), input=stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout, p.stderr


def selftest():
    ok = []

    def check(cond, msg):
        if not cond:
            print("FAIL: " + msg)
            sys.exit(1)
        ok.append(msg)

    # fixture: ordered (path, bytes, changed, skipped?)
    names = [b"a.py", b"sp ace/b c.py", "éè.txt".encode(), b"crlf.txt", b"yarn.lock", b"app.min.js", b"z.py"]
    pieces = [
        (names[0],) + _file(names[0], [b" ctx\n", b"-old\n", b"+new\n", b"+new2\n"]),
        (names[1],) + _file(names[1], [b"+x\n", b"+y\n"]),
        (names[2], b"", 2),
        (names[3],) + _file(names[3], [b" keep\r\n", b"-a\r\n", b"+b\r\n", b"\\ No newline at end of file\n"]),
        (names[4],) + _file(names[4], [b"+lock\n"] * 40),
        (names[5],) + _file(names[5], [b"+min\n"] * 5),
        (names[6],) + _file(names[6], [b"+z\n"] * 6),
    ]
    # git quotes non-ASCII paths (core.quotepath=on)
    pieces[2] = (names[2], b'diff --git "a/\\303\\251\\303\\250.txt" "b/\\303\\251\\303\\250.txt"\n'
                 b'--- "a/\\303\\251\\303\\250.txt"\n+++ "b/\\303\\251\\303\\250.txt"\n@@ -1 +1 @@\n-u\n+v\n', 2)
    pieces.insert(3, (b"bin.dat", b"diff --git a/bin.dat b/bin.dat\nindex 1..2 100644\n"
                      b"Binary files a/bin.dat and b/bin.dat differ\n", 0))
    pieces.insert(1, (b"mode.sh", b"diff --git a/mode.sh b/mode.sh\nold mode 100644\nnew mode 100755\n", 0))
    pieces.insert(2, (b"new.txt", b"diff --git a/new.txt b/new.txt\nnew file mode 100644\n--- /dev/null\n"
                      b"+++ b/new.txt\n@@ -0,0 +1,2 @@\n+n1\n+n2\n", 2))
    skip_names = {b"yarn.lock", b"app.min.js", b"bin.dat"}
    data = b"".join(p[1] for p in pieces)
    total = sum(p[2] for p in pieces)
    kept = b"".join(p[1] for p in pieces if p[0] not in skip_names)
    kept_n = sum(p[2] for p in pieces if p[0] not in skip_names)

    for lim in (1, 3, 5, 8, 12, 1000):
        man, pat = partition(data, lim)
        check(b"".join(pat) == kept, "limit %d: chunks reproduce non-skipped diffs byte for byte" % lim)
        check(sum(c["changed_lines"] for c in man["chunks"]) == kept_n and
              kept_n + sum(s["changed_lines"] for s in man["skipped"]) == total == man["total_changed_lines"],
              "limit %d: every changed line in exactly one chunk or skipped" % lim)
        check(all(c["changed_lines"] <= lim or len(c["files"]) == 1 for c in man["chunks"]),
              "limit %d: only single-file chunks exceed the limit" % lim)
    man, _ = partition(data, 1000)
    check(len(man["chunks"]) == 1 and {s["path"]: s["reason"] for s in man["skipped"]} ==
          {"yarn.lock": "lockfile", "app.min.js": "minified", "bin.dat": "binary"}, "skipped reasons + one chunk")
    check(man["chunks"][0]["files"][:3] == ["a.py", "mode.sh", "new.txt"], "original order kept")
    check("sp ace/b c.py" in man["chunks"][0]["files"] and "éè.txt" in man["chunks"][0]["files"],
          "spaces, quoted unicode paths parse")
    man, _ = partition(data, 1000, globs=[("*.py", "skip-glob")])
    check({s["reason"] for s in man["skipped"]} == {"skip-glob", "binary"}, "--skip-glob replaces defaults")
    man, pat = partition(data, 3)
    check(b"\r\n" in b"".join(pat) and b"b\r\n" in kept, "CRLF preserved")
    # rename diff parses (rename to wins)
    rn = b"diff --git a/o ld.txt b/n ew.txt\nsimilarity index 100%\nrename from o ld.txt\nrename to n ew.txt\n"
    check(partition(rn, 5)[0]["chunks"][0]["file"] == "n ew.txt", "rename parses")

    # split-hunks: big file, 3 hunks of 4 changes each
    hk = b"".join(b"@@ -%d +%d @@\n-a\n+b\n" % (k * 10 + 1, k * 10 + 1) for k in range(6))
    big = b"diff --git a/big.py b/big.py\n--- a/big.py\n+++ b/big.py\n" + hk
    man, pat = partition(big, 5)
    check(len(man["chunks"]) == 1 and man["chunks"][0]["changed_lines"] == 12, "no split-hunks: big file whole")
    man, pat = partition(big, 5, split_hunks=True)
    hdr = big[:big.index(b"@@")]
    check(len(pat) == 3 and all(p.startswith(hdr) for p in pat) and
          b"".join(p[len(hdr):] for p in pat) == hk, "split-hunks repeats header, hunks intact")
    check(all(partition(p, 5)[0]["total_changed_lines"] == c["changed_lines"] for p, c in zip(pat, man["chunks"])),
          "split-hunks chunks re-parse as valid patches")

    # CLI behaviour
    rc, out, err = _cli(stdin=b"")
    check(rc == 0 and json.loads(out)["chunks"] == [], "empty diff: exit 0, zero chunks")
    rc, out, err = _cli("--max-lines", "100", stdin=big)
    check(rc == 0 and b"partition: not needed" in err and len(json.loads(out)["chunks"]) == 1, "not needed message")
    for bad in (b"hello\n", b"diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,3 +1,3 @@\n a\n",
                b"diff --git a/x b/x\n@@ nope\n", b"diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\njunk\n"):
        rc, out, err = _cli(stdin=bad)
        check(rc == 2 and out == b"" and len(err.splitlines()) == 1 and b"Traceback" not in err,
              "malformed exit 2 one line: %r" % bad[:20])
    rc, _, err = _cli("--diff", "/nonexistent/x.patch")
    check(rc == 2 and len(err.splitlines()) == 1 and b"Traceback" not in err, "missing --diff file exit 2")
    rc, _, err = _cli("--base", "")
    check(rc == 2 and len(err.splitlines()) == 1, '--base "" rejected')
    rc, _, err = _cli("--base=--evil")
    check(rc == 2 and len(err.splitlines()) == 1, "option-like --base rejected")
    for bad in (b"diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\ndiff --cc x\n",
                b"diff --git a/x b/x\ndiff --combined y\n@@@ -1 -1 +1 @@@\n",
                b"diff --git a/x b/x\nrandom junk\n--- a/x\n"):
        rc, out, err = _cli(stdin=bad)
        check(rc == 2 and len(err.splitlines()) == 1, "hostile junk/combined diff exit 2: %r" % bad[-12:])
    host = (b"diff --git a/h.txt b/h.txt\n--- a/h.txt\n+++ b/h.txt\n@@ -1,3 +1,4 @@\n--- foo\n+++ bar\n"
            b"+diff --git x\n ctx\n-diff --cc\n+diff --cc2\n")
    hm = partition(host, 100)[0]
    check(hm["total_changed_lines"] == 5 and len(hm["chunks"]) == 1, "hunk bodies that look like headers stay in the hunk")
    gb = (b"diff --git a/b.bin b/b.bin\nnew file mode 100644\nindex 0..1\nGIT binary patch\nliteral 5\nHcmZ?b\n\n"
          b"diff --git a/ok.py b/ok.py\n--- a/ok.py\n+++ b/ok.py\n@@ -1 +1 @@\n-a\n+b\n")
    gm = partition(gb, 100)[0]
    check(gm["skipped"][0]["reason"] == "binary" and gm["chunks"][0]["files"] == ["ok.py"], "GIT binary patch block skipped")
    cp = (b"diff --git a/o.txt b/c p.txt\nsimilarity index 100%\ncopy from o.txt\ncopy to c p.txt\n"
          b"diff --git a/r.txt b/r2.txt\nsimilarity index 100%\nrename from r.txt\nrename to r2.txt\n")
    check(partition(cp, 5)[0]["chunks"][0]["files"] == ["c p.txt", "r2.txt"], "copy/rename without hunks")
    sg = (b"diff --git a/src/x.min.js b/src/x.min.js\n--- a/src/x.min.js\n+++ b/src/x.min.js\n@@ -1 +1 @@\n-a\n+b\n"
          b"diff --git a/pkg/gen/y.py b/pkg/gen/y.py\n--- a/pkg/gen/y.py\n+++ b/pkg/gen/y.py\n@@ -1 +1 @@\n-a\n+b\n"
          b"diff --git a/generated/z.py b/generated/z.py\n--- a/generated/z.py\n+++ b/generated/z.py\n@@ -1 +1 @@\n-a\n+b\n")
    check([s["path"] for s in partition(sg, 9)[0]["skipped"]] == ["src/x.min.js"], "generated/ dir not skipped by default")
    for g, hit in (("pkg/*.py", 0), ("pkg/**.py", 1), ("**/y.py", 1), ("pkg/*/y.py", 1), ("y.py", 1)):
        check(bool(partition(sg, 9, globs=[(g, "skip-glob")])[0]["skipped"] and any(
            s["path"] == "pkg/gen/y.py" for s in partition(sg, 9, globs=[(g, "skip-glob")])[0]["skipped"])) == bool(hit),
              "skip-glob %s crossing" % g)
    rc, _, err = _cli("--skip-glob", "*.py", stdin=sg)
    check(rc == 0 and b"WARN: skipped 2 files with 4 changed lines" in err, "WARN line for skipped changed lines")
    rc, _, err = _cli("--max-lines", "0", stdin=big)
    check(rc == 2 and len(err.splitlines()) == 1, "--max-lines 0 rejected")

    with tempfile.TemporaryDirectory() as td:
        od = os.path.join(td, "out")
        rc, out, _ = _cli("--max-lines", "5", "--out-dir", od, stdin=data)
        man = json.loads(out)
        files = sorted(os.listdir(od))
        got = b"".join(open(os.path.join(od, c["id"] + ".patch"), "rb").read() for c in man["chunks"])
        check(rc == 0 and got == kept and files[-1] == "manifest.json" and files[0] == "chunk-001.patch" and
              json.load(open(os.path.join(od, "manifest.json"))) == man, "--out-dir writes chunks + manifest")
        rc, _, err = _cli("--out-dir", od, stdin=data)
        check(rc == 2 and len(err.splitlines()) == 1, "--out-dir refuses a non-empty directory")
        rc, _, err = _cli("--out-dir", od, "--force", stdin=data)
        check(rc == 0 and not os.path.exists(os.path.join(od, "manifest.json.tmp")), "--force overwrites, no temp left")

        # --base against a real repo: odd names, binary, lockfile, CRLF, renames off
        def git(*a):
            subprocess.run(["git", "-C", td] + list(a), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def w(name, b):
            with open(os.path.join(td, name), "wb") as f:
                f.write(b)
        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        w("seed", b"s\n")
        w("old name.txt", b"keep\nthis\nline\nstays\nsame\nhere\nok\n")
        git("add", "-A")
        git("commit", "-qm", "base")
        git("branch", "base0")
        git("mv", "old name.txt", "new name.txt")
        w("q\"t.txt", b"1\n2\n")
        w("ü.txt", b"x\r\ny\r\n")
        w("bin.dat", b"\x00\x01\x02")
        w("Cargo.lock", b"l\n" * 9)
        w("sp ace.py", b"p\n" * 4)
        git("add", "-A")
        git("commit", "-qm", "change")
        cwd = os.getcwd()
        os.chdir(td)
        try:
            rc, out, err = _cli("--base", "base0", "--max-lines", "3")
            raw = subprocess.run(["git", "diff", "--no-renames", "base0...HEAD"], stdout=subprocess.PIPE).stdout
        finally:
            os.chdir(cwd)
        man = json.loads(out)
        paths = [f for c in man["chunks"] for f in c["files"]] + [s["path"] for s in man["skipped"]]
        check(rc == 0 and sorted(paths) == sorted(["new name.txt", "old name.txt", 'q"t.txt', "ü.txt",
                                                    "bin.dat", "Cargo.lock", "sp ace.py"]),
              "--base real repo: every file in a chunk or skipped (rename = delete+add)")
        ns = subprocess.run(["git", "-C", td, "diff", "--no-renames", "--numstat", "base0...HEAD"],
                            stdout=subprocess.PIPE).stdout.split(b"\n")
        want = sum(int(x.split(b"\t")[0]) + int(x.split(b"\t")[1]) for x in ns if x and x[:1] != b"-")
        check(man["total_changed_lines"] == want, "--base total matches git numstat")
    print("PASS: partition_diff selftest (%d checks)" % len(ok))
    return 0


if __name__ == "__main__":
    sys.exit(main())
