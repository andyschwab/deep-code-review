#!/usr/bin/env python3
"""Offline tests for derived_numbers.py: CLI exit codes, --fix, the real repo's docs, and the dcr-gates.sh wiring."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, ".claude/skills/deep-code-review/scripts/derived_numbers.py")
GATES = os.path.join(ROOT, ".claude/skills/deep-code-review/templates/dcr-gates.sh")


def run(*args, **kw):
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, **kw)
    return p.returncode, p.stdout + p.stderr


class DerivedNumbers(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
        self.doc = os.path.join(self.d, "README.md")

    def put(self, text):
        with open(self.doc, "w", encoding="utf-8") as f:
            f.write(text)

    def test_selftest(self):
        self.assertEqual(run("--selftest")[0], 0)

    def test_count_of_real_files_drifts_then_fixes(self):
        for n in ("a.txt", "b.txt"):
            open(os.path.join(self.d, n), "w").close()
        self.put("We ship <!-- derived: ls *.txt | wc -l -->5 text files.\n")
        rc, out = run(self.d)
        self.assertEqual(rc, 1)
        self.assertIn("README.md:1: drift: doc says 5", out)
        self.assertIn("prints 2", out)
        self.assertEqual(run("--fix", self.d)[0], 0)
        self.assertEqual(Path(self.doc).read_text(), "We ship <!-- derived: ls *.txt | wc -l -->2 text files.\n")
        self.assertEqual(run(self.d)[0], 0)

    def test_no_markers_passes(self):
        self.put("nothing derived here\n")
        self.assertEqual(run(self.d), (0, "derived_numbers: 0 claim(s), 0 finding(s)\n"))

    def test_failing_command_is_a_finding_and_fix_leaves_doc_alone(self):
        self.put("<!-- derived: exit 3 -->7 x\n")
        self.assertEqual(run("--fix", self.d)[0], 1)
        self.assertEqual(Path(self.doc).read_text(), "<!-- derived: exit 3 -->7 x\n")

    def test_bad_args_exit_2(self):
        self.assertEqual(run("--nope")[0], 2)

    def test_repo_docs_have_no_drift(self):
        rc, out = run(ROOT)
        self.assertEqual(rc, 0, out)
        self.assertNotIn(" 0 claim(s)", out, "dogfood: this repo's docs must carry at least one bound claim")


class GateRunnerWiring(unittest.TestCase):
    def test_runner_runs_the_gate_selftests_it_and_can_opt_out(self):
        text = Path(GATES).read_text(encoding="utf-8")
        self.assertIn("derived_numbers.py", text.split("SELFTEST_SCRIPTS=(")[1].split(")")[0])
        self.assertIn('${DCR_DERIVED_NUMBERS:-1}', text, "on by default")
        self.assertIn("dcr-gates: derived_numbers PASS", text)

    def test_installed_runner_fails_on_stale_doc_and_passes_when_off(self):
        d = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
        sk = os.path.join(d, ".claude/skills/deep-code-review")
        os.makedirs(os.path.join(d, "scripts"))
        os.makedirs(sk)
        Path(sk, "SKILL.md").write_text("---\nname: deep-code-review\n---\n")
        subprocess.run(["cp", "-R", os.path.join(ROOT, ".claude/skills/deep-code-review/scripts"), sk], check=True)
        subprocess.run(["cp", GATES, os.path.join(d, "scripts/dcr-gates.sh")], check=True)
        Path(d, "README.md").write_text("<!-- derived: echo 4 -->3 tests\n")
        for c in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "x"]):
            subprocess.run(["git", "-C", d, *c], check=True, capture_output=True)
        env = {**os.environ, "BASE_SHA": "", "HEAD_SHA": ""}
        p = subprocess.run(["bash", os.path.join(d, "scripts/dcr-gates.sh")], capture_output=True, text=True, env=env)
        self.assertIn("dcr-gates: derived_numbers FAIL", p.stderr)
        self.assertIn("drift: doc says 3", p.stderr)
        self.assertNotEqual(p.returncode, 0)
        p = subprocess.run(["bash", os.path.join(d, "scripts/dcr-gates.sh")], capture_output=True, text=True, env={**env, "DCR_DERIVED_NUMBERS": "0"})
        self.assertNotIn("derived_numbers PASS", p.stdout)
        self.assertNotIn("derived_numbers FAIL", p.stderr)
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
