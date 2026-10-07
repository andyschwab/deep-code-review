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
        self.assertLessEqual(len(t.encode()), 200)
        self.assertTrue(t.endswith("[truncated]\n"))

    def test_bad_base_fails_closed(self):
        for b in ("nosuchref", "--output=/tmp/x"):
            with self.assertRaises(SystemExit):
                im.build(b, self.d, 8)

    def test_noprefix_config_still_parsed(self):
        git(self.d, "config", "diff.noprefix", "true")
        try:
            self.assertEqual(im.build("main", self.d, 8)["changed_files"], ["core.py"])
        finally:
            git(self.d, "config", "--unset", "diff.noprefix")

    def test_removed_dashdash_line_not_header(self):
        diff = "diff --git a/q.sql b/q.sql\n--- a/q.sql\n+++ b/q.sql\n@@ -1,2 +1,2 @@\n--- a sql comment\n+def real_fn(x)\n"
        files, contract = im.parse_diff(diff)
        self.assertEqual(files, {"q.sql": {"real_fn"}})
        self.assertTrue(contract)

    def test_pack_cleans_control_chars(self):
        self.assertNotIn("\n", cp.clean("a\nb\x1b[0m"))


class Brace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = cls.tmp.name
        p = Path(d)
        (p / "lib.js").write_text("export function alpha(x) {\n  return x;\n}\nexport const beta = (y) => {\n  return y;\n};\n"
                                  "function gamma(z) {\n  const k = 1;\n  return delta(z) + k;\n}\n")
        (p / "dep.js").write_text("function delta(q) {\n  return q;\n}\n")
        for i in range(3):
            (p / f"use{i}.js").write_text("alpha(1);\n")
        git(d, "init", "-q", "-b", "main")
        git(d, "add", ".")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feat")
        (p / "lib.js").write_text("export function alpha(x, w) {\n  return x;\n}\nexport const beta = (y, v) => {\n  return y;\n};\n"
                                  "function gamma(z) {\n  const k = 2;\n  return delta(z) + k;\n}\n")
        git(d, "commit", "-qam", "change")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_symbols_and_cap(self):
        m = im.build("main", self.d, 2)
        names = {s["name"] for s in m["symbols"]}
        self.assertEqual(names, {"alpha", "beta", "gamma"})  # gamma via @@ hunk header (body-only)
        a = next(s for s in m["symbols"] if s["name"] == "alpha")
        self.assertEqual(len(a["callers"]), 2)
        self.assertTrue(m["truncated"])
        self.assertTrue(m["contract_change"])

    def test_callee_body(self):
        g = next(s for s in im.build("main", self.d, 8)["symbols"] if s["name"] == "gamma")
        self.assertEqual([(c["name"], c["file"]) for c in g["callees"]], [("delta", "dep.js")])

    def test_body_only_no_contract(self):
        p = Path(self.d)
        git(self.d, "checkout", "-q", "main")
        git(self.d, "checkout", "-qb", "body")
        (p / "lib.js").write_text((p / "lib.js").read_text().replace("const k = 1", "const k = 3"))
        git(self.d, "commit", "-qam", "body")
        try:
            m = im.build("main", self.d, 8)
        finally:
            git(self.d, "checkout", "-q", "feat")
        self.assertEqual([s["name"] for s in m["symbols"]], ["gamma"])
        self.assertFalse(m["contract_change"])


if __name__ == "__main__":
    unittest.main()
