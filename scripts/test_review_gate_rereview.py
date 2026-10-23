#!/usr/bin/env python3
"""review_gate.py re-review rule: a receipt for an older head still covers a newer one when the diff since the reviewed
head touches no tier-1 path (templates/review-tiers.tsv); a tier-1 path in the delta, or a commit not present locally, needs a fresh review."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RG = ROOT / ".claude/skills/agentic-delivery/scripts/review_gate.py"


class T(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.repo = Path(self.t.name) / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, "GH": "false", "REVIEW_DIR": str(Path(self.t.name) / "rev"),
                    "PERUN_POLICY": str(Path(self.t.name) / "p.json"), "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
        Path(self.env["PERUN_POLICY"]).write_text('{"review_gate": "enforce"}')
        self.git("init", "-q")
        self.reviewed = self.commit("src/app.py")

    def tearDown(self):
        self.t.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=T", *a], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, path):
        f = self.repo / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f.read_text() + "x\n" if f.exists() else "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", path)
        return self.git("rev-parse", "HEAD")

    def check(self, head):
        subprocess.run([sys.executable, str(RG), "receipt", "1", "--reviewer", "rev1", "--author", "bld1", "--head", self.reviewed],
                       env=self.env, check=True)
        return subprocess.run([sys.executable, str(RG), "check", "1", "--head", head], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL).returncode

    def test_same_head_ok(self):
        self.assertEqual(self.check(self.reviewed), 0)

    def test_delta_without_tier1_path_keeps_review(self):
        self.assertEqual(self.check(self.commit("references/notes.md")), 0)

    def test_delta_touching_tier1_path_needs_fresh_review(self):
        self.commit("src/other.py")
        self.assertEqual(self.check(self.commit(".claude/hooks/guard.sh")), 1)

    def test_rename_of_tier1_file_into_references_needs_fresh_review(self):
        self.commit(".claude/hooks/guard.sh")
        self.reviewed = self.git("rev-parse", "HEAD")
        (self.repo / "references").mkdir()
        self.git("mv", ".claude/hooks/guard.sh", "references/guard.md")
        self.git("commit", "-q", "-m", "mv")
        self.assertEqual(self.check(self.git("rev-parse", "HEAD")), 1)

    def skill(self, front, body="body"):
        p = self.repo / ".claude/skills/demo/SKILL.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nname: demo\n{front}\n---\n{body}\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "skill")
        return self.git("rev-parse", "HEAD")

    def test_skill_tool_line_change_needs_fresh_review(self):
        self.reviewed = self.skill("allowed-tools: Read")
        self.assertEqual(self.check(self.skill("allowed-tools: Read, Bash")), 1)

    def test_skill_tool_list_item_added_needs_fresh_review(self):
        self.reviewed = self.skill("allowed-tools:\n  - Read")
        self.assertEqual(self.check(self.skill("allowed-tools:\n  - Read\n  - Bash")), 1)

    def test_skill_body_change_keeps_review(self):
        self.reviewed = self.skill("allowed-tools:\n  - Read", "body")
        self.assertEqual(self.check(self.skill("allowed-tools:\n  - Read", "new body")), 0)

    def test_unknown_head_needs_fresh_review(self):
        self.assertEqual(self.check("c" * 40), 1)


if __name__ == "__main__":
    unittest.main()
