#!/usr/bin/env python3
"""Repo-scan gates enumerate git files only: a nested worktree and a gitignored dir holding a planted violation
are NOT scanned (ci-gates privacy + size, perun_doctor.walk), while an untracked-not-ignored file IS, and a
non-git directory still falls back to a full walk."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
GATES = ROOT / "scripts/ci-gates.sh"
PLANT = "PLANTED_SECRET_12345\n"
SKILL = ".claude/skills/demo/SKILL.md"


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=a@example.com", "-c", "user.name=A", *a],
                   check=True, capture_output=True)


def put(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def gate(root, *args):
    r = subprocess.run(["bash", str(GATES), *args], cwd=root, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout + r.stderr


def privacy(root):
    return gate(root, "privacy", "--banlist", ".banlist.txt", ".")


def size(root):
    return gate(root, "size", "--config", "sizes.tsv", ".")


def make_fixture(d):
    d = Path(d)
    put(d, ".banlist.txt", "PLANTED_SECRET_[0-9]+\n")
    put(d, "sizes.tsv", f"# unit: bytes\n{SKILL}\t100\n")
    put(d, SKILL, "ok\n")
    put(d, "src/a.txt", "clean\n")
    put(d, ".gitignore", "build/\n")
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "init")
    return d


class T(unittest.TestCase):
    def test_nested_worktree_and_ignored_dir_not_scanned(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_fixture(Path(t) / "repo")
            self.assertEqual(privacy(d)[0], 0)
            self.assertEqual(size(d)[0], 0)
            put(d, "build/leak.txt", PLANT)  # ignored build dir
            put(d, "build/.claude/skills/x/SKILL.md", "no budget row\n")
            git(d, "worktree", "add", "-q", "--detach", "nested", "HEAD")  # nested worktree, untracked in the parent
            put(d / "nested", "leak.txt", PLANT)
            put(d / "nested", ".claude/skills/y/SKILL.md", "no budget row\n")
            self.assertEqual(privacy(d)[0], 0, privacy(d)[1])
            self.assertEqual(size(d)[0], 0, size(d)[1])
            import perun_doctor
            seen = {p.name for p in perun_doctor.walk(d)}
            self.assertIn("a.txt", seen)
            self.assertNotIn("leak.txt", seen)
            put(d, "src/new.txt", PLANT)  # untracked-not-ignored IS scanned
            self.assertEqual(privacy(d)[0], 1)

    def test_non_git_dir_falls_back_to_full_walk(self):
        with tempfile.TemporaryDirectory() as t:
            put(t, ".banlist.txt", "PLANTED_SECRET_[0-9]+\n")
            put(t, "deep/leak.txt", PLANT)
            self.assertEqual(privacy(t)[0], 1)


if __name__ == "__main__":
    unittest.main()
