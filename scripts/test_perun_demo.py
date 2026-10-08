#!/usr/bin/env python3
"""Offline tests for perun_demo.py: planted bugs listed, catches scored, benchmark quoted or withheld."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DEMO = SCRIPTS.parent / ".claude/skills/deep-code-review/scripts/perun_demo.py"


def run(*args):
    return subprocess.run([sys.executable, str(DEMO), *args], capture_output=True, text=True)


class PerunDemo(unittest.TestCase):
    def test_default_output(self):
        r = run()
        self.assertEqual(r.returncode, 0)
        self.assertIn("Planted bugs: 6", r.stdout)
        self.assertIn("catches 6 of 6", r.stdout)
        self.assertIn("benchmark (copied from fixtures/bench-results.md): ", r.stdout)

    def test_missing_results_prints_see_docs(self):
        r = run("--results", "/nonexistent/results.md")
        self.assertIn("benchmark: see docs", r.stdout)

    def test_results_without_bluf_prints_see_docs(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text("# no summary line here, recall 0.99\n", encoding="utf-8")
            r = run("--results", str(p))
        self.assertIn("benchmark: see docs", r.stdout)
        self.assertNotIn("0.99", r.stdout)


if __name__ == "__main__":
    unittest.main()
