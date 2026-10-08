#!/usr/bin/env python3
"""review_gate.py: independent-review receipt/comment gate, warn-first policy, wired into land_train.sh. Offline (gh is a stub)."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AD = ROOT / ".claude/skills/agentic-delivery"
RG = AD / "scripts/review_gate.py"
HEAD = "a" * 40


class T(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        gh = self.d / "gh"
        gh.write_text(f"#!/bin/sh\ncat {self.d}/gh.json 2>/dev/null || exit 1\n")
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, "GH": str(gh), "REVIEW_DIR": str(self.d / "rev"), "PERUN_POLICY": str(self.d / "p.json")}

    def tearDown(self):
        self.t.cleanup()

    def run_gate(self, *a, mode=None):
        if mode:
            (self.d / "p.json").write_text(json.dumps({"review_gate": mode}))
        else:
            (self.d / "p.json").write_text("{}")
        return subprocess.run([sys.executable, str(RG), *a], env=self.env, capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def marker(self, reviewer="rev1", author="bld1", head=HEAD):
        return f"<!-- perun-review reviewer={reviewer} author={author} head={head} diff=pass evil-twin=pass -->"

    def test_default_warns_never_blocks(self):
        r = self.run_gate("check", "7", "--head", HEAD)
        self.assertEqual(r.returncode, 0)
        self.assertIn("WARN review_gate", r.stderr)

    def test_enforce_blocks_without_evidence(self):
        r = self.run_gate("check", "7", "--head", HEAD, mode="enforce")
        self.assertEqual(r.returncode, 1)
        self.assertIn("REVIEW GATE", r.stderr)

    def test_off_is_silent(self):
        r = self.run_gate("check", "7", "--head", HEAD, mode="off")
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_receipt_satisfies_enforce_and_binds_head(self):
        self.assertEqual(self.run_gate("receipt", "7", "--reviewer", "rev1", "--author", "bld1", "--head", HEAD).returncode, 0)
        self.assertEqual(self.run_gate("check", "7", "--head", HEAD[:12], mode="enforce").returncode, 0)
        self.assertEqual(self.run_gate("check", "7", "--head", "b" * 40, mode="enforce").returncode, 1)

    def test_self_review_refused(self):
        r = self.run_gate("receipt", "7", "--reviewer", "Bld1", "--author", "bld1", "--head", HEAD)
        self.assertEqual(r.returncode, 2)
        (self.d / "rev").mkdir()
        (self.d / "rev/7.json").write_text(json.dumps({"reviewer": "bld1", "author": "BLD1", "head": HEAD, "diff_pass": True, "evil_twin": True}))
        self.assertEqual(self.run_gate("check", "7", "--head", HEAD, mode="enforce").returncode, 1)

    def test_pr_comment_marker(self):
        def gh(body, login="octo"):
            (self.d / "gh.json").write_text(json.dumps({"author": {"login": login}, "comments": [{"body": body}]}))
        gh("looks good " + self.marker())
        self.assertEqual(self.run_gate("check", "9", "--head", HEAD, mode="enforce").returncode, 0)
        gh(self.marker(reviewer="octo"), login="octo")  # reviewer is the GitHub PR author
        self.assertEqual(self.run_gate("check", "9", "--head", HEAD, mode="enforce").returncode, 1)
        gh(self.marker(head="c" * 40))  # review of a different head
        self.assertEqual(self.run_gate("check", "9", "--head", HEAD, mode="enforce").returncode, 1)
        gh("diff=pass evil-twin=pass")  # prose without the marker
        self.assertEqual(self.run_gate("check", "9", "--head", HEAD, mode="enforce").returncode, 1)

    def test_head_required_and_stale_marker_rejected(self):
        self.assertNotEqual(self.run_gate("check", "9").returncode, 0)  # --head is mandatory
        (self.d / "gh.json").write_text(json.dumps({"author": {"login": "octo"}, "comments": [
            {"author": {"login": "octo"}, "body": self.marker(head="c" * 40)}]}))
        self.assertEqual(self.run_gate("check", "9", "--head", HEAD, mode="enforce").returncode, 1)  # old SHA
        (self.d / "gh.json").write_text(json.dumps({"author": {"login": "octo"}, "comments": [
            {"author": {"login": "octo"}, "body": self.marker()}]}))
        r = self.run_gate("check", "9", "--head", HEAD, mode="enforce")
        self.assertEqual(r.returncode, 0)
        self.assertIn("same-account review: run-id separation only", r.stderr)

    def test_internal_error_never_blocks_in_warn(self):
        code = ("import sys; sys.path.insert(0, %r); import review_gate as g\n"
                "g._main = lambda a: 1 / 0\nsys.exit(g.main(['check', '1', '--head', 'abcdef1']))" % str(AD / "scripts"))
        (self.d / "p.json").write_text("{}")
        r = subprocess.run([sys.executable, "-c", code], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("WARN review_gate: internal error", r.stderr)

    def test_policy_key_validated_and_wired(self):
        sys.path.insert(0, str(AD / "scripts"))
        import perun_policy
        self.assertEqual(perun_policy.validate({})["review_gate"], "warn")
        with self.assertRaises(ValueError):
            perun_policy.validate({"review_gate": "maybe"})
        self.assertIn("review_gate.py", (AD / "scripts/land_train.sh").read_text())
        self.assertIn("review_gate.py", (AD / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
