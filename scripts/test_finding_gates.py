#!/usr/bin/env python3
"""Tests for finding_ground_check.py and merge_findings.py (plain asserts; exits non-zero on failure)."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(ROOT, ".claude", "skills", "deep-code-review", "scripts")
sys.path.insert(0, SD)
import finding_ground_check as g  # noqa: E402
import merge_findings as m  # noqa: E402

with tempfile.TemporaryDirectory() as t:
    os.makedirs(os.path.join(t, "src"))
    with open(os.path.join(t, "src", "a.py"), "w") as fh:
        fh.write("\n".join(f"code line {i}" for i in range(1, 31)) + "\n")

    def row(ev, snip="code line 10", **kw):
        return {"id": "F", "severity": "High", "title": "t", "evidence": [ev], "snippet": snip, **kw}

    def ck(r):
        return g.check(r, t)

    assert ck(row("src/a.py:10")) == (True, "ok")
    assert ck(row("src/a.py:10", "code   line   10"))[0], "whitespace-normalized"
    assert ck(row("src/a.py:14"))[0] and ck(row("src/a.py:5"))[0], "+-5 window"
    assert ck(row("src/a.py:20"))[1] == "snippet not within +-5 lines"
    assert ck(row("src/a.py:8-12", "code line 13"))[0], "range widens window"
    assert ck(row("src/a.py:99")) == (False, "line out of range")
    assert ck(row("src/a.py:0"))[1] == "line out of range"
    assert ck(row("src/nope.py:1")) == (False, "file not found")
    assert ck(row("../etc/passwd:1"))[1] == "path outside root"
    assert ck(row("/etc/passwd:1"))[1] == "path outside root"
    assert ck(row("src/a.py:10", ""))[1] == "no snippet quoted"
    assert ck(row("src/a.py:10", "e"))[1] == "snippet too short" and ck(row("src/a.py:10", "(")) [1] == "snippet too short"
    assert g.parse("a:1:2") == ("a:1", 2, 2) and g.parse("a:3-5") == ("a", 3, 5) and g.parse("a") is None

    # --ref reads the git tree, not the working tree
    subprocess.run("git init -q . && git add . && git -c user.name=t -c user.email=t@example.com commit -qm x", shell=True, cwd=t, check=True)
    with open(os.path.join(t, "src", "a.py"), "w") as fh:
        fh.write("changed\n")
    assert g.check(row("src/a.py:10"), t) == (False, "line out of range"), "working tree is the changed file"
    assert g.check(row("src/a.py:10"), t, "HEAD") == (True, "ok"), "--ref grounds against the commit"
    assert g.check(row("src/a.py:10"), t, "--output=x")[1] == "file not found", "option-like ref refused"
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=t, check=True)
    assert ck({"id": "F", "evidence": []})[1] == "no path:line evidence"
    assert ck(row("src"))[1] == "no path:line evidence"

    # CLI: annotates gap rows, leaves strengths alone, bad input exits 2
    p = os.path.join(t, "f.json")
    json.dump({"findings": [row("src/a.py:10"), {"id": "S", "polarity": "strength", "evidence": ["x:1"]}]}, open(p, "w"))
    r = subprocess.run([sys.executable, os.path.join(SD, "finding_ground_check.py"), p, "--root", t], capture_output=True, text=True)
    out = json.loads(r.stdout)["findings"]
    assert r.returncode == 0 and out[0]["grounded"] is True and "grounded" not in out[1]
    bad = subprocess.run([sys.executable, os.path.join(SD, "finding_ground_check.py"), os.path.join(t, "none.json")], capture_output=True, text=True)
    assert bad.returncode == 2

# merge re-checks grounding itself (a caller-supplied grounded flag is ignored), dedupes near same-file
# same-mechanism rows (keep highest sev, union evidence), ranks, caps
with tempfile.TemporaryDirectory() as t:
    for fn in ("db.py", "u.py", "other.py", "q.py", "a.py"):
        with open(os.path.join(t, fn), "w") as fh:
            fh.write("\n".join(f"code line {i}" for i in range(1, 1001)) + "\n")

    def G(ev, **k):
        return {"polarity": "gap", "snippet": "code line " + ev.split(":")[1], "evidence": [ev], **k}

    rows = [
        G("db.py:5", id="a", severity="Low", title="x", mechanism="sqli"),
        G("db.py:9", id="b", severity="Critical", title="y", mechanism="SQLi"),
        G("u.py:1", id="c", severity="Medium", title="Null deref"),
        G("u.py:7", id="d", severity="High", title="null  deref!"),
        G("other.py:1", id="e", severity="High", title="Null deref"),
        {**G("q.py:1", id="f", severity="Critical", title="z"), "snippet": "not in file at all"},
        {**G("q.py:2", id="g", severity="Critical", title="liar"), "snippet": "fabricated text", "grounded": True},
        {"id": "s", "polarity": "strength", "title": "good"},
    ]
    res = m.merge([dict(r) for r in rows], root=t)
    ids = [f["id"] for f in res["findings"]]
    assert ids == ["b", "d", "e", "s"], ids
    assert res["dropped"] == {"ungrounded": 2, "duplicate": 2, "over_cap": 0}, res["dropped"]
    assert res["findings"][0]["evidence"] == ["db.py:9", "db.py:5"]
    cap = m.merge([dict(r) for r in rows], cap=1, root=t)
    assert [f["id"] for f in cap["findings"]] == ["b", "s"] and cap["dropped"]["over_cap"] == 2
    assert m.merge([]) == {"findings": [], "dropped": {"ungrounded": 0, "duplicate": 0, "over_cap": 0}}, "NONE is valid"

    # far-apart same title stays 2; punctuation-only titles fall back to the id; equal severity keeps the first
    far = m.merge([G("a.py:1", id="n1", severity="High", title="Same"), G("a.py:900", id="n2", severity="High", title="Same")], root=t)
    assert [f["id"] for f in far["findings"]] == ["n1", "n2"] and far["dropped"]["duplicate"] == 0
    punct = m.merge([G("a.py:3", id="p1", severity="High", title="!!!"), G("a.py:4", id="p2", severity="High", title="???")], root=t)
    assert len(punct["findings"]) == 2 and punct["dropped"]["duplicate"] == 0
    tie = m.merge([G("a.py:5", id="t1", severity="High", title="Tie"), G("a.py:6", id="t2", severity="High", title="Tie")], root=t)
    assert [f["id"] for f in tie["findings"]] == ["t1"], "equal severity keeps the first row"
    # schema severities: Blocker ranks first, Nit last
    sv = m.merge([G("a.py:1", id="n", severity="Nit", title="n"), G("a.py:100", id="l", severity="Low", title="l"), G("a.py:200", id="b", severity="Blocker", title="b")], root=t)
    assert [f["id"] for f in sv["findings"]] == ["b", "l", "n"], sv
print("test_finding_gates: all passed")
