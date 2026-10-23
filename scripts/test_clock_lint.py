#!/usr/bin/env python3
"""Offline tests for clock_lint.py: CLI output, exit codes, --base changed-files mode, COULD_NOT_CHECK."""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINT = os.path.join(ROOT, ".claude/skills/agentic-delivery/scripts/clock_lint.py")


def lint(*args):
    p = subprocess.run([sys.executable, LINT, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class ClockLint(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))

    def put(self, name, text):
        p = os.path.join(self.d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_finding_format_and_exit(self):
        p = self.put("test_a.py", "import time\nx = time.time()\n")
        rc, out = lint(p)
        self.assertEqual(rc, 1)
        self.assertEqual(out.strip(), "%s:2: real clock in test; pin a fake clock or inject now" % p)

    def test_marker_and_allow_and_non_test(self):
        self.assertEqual(lint(self.put("test_b.py", "@freeze_time(\"2020-01-01\")\ndef test_a():\n    datetime.now()\n"))[0], 0)
        self.assertEqual(lint(self.put("c.test.ts", "// clock-lint: allow\nDate.now()\n"))[0], 0)
        self.assertEqual(lint(self.put("d.test.mjs", "Date.now()\n"))[0], 1)
        self.assertEqual(lint(self.put("e.py_x/test_e.py", "def test_a():\n    now = datetime.now()\n"))[0], 1)
        self.assertEqual(lint(self.put("test_f.py", "@mock.patch('time.sleep')\ndef test_a(s):\n    time.time()\n"))[0], 1)
        p = self.put("app.rb", "Time.now\n")  # py/js non-test files are scanned for date bombs, not skipped
        self.assertEqual(lint(p), (0, "SKIP %s: not a test file\n" % p))

    def test_each_language(self):
        for name, src in (("t.spec.js", "new Date()\n"), ("x_test.go", "time.Now()\n"),
                          ("test-x.sh", "echo $(date +%s)\n"), ("tests/test_z.py", "datetime.utcnow()\n")):
            self.assertEqual(lint(self.put(name, src))[0], 1, name)
        self.assertEqual(lint(self.put("t2.spec.js", "new Date(0)\nDate.now = () => 1\n"))[0], 0)

    def test_unreadable_is_not_silent(self):
        rc, out = lint(os.path.join(self.d, "test_nope.py"))
        self.assertEqual(rc, 2)
        self.assertIn("COULD_NOT_CHECK", out)

    def test_base_mode_only_changed_files(self):
        g = lambda *a: subprocess.run(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "user.name=t", "-c", "user.email=t@example.com", *a],
                                      cwd=self.d, check=True, capture_output=True, text=True)
        g("init", "-q")
        self.put("test_old.py", "time.time()\n")
        g("add", "."), g("commit", "-qm", "base")
        base = g("rev-parse", "HEAD").stdout.strip()
        self.put("test_new.py", "time.time()\n")
        g("add", "."), g("commit", "-qm", "new")
        rc, out = lint("--root", self.d, "--base", base)
        self.assertEqual((rc, out.strip()), (1, "test_new.py:1: real clock in test; pin a fake clock or inject now"))
        self.assertEqual(lint("--root", self.d, "--base", "nope-ref")[0], 2)
        sub = self.put("sub/x.txt", "x")  # --root below the repo top: paths still resolve from the top
        rc, out = lint("--root", os.path.dirname(sub), "--base", base)
        self.assertEqual(rc, 1, out)
        self.assertIn("test_new.py:1:", out)
        self.assertEqual(lint("--root", self.d, "--base", base, "--head", base), (0, ""))

    def test_pre_push_hook_wired_warn_only(self):
        with open(os.path.join(ROOT, ".claude/skills/deep-code-review/templates/pre-push-verify.sh")) as fh:
            hook = fh.read()
        self.assertIn('python3 "${clock_lint}" --base "${base_sha}" --head "${local_sha}" --block-added --deadline 5 >&2 || cl_rc=$?', hook)

    def test_deadline_is_not_silent(self):
        p = self.put("test_d.py", "time.time()\n")
        rc, out = lint("--deadline", "0", p)
        self.assertEqual(rc, 2)
        self.assertIn("COULD_NOT_CHECK deadline exceeded", out)
        self.assertEqual(lint("--deadline", "5", p)[0], 1)

    def test_always_flag_wall_clock_never_monotonic(self):
        p = self.put("test_m.py", "def test_a():\n    a = time.monotonic() + time.perf_counter() + time.process_time()\n")
        self.assertEqual(lint(p)[0], 0)
        p = self.put("test_w.py", "def test_a():\n    x = datetime.now() - timedelta(days=1)\n    deadline = datetime.now()\n    s = time.time()\n    e = time.time() - s\n")
        self.assertEqual(lint(p)[1].count("real clock in test"), 4)

    def test_fixture_in_test_name_is_not_a_marker(self):
        p = self.put("test_n.py", "@freeze_time('2020-01-01')\ndef test_fixture_a():\n    datetime.now()\ndef test_b():\n    datetime.now()\n")
        self.assertIn("test_n.py:5:", lint(p)[1])
        p = self.put("test_o.py", "@pytest.fixture\ndef c():\n    with freeze_time('2020-01-01'):\n        yield\ndef test_b():\n    datetime.now()\n")
        self.assertEqual(lint(p)[0], 0)

    def test_sh_date_flags_before_d(self):
        p = self.put("test-u.sh", "a=$(date -u -d '2020-01-01' +%F)\nb=$(date --utc --date='2020-01-01')\n")
        self.assertEqual(lint(p)[0], 0)
        self.assertEqual(lint(self.put("test-v.sh", "a=$(date -u +%F)\nb=$(date -u -d 'yesterday')\n"))[1].count("real clock"), 2)

    def test_selftest(self):
        self.assertEqual(lint("--selftest")[0], 0)


if __name__ == "__main__":
    unittest.main()
