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
        fh.write("\n".join(f"line {i}" for i in range(1, 31)) + "\n")

    def row(ev, snip="line 10", **kw):
        return {"id": "F", "severity": "High", "title": "t", "evidence": [ev], "snippet": snip, **kw}

    def ck(r):
        return g.check(r, t)

    assert ck(row("src/a.py:10")) == (True, "ok")
    assert ck(row("src/a.py:10", "line   10"))[0], "whitespace-normalized"
    assert ck(row("src/a.py:14"))[0] and ck(row("src/a.py:5"))[0], "+-5 window"
    assert ck(row("src/a.py:20"))[1] == "snippet not within +-5 lines"
    assert ck(row("src/a.py:8-12", "line 13"))[0], "range widens window"
    assert ck(row("src/a.py:99")) == (False, "line out of range")
    assert ck(row("src/a.py:0"))[1] == "line out of range"
    assert ck(row("src/nope.py:1")) == (False, "file not found")
    assert ck(row("../etc/passwd:1"))[1] == "path outside root"
    assert ck(row("/etc/passwd:1"))[1] == "path outside root"
    assert ck(row("src/a.py:10", ""))[1] == "no snippet quoted"
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

# merge: drop ungrounded/unchecked, dedupe by file+mechanism (keep highest sev, union evidence), rank, cap
G = lambda **k: {"grounded": True, "polarity": "gap", **k}  # noqa: E731
rows = [
    G(id="a", severity="Low", title="x", mechanism="sqli", evidence=["db.py:5"]),
    G(id="b", severity="Critical", title="y", mechanism="SQLi", evidence=["db.py:9"]),
    G(id="c", severity="Medium", title="Null deref", evidence=["u.py:1"]),
    G(id="d", severity="High", title="null  deref!", evidence=["u.py:7"]),
    G(id="e", severity="High", title="Null deref", evidence=["other.py:1"]),
    {"id": "f", "severity": "Critical", "title": "z", "evidence": ["q.py:1"], "grounded": False},
    {"id": "g", "severity": "Critical", "title": "unchecked", "evidence": ["q.py:2"]},
    {"id": "s", "polarity": "strength", "title": "good"},
]
res = m.merge([dict(r) for r in rows])
ids = [f["id"] for f in res["findings"]]
assert ids == ["b", "d", "e", "s"], ids
assert res["dropped"] == {"ungrounded": 2, "duplicate": 2, "over_cap": 0}, res["dropped"]
assert res["findings"][0]["evidence"] == ["db.py:9", "db.py:5"]
cap = m.merge([dict(r) for r in rows], cap=1)
assert [f["id"] for f in cap["findings"]] == ["b", "s"] and cap["dropped"]["over_cap"] == 2
assert m.merge([]) == {"findings": [], "dropped": {"ungrounded": 0, "duplicate": 0, "over_cap": 0}}, "NONE is valid"
print("test_finding_gates: all passed")
