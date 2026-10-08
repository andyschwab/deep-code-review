#!/usr/bin/env python3
"""install.sh ships slash commands into .claude/commands/ and /perun-demo's script resolves in the installed tree."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALWAYS = {"review.md", "perun-demo.md", "deliver.md"}
GATED = {"cost-retro.md", "perun.md", "perun-run.md"}


def install(repo, *flags):
    return subprocess.run(["bash", str(ROOT / "install.sh"), *flags, str(repo)], capture_output=True, text=True)


def names(repo):
    return {p.name for p in (repo / ".claude/commands").glob("*")}


class InstallCommands(unittest.TestCase):
    def test_default_install_ships_always_commands_only(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            r = install(repo)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(names(repo), ALWAYS)

    def test_perun_demo_script_resolves_and_runs_in_installed_tree(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            install(repo)
            self.assertIn("<deep-code-review>/scripts/perun_demo.py", (repo / ".claude/commands/perun-demo.md").read_text())
            script = repo / ".claude/skills/deep-code-review/scripts/perun_demo.py"
            self.assertTrue(script.is_file())
            r = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("catches 6 of 6", r.stdout)
            self.assertNotIn("benchmark: see docs", r.stdout)

    def test_gated_commands_follow_installed_skills(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            install(repo, "--with-ceo")
            self.assertEqual(names(repo), ALWAYS | GATED)

    def test_existing_file_kept_new_written_and_uninstall_keeps_user_file(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / ".claude/commands").mkdir(parents=True)
            mine = repo / ".claude/commands/review.md"
            mine.write_text("mine\n")
            r = install(repo)
            self.assertEqual(mine.read_text(), "mine\n")
            self.assertTrue((repo / ".claude/commands/review.md.new").is_file())
            self.assertIn("review.md.new", r.stdout)
            self.assertEqual(install(repo).returncode, 0)  # idempotent: no extra .new for identical perun-demo.md
            self.assertEqual(sorted(names(repo) - ALWAYS), ["review.md.new", "review.md.new-1"])
            subprocess.run([sys.executable, str(ROOT / "scripts/perun_uninstall.py"), str(repo), "--apply"], capture_output=True, text=True)
            self.assertEqual(mine.read_text(), "mine\n")
            self.assertFalse((repo / ".claude/commands/perun-demo.md").exists())
            self.assertFalse((repo / ".claude/commands/deliver.md").exists())


if __name__ == "__main__":
    unittest.main()
