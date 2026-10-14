#!/usr/bin/env python3
"""End-to-end checks for clock_lint.py date-literal time bombs; "today" is always injected via --today."""
import inspect, os, subprocess, sys, tempfile, unittest

LINT = os.path.join(os.path.dirname(__file__), "..", ".claude", "skills", "agentic-delivery", "scripts", "clock_lint.py")
SRC = "SUNSET = date(2026, 10, 20)\n\n\ndef live():\n    return date.today() < SUNSET\n"


def lint(*a):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "rule_gate.py")
        with open(p, "w") as fh:
            fh.write(SRC)
        r = subprocess.run([sys.executable, LINT, "--today", "2026-10-14", *a, p], capture_output=True, text=True)
        return r.returncode, r.stdout.replace(p, "F")


class Bombs(unittest.TestCase):
    def test_urgent_warns_without_failing(self):
        rc, out = lint()
        self.assertIn("F:1: date literal compared with real clock; expires 2026-10-20 (URGENT: 6d)", out)
        self.assertEqual(rc, 0)

    def test_strict_fails(self):
        self.assertEqual(lint("--strict")[0], 1)

    def test_no_skip_line_for_scanned_file(self):
        self.assertNotIn("SKIP", lint()[1])

    def test_bad_today_exits_2_without_traceback(self):
        r = subprocess.run([sys.executable, LINT, "--today", "2026-13-45"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--today needs YYYY-MM-DD", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_false_positives_stay_quiet(self):
        for src in ('created = "2020-01-01"\nprint(datetime.now())\n',  # past fixture near a read
                    "DAY = date(2026, 10, 20)\nok = date.today() < DAYS\n",  # bare-word prefix
                    "SUNSET = date(2026, 10, 20)\nlog(SUNSET, date.today())\n"):  # no comparison
            global SRC
            old, SRC = SRC, src
            try:
                self.assertEqual(lint(), (0, ""), src)
            finally:
                SRC = old


class PreflightWiring(unittest.TestCase):
    def test_advisory_silent_outside_repo_or_without_base(self):
        sys.path.insert(0, os.path.dirname(LINT))
        import preflight
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                self.assertEqual(preflight.clock_advisory(), [])
                self.assertEqual(preflight.clock_advisory("no-such-ref"), [])
                self.assertIn("clock_advisory(", inspect.getsource(preflight.main))  # wired into the default run
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
