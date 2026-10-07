"""Fixture tests for learning_to_pr.py: fictional data only."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/skills/contribution/scripts/learning_to_pr.py"
LESSON = "Pin the retry budget per request, not per client, so one slow call cannot starve the queue."


class T(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / ".banlist.txt").write_text("Acme Capital\nJane Smith\n")
        ref = self.d / "skills/demo/references"
        ref.mkdir(parents=True)
        (self.d / "skills/demo/SKILL.md").write_text("# Demo\n\nAlways validate input at trust boundaries before use.\n")
        (ref / "a.md").write_text("Prefer idempotent writes so a replay changes nothing at all.\n")
        subprocess.run(["git", "init", "-q", str(self.d)], check=True)
        self.env = {**os.environ, "BANLIST_DIR": str(self.d), "PERUN_LEDGER": str(self.d / "led.jsonl"),
                    "GIT_CONFIG_GLOBAL": "/dev/null"}

    def run_(self, text, *extra):
        return subprocess.run([sys.executable, str(SCRIPT), "--text", text, "--skills", str(self.d / "skills"),
                               "--out", str(self.d / "out"), *extra], capture_output=True, text=True,
                              env=self.env, cwd=self.d)

    def status(self):
        return json.loads((self.d / "led.jsonl").read_text().splitlines()[-1])["status"]

    def test_draft_applies_and_is_local(self):
        r = self.run_(LESSON)
        self.assertEqual(r.returncode, 0, r.stderr)
        (p,) = (self.d / "out").glob("*/change.patch")
        self.assertTrue((p.parent / "body.md").is_file())
        ap = subprocess.run(["git", "apply", "--check", str(p)], cwd=self.d, capture_output=True, text=True)
        self.assertEqual(ap.returncode, 0, ap.stderr)
        self.assertIn(LESSON, p.read_text())
        self.assertEqual(self.status(), "pr-drafted")

    def test_draft_appends_to_existing_target(self):
        t = self.d / "notes.md"
        t.write_text("# Notes\n\n- first rule about caching headers\n")
        r = self.run_(LESSON, "--target", "notes.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        (p,) = (self.d / "out").glob("*/change.patch")
        ap = subprocess.run(["git", "apply", "--check", str(p)], cwd=self.d, capture_output=True, text=True)
        self.assertEqual(ap.returncode, 0, ap.stderr)

    def test_privacy_hit_refuses_and_writes_nothing(self):
        for bad in ("Jane Smith hit this bug twice in review.", "See acme-org/app-repo for the fix.",
                    "Seen in /Users/jane/work/app today."):
            self.assertEqual(self.run_(bad).returncode, 1, bad)
        self.assertFalse((self.d / "out").exists())
        self.assertEqual(self.status(), "refused")
        self.assertNotIn("Jane", (self.d / "led.jsonl").read_text())

    def test_missing_banlist_fails_closed(self):
        (self.d / ".banlist.txt").unlink()
        self.assertEqual(self.run_(LESSON).returncode, 2)

    def test_near_duplicate_of_doctrine_not_drafted(self):
        r = self.run_("Always validate input at the trust boundaries before use.")
        self.assertEqual(r.returncode, 0)
        self.assertIn("near-duplicate", r.stdout)
        self.assertFalse((self.d / "out").exists())
        self.assertEqual(self.status(), "duplicate")

    def test_unsafe_target_and_empty_rejected(self):
        self.assertEqual(self.run_("   ").returncode, 2)
        self.assertEqual(self.run_(LESSON, "--target", "../x.md").returncode, 2)


if __name__ == "__main__":
    unittest.main()
