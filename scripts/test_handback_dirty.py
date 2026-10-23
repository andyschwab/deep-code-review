#!/usr/bin/env python3
"""Regression test: handback_cap warns (default) or blocks (opt-in) when a lane hands back from a linked worktree with
uncommitted changes. Uses throwaway git repos under a temp dir; no network."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/agentic-delivery/scripts"))
import handback_cap as hc  # noqa: E402


def git(cwd, *a):
    subprocess.run(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "user.name=T", "-c", "user.email=t@example.com", *a], cwd=cwd, check=True, capture_output=True)


def check(cwd, mode="warn", agent_type=None):
    """check() with the process scans stubbed; returns (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as st, mock.patch.object(hc, "STATE_DIR", st), \
            mock.patch.dict(os.environ, {"PERUN_BACKGROUND_GUARD": mode, "HANDBACK_AUDIT_LEDGER": "off"}), \
            mock.patch.object(hc, "_push_running", lambda c: False), mock.patch.object(hc, "_bg_running", lambda c: []), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = hc.check({"agent_id": "L1", "cwd": cwd, "agent_type": agent_type, "last_assistant_message": "status=VERIFIED"})
    return rc, out.getvalue(), err.getvalue()


class DirtyTree(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.main = os.path.realpath(self._t.name) + "/main"
        self.lane = os.path.realpath(self._t.name) + "/lane"
        os.mkdir(self.main)
        git(self.main, "init", "-q", "-b", "main")
        Path(self.main, ".gitignore").write_text("ignored.log\n")
        Path(self.main, "a.txt").write_text("a\n")
        git(self.main, "add", ".")
        git(self.main, "commit", "-qm", "init")
        git(self.main, "worktree", "add", "-q", "-b", "lane", self.lane)

    def test_clean_linked_worktree_is_silent(self):
        self.assertEqual(check(self.lane), (0, "", ""))

    def test_gitignored_file_is_ignored(self):
        Path(self.lane, "ignored.log").write_text("x")
        self.assertEqual(check(self.lane), (0, "", ""))

    def test_untracked_and_modified_warn_once(self):
        Path(self.lane, "new.txt").write_text("x")
        Path(self.lane, "a.txt").write_text("changed\n")
        rc, out, err = check(self.lane)
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn("dirty worktree: 2 uncommitted path(s)", json.loads(out)["systemMessage"])

    def test_main_checkout_is_never_reported(self):
        Path(self.main, "new.txt").write_text("x")
        self.assertEqual(check(self.main), (0, "", ""))
        self.assertEqual(hc._dirty_tree(self.main), [])

    def test_block_mode_blocks_then_off_is_silent(self):
        Path(self.lane, "new.txt").write_text("x")
        rc, out, err = check(self.lane, "block")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("uncommitted path(s)", err)
        self.assertEqual(check(self.lane, "off"), (0, "", ""))

    def test_committed_work_passes_in_block_mode(self):
        Path(self.lane, "new.txt").write_text("x")
        git(self.lane, "add", ".")
        git(self.lane, "commit", "-qm", "work")
        self.assertEqual(check(self.lane, "block"), (0, "", ""))

    def test_git_failure_fails_open(self):
        with mock.patch.object(hc.subprocess, "run", side_effect=OSError("no git")):
            self.assertIsNone(hc._dirty_tree(self.lane))
        with mock.patch.object(hc, "_dirty_tree", lambda c: None):
            rc, out, err = check(self.lane, "block")
        self.assertEqual((rc, out), (0, ""))
        self.assertIn("COULD_NOT_CHECK", err)

    def test_git_timeout_and_nonzero_exit_fail_open(self):
        Path(self.lane, "new.txt").write_text("x")
        with mock.patch.object(hc.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 15)):
            self.assertIsNone(hc._dirty_tree(self.lane))
        real = subprocess.run

        def status_fails(cmd, *a, **k):
            return subprocess.CompletedProcess(cmd, 128, "", "boom") if "status" in cmd else real(cmd, *a, **k)

        with mock.patch.object(hc.subprocess, "run", status_fails):
            self.assertIsNone(hc._dirty_tree(self.lane))

    def test_non_repo_dir_is_clean(self):
        d = os.path.realpath(self._t.name) + "/plain"
        os.mkdir(d)
        Path(d, "x.txt").write_text("x")
        self.assertEqual(hc._dirty_tree(d), [])

    def test_separate_git_dir_repo_is_not_a_linked_worktree(self):
        # `.git` is a FILE here (as in a linked worktree or submodule) but git-dir == common dir
        d = os.path.realpath(self._t.name) + "/sep"
        os.mkdir(d)
        subprocess.run(["git", "init", "-q", "--separate-git-dir", os.path.realpath(self._t.name) + "/sep.git", d], check=True, capture_output=True)
        self.assertTrue(Path(d, ".git").is_file())
        Path(d, "x.txt").write_text("x")
        self.assertEqual(check(d, "block"), (0, "", ""))

    def test_read_only_agent_types_are_skipped(self):
        Path(self.lane, "new.txt").write_text("x")
        for t in ("cavecrew-reviewer", "code-investigator", "security-audit", "Explore"):
            self.assertEqual(check(self.lane, "block", t), (0, "", ""), t)
        self.assertEqual(check(self.lane, "block", "cavecrew-builder")[0], 2)

    def test_message_says_to_ignore_foreign_edits(self):
        Path(self.lane, "new.txt").write_text("x")
        self.assertIn("Ignore if these edits are not yours", json.loads(check(self.lane)[1])["systemMessage"])

    def test_missing_dir_or_cwd_is_clean(self):
        self.assertEqual(hc._dirty_tree("/nonexistent-dir-xyz"), [])
        self.assertEqual(hc._dirty_tree(None), [])


if __name__ == "__main__":
    unittest.main()
