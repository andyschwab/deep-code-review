#!/usr/bin/env python3
"""Tests for wired_check.py, scrub_env.sh and the fail-closed worktree privacy gate (stdlib only)."""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(ROOT, ".claude/skills/agentic-delivery/scripts")
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def sh(*a, cwd=None, env=None):
    return subprocess.run(a, cwd=cwd, env=env or CLEAN, capture_output=True, text=True)


def git(cwd, *a):
    r = sh("git", "-c", "user.email=a@example.com", "-c", "user.name=T", *a, cwd=cwd)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def put(root, rel, text="x\n"):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


class WiredCheck(unittest.TestCase):
    def test_wired_unwired_and_test_only(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q", "-b", "main")
            put(d, "README.md")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "base")
            base = git(d, "rev-parse", "HEAD")
            for n in ("wired", "orphan", "testonly"):
                put(d, "scripts/%s.py" % n)
            put(d, "scripts/test_orphan.py", "import orphan  # orphan.py\n")
            put(d, "scripts/test_testonly.py", "run testonly.py\n")
            put(d, ".claude/settings.json", '{"hooks": "python3 scripts/wired.py"}\n')
            put(d, "scripts/INDEX.md", "orphan.py testonly.py\n")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "new")
            r = sh("python3", os.path.join(SD, "wired_check.py"), base, "HEAD", "--root", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("scripts/wired.py", r.stdout)
            self.assertIn("WARN: scripts/orphan.py", r.stdout)
            self.assertIn("WARN: scripts/testonly.py", r.stdout)
            self.assertIn("3 new script(s), 2 unwired", r.stdout)


class ScrubEnv(unittest.TestCase):
    def test_child_does_not_see_git_dir(self):
        env = dict(CLEAN, GIT_DIR="/nonexistent", GIT_WORK_TREE="/x", DATABASE_URL="u", KEEP="1")
        helper = os.path.join(SD, "scrub_env.sh")
        r = sh("bash", helper, "sh", "-c", 'echo "[${GIT_DIR-}${GIT_WORK_TREE-}${DATABASE_URL-}][$KEEP]"', env=env)
        self.assertEqual(r.stdout.strip(), "[][1]")
        self.assertIn("-u GIT_DIR", sh("bash", helper, env=env).stdout)


class PrivacyWorktree(unittest.TestCase):
    def test_fail_closed_when_worktree_lacks_local_banlist(self):
        gates = os.path.join(ROOT, "scripts/ci-gates.sh")
        with tempfile.TemporaryDirectory() as d:
            main, wt = os.path.join(d, "main"), os.path.join(d, "wt")
            os.makedirs(main)
            git(main, "init", "-q", "-b", "main")
            put(main, ".banlist.txt", "NOMATCH_[A-Z]+\n")
            put(main, ".banlist.local.txt", "ALSONOMATCH_[A-Z]+\n")
            put(main, "f.txt", "clean\n")
            git(main, "add", ".banlist.txt", "f.txt")
            git(main, "commit", "-qm", "c")
            git(main, "worktree", "add", "-q", "--detach", wt)
            run = lambda root: sh("bash", gates, "privacy", "--banlist", os.path.join(root, ".banlist.txt"),
                                  os.path.join(root, "f.txt"))
            self.assertEqual(run(main).returncode, 0)
            r = run(wt)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("cp '", r.stderr)
            self.assertIn(os.path.join(wt, ".banlist.local.txt"), r.stderr)
            put(wt, ".banlist.local.txt", "ALSONOMATCH_[A-Z]+\n")
            self.assertEqual(run(wt).returncode, 0)


if __name__ == "__main__":
    unittest.main()
