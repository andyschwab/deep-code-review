"""Tests that the opt-in primitives are wired into defaults: templates, commands, selfcheck, share_learning."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AD = ROOT / ".claude/skills/agentic-delivery"
SL = ROOT / ".claude/skills/contribution/scripts/share_learning.py"


def txt(p):
    return (ROOT / p).read_text()


class T(unittest.TestCase):
    def test_heavy_wired_into_lane_and_coordinator(self):
        for p in (".claude/skills/agentic-delivery/templates/lane-preamble.md",
                  ".claude/skills/agentic-delivery/templates/loops/coordinator.md"):
            s = txt(p)
            self.assertIn("--lane-type heavy", s, p)
            self.assertIn("heavy-slots", s, p)

    def test_heavy_commands_resolve(self):
        r = subprocess.run([sys.executable, str(AD / "scripts/perun_policy.py"), "heavy-slots"],
                           capture_output=True, text=True)
        self.assertTrue(r.stdout.strip().isdigit() and int(r.stdout) >= 2, r)

    def test_perun_run_wires_queue_guard_receipt_ratchet(self):
        s = txt("commands/perun-run.md")
        for k in ("queue_guard.py", "PRIORITIES.md", "weekly_receipt.py", "token_ratchet.py", "--warn"):
            self.assertIn(k, s)

    def test_selfcheck_surfaces_receipt_and_ratchet(self):
        r = subprocess.run([sys.executable, str(AD / "scripts/operating_selfcheck.py"), "--project", str(ROOT),
                            "--settings", str(Path(tempfile.mkdtemp()) / "none.json")],
                           capture_output=True, text=True)
        self.assertIn("weekly-receipt: PRESENT", r.stdout)
        self.assertIn("token-ratchet: PRESENT", r.stdout)

    def test_share_learning_offers_pr_draft(self):
        d = Path(tempfile.mkdtemp())
        (d / ".banlist.txt").write_text("Acme Capital\n")
        env = {**os.environ, "BANLIST_DIR": str(d), "PERUN_LEDGER": str(d / "l.jsonl"),
               "GIT_CONFIG_GLOBAL": "/dev/null"}
        r = subprocess.run([sys.executable, str(SL), "--text",
                            "Pin the retry budget per request so one slow call cannot starve the queue.",
                            "--title", "Retry budget per request"], capture_output=True, text=True, env=env, cwd=d)
        self.assertIn("learning_to_pr.py", r.stderr, r)
        self.assertIn("never pushed", r.stderr)


if __name__ == "__main__":
    unittest.main()
