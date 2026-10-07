#!/usr/bin/env python3
"""Tests for perun_policy.py, host_probe policy wiring, and share_learning.py (gh is a stub). Offline."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AD = ROOT / ".claude/skills/agentic-delivery/scripts"
CT = ROOT / ".claude/skills/contribution/scripts"
sys.path.insert(0, str(AD))
import perun_policy  # noqa: E402


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


class PolicyCli(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.pol = self.d / "p.json"
        self.env = {**os.environ, "PERUN_POLICY": str(self.pol)}

    def get(self, dim):
        return run([sys.executable, str(AD / "perun_policy.py"), "get", dim], env=self.env)

    def test_defaults_without_file(self):
        self.assertEqual(self.get("github_actions").stdout.strip(), "efficient")
        self.assertEqual(self.get("share_learnings").stdout.strip(), "ask")

    def test_example_policy(self):
        self.pol.write_text('{"local_cpu": "maximize", "github_actions": "off"}')
        self.assertEqual(self.get("github_actions").stdout.strip(), "off")
        self.assertEqual(self.get("local_cpu").stdout.strip(), "maximize")
        self.assertEqual(self.get("tokens").stdout.strip(), "efficient")

    def test_malformed_fails_closed(self):
        self.pol.write_text('{"tokens": "lots"}')
        r = self.get("tokens")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.get("nonsense").returncode, 2)

    def test_lanes(self):
        self.assertEqual(perun_policy.lanes("maximize", 10, 4.0), 6)
        self.assertEqual(perun_policy.lanes("maximize", 10, 50.0), 1)  # never past the load ceiling
        self.assertEqual(perun_policy.lanes("efficient", 10), 5)
        self.assertEqual(perun_policy.lanes(3, 10), 3)
        self.assertEqual(perun_policy.lanes("off", 10), 1)

    def test_host_probe_bad_policy_cannot_check(self):
        self.pol.write_text("{")
        r = run([sys.executable, str(AD / "host_probe.py")], env=self.env)
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("COULD_NOT_CHECK policy"))


class ShareLearning(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / ".banlist.txt").write_text("Acme Capital\n")
        self.pol = self.d / "p.json"
        self.ledger = self.d / "ledger.jsonl"
        self.calls = self.d / "calls.log"
        gh = self.d / "gh"
        gh.write_text(f'#!/usr/bin/env bash\necho "$*" >>"{self.calls}"\n'
                      f'case "$2" in list) cat "{self.d}/existing.json";; create) echo https://example.com/i/9;; esac\n')
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        (self.d / "existing.json").write_text("[]")
        self.env = {**os.environ, "PERUN_POLICY": str(self.pol), "GH": str(gh), "BANLIST_DIR": str(self.d),
                    "PERUN_LEDGER": str(self.ledger)}

    def share(self, text, *extra):
        return run([sys.executable, str(CT / "share_learning.py"), "--text", text, *extra], env=self.env)

    def created(self):
        return self.calls.exists() and "issue create" in self.calls.read_text()

    def test_ask_default_holds_draft(self):
        r = self.share("Retry loops hide flaky gates")
        self.assertEqual(r.returncode, 3)
        self.assertFalse(self.calls.exists())

    def test_off_does_nothing(self):
        self.pol.write_text('{"share_learnings": "off"}')
        self.assertEqual(self.share("x lesson").returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_auto_generalizes_and_files(self):
        self.pol.write_text('{"share_learnings": "auto"}')
        r = self.share("Acme Capital repo foo/bar at /Users/jane/x mailed jane@example.com: gates drift", "--title", "Gates drift")
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = self.calls.read_text()
        for leak in ("Acme", "foo/bar", "/Users/jane", "jane@example.com"):
            self.assertNotIn(leak, sent)
        self.assertIn("--repo remigiusz-antczak/deep-code-review", sent)
        rec = json.loads(self.ledger.read_text().splitlines()[-1])
        self.assertEqual((rec["status"], rec["url"]), ("created", "https://example.com/i/9"))
        self.assertNotIn("pr create", sent)

    def test_ask_with_approve_files(self):
        self.assertEqual(self.share("Gates drift under load", "--approve").returncode, 0)
        self.assertTrue(self.created())

    def test_duplicate_open_or_closed_not_filed(self):
        self.pol.write_text('{"share_learnings": "auto"}')
        (self.d / "existing.json").write_text('[{"number": 4, "title": "Gates drift under load", "state": "CLOSED"}]')
        r = self.share("Gates drift under load now")
        self.assertEqual(r.returncode, 0)
        self.assertIn("duplicate of #4", r.stdout)
        self.assertFalse(self.created())
        self.assertEqual(json.loads(self.ledger.read_text().splitlines()[-1])["status"], "duplicate")

    def test_missing_banlist_fails_closed(self):
        self.pol.write_text('{"share_learnings": "auto"}')
        (self.d / ".banlist.txt").unlink()
        self.assertEqual(self.share("Gates drift").returncode, 2)
        self.assertFalse(self.created())

    def test_gh_list_failure_does_not_file(self):
        self.pol.write_text('{"share_learnings": "auto"}')
        (self.d / "existing.json").unlink()  # stub's `cat` fails
        self.assertEqual(self.share("Gates drift").returncode, 2)
        self.assertFalse(self.created())


if __name__ == "__main__":
    unittest.main()
