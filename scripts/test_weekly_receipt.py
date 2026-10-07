#!/usr/bin/env python3
"""Fixture tests for weekly_receipt.py. Offline; fictional data only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / ".claude/skills/agentic-ceo/scripts/weekly_receipt.py"
SESSION = ROOT / ".claude/skills/agentic-ceo/scripts/fixtures/token/session.jsonl"
TOKEN = ROOT / ".claude/skills/agentic-ceo/scripts/token_report.py"


def receipt(*args):
    return subprocess.run([sys.executable, str(RECEIPT), *args], capture_output=True, text=True).stdout


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Jane Smith", "-c", "user.email=jane@example.com", *a],
                   check=True, capture_output=True)


class Receipt(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_all_unknown_without_inputs(self):
        git(self.d, "init", "-q")  # empty repo: git log fails -> unknown, not 0
        out = receipt("--repo", str(self.d))
        for label in ("PRs landed:", "Review findings:", "Tokens per PR:", "Spend:", "Heavy-job holds:"):
            line = next(ln for ln in out.splitlines() if ln.startswith(label))
            self.assertIn("unknown", line)
            self.assertIn("[source:", line)

    def test_counts_prs_findings_holds_spend_tokens(self):
        git(self.d, "init", "-q")
        for s in ("Merge pull request #1 from acme/a", "Merge pull request #2 from acme/b", "plain commit"):
            git(self.d, "commit", "-q", "--allow-empty", "-m", s)
        (self.d / "f.txt").write_text("one\n\ntwo\nthree\n")
        (self.d / "h.txt").write_text("hold\n")
        (self.d / "s.csv").write_text("api_key_name,cost_usd\nENG-1-jane,1.50\nENG-2-bob,2.00\nENG-2-bob,n/a\n")
        rep = json.loads(subprocess.run([sys.executable, str(TOKEN), "--session", str(SESSION), "--json"],
                                        capture_output=True, text=True).stdout)
        total = rep["main"]["raw_tokens"] + rep["subagents_totals"]["raw_tokens"]
        out = receipt("--repo", str(self.d), "--findings", str(self.d / "f.txt"), "--holds", str(self.d / "h.txt"),
                      "--spend", str(self.d / "s.csv"), "--session", str(SESSION), "--days", "3650",
                      "--baseline", str(total))
        self.assertIn("PRs landed:         2 ", out)
        self.assertIn("Review findings:    3 ", out)
        self.assertIn("Heavy-job holds:    1 ", out)
        self.assertIn("$3.50 (1 unpriced rows excluded)", out)
        self.assertIn(f"{total // 2:,}", out)
        self.assertIn("ESTIMATE", out)

    def test_no_baseline_is_unknown_not_guessed(self):
        git(self.d, "init", "-q")
        git(self.d, "commit", "-q", "--allow-empty", "-m", "Merge pull request #7 from acme/a")
        out = receipt("--repo", str(self.d), "--session", str(SESSION), "--days", "3650")
        self.assertIn("unknown (needs session tokens", out)


if __name__ == "__main__":
    unittest.main()
