#!/usr/bin/env python3
"""handback.py --spec: a flake fix must carry a 3x spec receipt. Reuses the throwaway-repo fixture of test_handback.py."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_handback as th  # noqa: E402

LED = ".claude/flake-ledger/quarantine.json"


class Spec(unittest.TestCase):
    setUp, tearDown, git, commit, lane, hb = (th.T.__dict__[n] for n in ("setUp", "tearDown", "git", "commit", "lane", "hb"))

    def spec(self, fail_on=0, body=""):
        """Commit a spec onto the lane that counts its runs in a file and exits 1 on run number fail_on (0 = never).
        Returns (spec path, run-counter file, sha)."""
        n = self.d / "runs"
        sha = self.commit("spec.py", f"import pathlib,sys,time\nn=pathlib.Path({str(n)!r})\nk=int(n.read_text() or 0)+1 if n.exists() else 1\n"
                          f"n.write_text(str(k))\n{body}sys.exit(1 if k=={fail_on} else 0)\n", "spec")
        return "spec.py", n, sha

    def flake_subject(self, subject):
        self.git("checkout", "-q", "-b", "lane")
        self.commit("changelog.d/x.md", "### Fixed\n- x\n", subject)
        return self.git("rev-parse", "HEAD")

    def quarantine(self, ident, on_base=False):
        """Quarantine ident in an absolute dir (default) or, on_base, in the repo's default ledger dir committed on main."""
        q = json.dumps({ident: {"since": "2026-01-01", "expires": "2099-01-01"}})
        if on_base:
            self.commit(LED, q, "ledger")
        else:
            (self.d / "led").mkdir()
            (self.d / "led/quarantine.json").write_text(q)
            self.env["FLAKE_LEDGER_DIR"] = str(self.d / "led")

    def assert_spec_required(self, r):
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("handback RED: spec: --spec PATH is required", r.stdout)

    def test_three_passes_are_ok(self):
        s, n, sha = self.spec_on_lane()
        r = self.hb(sha, "--spec", s)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(n.read_text(), "3")

    def spec_on_lane(self, **kw):
        self.lane()
        return self.spec(**kw)

    def test_one_flaky_failure_is_red(self):
        s, _, sha = self.spec_on_lane(fail_on=2)
        r = self.hb(sha, "--spec", s)
        self.assertEqual(r.returncode, 1)
        self.assertIn("handback RED: spec spec.py", r.stdout)

    def test_dirty_worktree_is_red(self):
        s, n, sha = self.spec_on_lane()
        (self.repo / "spec.py").write_text("import sys\nsys.exit(0)\n")  # the receipt would not be for SHA
        r = self.hb(sha, "--spec", s)
        self.assertIn("handback RED: spec: worktree not clean at SHA", r.stdout)
        self.assertFalse(n.exists())

    def test_slow_spec_times_out(self):
        s, _, sha = self.spec_on_lane(body="time.sleep(5)\n")
        r = self.hb(sha, "--spec", s, "--timeout", "1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("handback RED: spec spec.py: timeout", r.stdout)

    def test_flake_subject_without_spec_is_red(self):
        self.assert_spec_required(self.hb(self.flake_subject("Fix login test flake")))

    def test_flaky_flakiness_and_uppercase_subjects_are_red(self):
        for subject in ("fix: flaky retry test", "fix the flakiness of login", "FIX FLAKE in login"):
            with self.subTest(subject):
                self.assert_spec_required(self.hb(self.flake_subject(subject)))
                self.git("checkout", "-q", "main")
                self.git("branch", "-q", "-D", "lane")

    def test_flake_subject_below_the_tip_is_red(self):
        self.flake_subject("fix: flaky retry test")
        self.assert_spec_required(self.hb(self.commit("work.txt", "w\n", "tidy")))

    def test_flake_subject_with_green_spec_is_ok(self):
        self.flake_subject("fix: flaky retry test")
        s, n, sha = self.spec()
        r = self.hb(sha, "--spec", s)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(n.read_text(), "3")

    def test_quarantined_path_and_path_name_ids_are_red(self):
        for ident in ("work.txt::case", "work.txt"):
            with self.subTest(ident):
                self.quarantine(ident)
                self.assert_spec_required(self.hb(self.lane()))
                (self.d / "led/quarantine.json").unlink()
                (self.d / "led").rmdir()
                self.git("checkout", "-q", "main")
                self.git("branch", "-q", "-D", "lane")

    def test_quarantined_id_outside_the_diff_needs_no_spec(self):
        self.quarantine("other.txt::case")
        r = self.hb(self.lane())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_quarantine_is_read_from_base_not_the_lane(self):
        self.quarantine("work.txt", on_base=True)
        self.lane()
        self.git("rm", "-q", LED)  # the PR deletes its own entry
        self.assert_spec_required(self.hb(self.commit("gone.txt", "g\n", "drop ledger")))

    def test_normal_subject_without_spec_is_ok(self):
        r = self.hb(self.lane())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
