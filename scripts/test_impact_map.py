#!/usr/bin/env python3
"""Tests for impact_map.py and context_pack.py on a synthetic multi-file repo (offline, hermetic)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

S = Path(__file__).resolve().parent.parent / ".claude/skills/deep-code-review/scripts"
sys.path.insert(0, str(S))
import context_pack as cp  # noqa: E402
import impact_map as im  # noqa: E402


def git(d, *a):
    subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.com", *a], cwd=d, check=True, capture_output=True)


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = cls.tmp.name
        p = Path(d)
        (p / "util.py").write_text("def helper(x):\n    return x\n")
        (p / "core.py").write_text("from util import helper\n\ndef compute(a):\n    return helper(a) + 1\n")
        (p / "api.py").write_text("from core import compute\n\ndef handler(v):\n    return compute(v)\n")
        (p / "other.py").write_text("def unrelated():\n    return 0\n")
        git(d, "init", "-q", "-b", "main")
        git(d, "add", ".")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feat")
        (p / "core.py").write_text("from util import helper\n\ndef compute(a, b):\n    return helper(a) + b\n")
        git(d, "commit", "-qam", "change compute signature")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_callers_out_of_diff(self):
        m = im.build("main", self.d, 8)
        self.assertEqual(m["changed_files"], ["core.py"])
        self.assertTrue(m["contract_change"])
        s = next(x for x in m["symbols"] if x["name"] == "compute")
        self.assertEqual({c["file"] for c in s["callers"]}, {"api.py"})
        self.assertIn("api.py", m["out_of_diff_files"])
        self.assertNotIn("other.py", m["out_of_diff_files"])

    def test_callees(self):
        s = next(x for x in im.build("main", self.d, 8)["symbols"] if x["name"] == "compute")
        self.assertEqual([c["name"] for c in s["callees"]], ["helper"])
        self.assertEqual(s["callees"][0]["file"], "util.py")

    def test_cap(self):
        m = im.build("main", self.d, 0)
        self.assertTrue(m["truncated"])
        self.assertEqual(m["symbols"][0]["callers"], [])

    def test_no_diff(self):
        m = im.build("feat", self.d, 8)
        self.assertEqual((m["changed_files"], m["symbols"], m["contract_change"]), ([], [], False))

    def test_pack(self):
        t = cp.render("main", self.d, "make compute take b", 8, 24000)
        for want in ("make compute take b", "api.py:4", "change compute signature", "callee helper"):
            self.assertIn(want, t)
        self.assertIn("no intent supplied", cp.render("main", self.d, "", 8, 24000))

    def test_pack_bounded(self):
        t = cp.render("main", self.d, "", 8, 200)
        self.assertLessEqual(len(t.encode()), 220)
        self.assertTrue(t.endswith("[truncated]\n"))


if __name__ == "__main__":
    unittest.main()
