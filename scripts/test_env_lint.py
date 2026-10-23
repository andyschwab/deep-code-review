#!/usr/bin/env python3
"""End-to-end checks for env_lint.py (CLI, exit codes, --base selection) and its preflight advisory wiring."""
import inspect, os, subprocess, sys, tempfile, unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", ".claude", "skills", "agentic-delivery", "scripts")
LINT = os.path.join(SCRIPTS, "env_lint.py")
BAD = 'import os\n\n\ndef test_slot():\n    assert os.environ["CLASS_SLOT"] == "a"\n'
GOOD = 'import os\n\n\ndef test_slot():\n    assert os.environ.get("CLASS_SLOT", "a") == "a"\n'


def lint(name, src, *a):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, name)
        with open(p, "w") as fh:
            fh.write(src)
        r = subprocess.run([sys.executable, LINT, *a, p], capture_output=True, text=True)
        return r.returncode, r.stdout.replace(p, "F")


class EnvLint(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(subprocess.run([sys.executable, LINT, "--selftest"], capture_output=True).returncode, 0)

    def test_flags_with_message_and_exit_1(self):
        rc, out = lint("test_slot.py", BAD)
        self.assertEqual(rc, 1)
        self.assertEqual(out, "F:5: test reads env var CLASS_SLOT without default; set it in the test or give a default\n")

    def test_default_is_clean(self):
        self.assertEqual(lint("test_slot.py", GOOD), (0, ""))

    def test_non_test_file_skipped(self):
        rc, out = lint("app.py", BAD)
        self.assertEqual((rc, out), (0, "SKIP F: not a test file\n"))

    def test_escape_comment(self):
        self.assertEqual(lint("test_slot.py", BAD.replace('"a"\n', '"a"  # env-lint: allow\n'))[0], 0)

    def test_unreadable_base_exits_2(self):
        r = subprocess.run([sys.executable, LINT, "--base", "no-such-ref"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("COULD_NOT_CHECK", r.stdout)

    def test_base_selects_changed_test_files(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*a):
                subprocess.run(["git", "-C", d, "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "user.name=t", "-c", "user.email=t@example.com", *a],
                               check=True, capture_output=True)
            git("init", "-q")
            open(os.path.join(d, "test_old.py"), "w").write(BAD)
            git("add", "."); git("commit", "-qm", "base"); git("tag", "base")
            open(os.path.join(d, "test_new.py"), "w").write(BAD)
            git("add", "."); git("commit", "-qm", "new")
            r = subprocess.run([sys.executable, LINT, "--root", d, "--base", "base"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("test_new.py:5:", r.stdout)
            self.assertNotIn("test_old.py", r.stdout)


class PreflightWiring(unittest.TestCase):
    def test_env_lint_is_a_default_advisory_step(self):
        sys.path.insert(0, SCRIPTS)
        import preflight
        self.assertIn('"env_lint"', inspect.getsource(preflight.main))
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                self.assertEqual(preflight.clock_advisory(tool="env_lint.py"), [])
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
