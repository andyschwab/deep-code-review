#!/usr/bin/env python3
"""Offline tests for derived_numbers.py: CLI exit codes, --fix, injection safety, encodings, the real repo's docs, and the dcr-gates.sh wiring."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, ".claude/skills/deep-code-review/scripts/derived_numbers.py")
GATES = os.path.join(ROOT, ".claude/skills/deep-code-review/templates/dcr-gates.sh")


def run(*args):
    p = subprocess.run([sys.executable, "-B", TOOL, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class DerivedNumbers(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.doc = self.d / "README.md"
        for n in ("a.txt", "b.txt"):
            (self.d / n).write_text("x\ny\n")

    def put(self, data):
        self.doc.write_bytes(data if isinstance(data, bytes) else data.encode())

    def test_selftest(self):
        self.assertEqual(run("--selftest")[0], 0)

    def test_count_of_real_files_drifts_then_fixes(self):
        self.put("We ship <!-- derived: files *.txt -->5 text files.\n")
        rc, out = run(str(self.d))
        self.assertEqual(rc, 1)
        self.assertIn("README.md:1: drift: doc says 5", out)
        self.assertIn("gives 2", out)
        self.assertEqual(run("--fix", str(self.d))[0], 0)
        self.assertEqual(self.doc.read_text(), "We ship <!-- derived: files *.txt -->2 text files.\n")
        self.assertEqual(run(str(self.d))[0], 0)

    def test_no_markers_passes(self):
        self.put("nothing derived here\n")
        self.assertEqual(run(str(self.d)), (0, "derived_numbers: 0 claim(s), 0 finding(s)\n"))

    def test_injection_attempts_never_execute(self):
        for evil in ("touch PWNED", "files *.txt; touch PWNED", "$(touch PWNED)", "`touch PWNED`", "echo 2 | touch PWNED", "lines a.txt && touch PWNED"):
            self.put(f"<!-- derived: {evil} -->2 x\n")
            rc, out = run("--fix", str(self.d))
            self.assertEqual(rc, 1, evil)
            self.assertIn("bad marker", out)
            self.assertEqual(self.doc.read_text(), f"<!-- derived: {evil} -->2 x\n", "fix must not touch a bad marker")
            self.assertFalse((self.d / "PWNED").exists() or Path("PWNED").exists(), f"executed: {evil}")

    def test_paths_stay_in_repo_and_skip_symlinks(self):
        outside = self.d.parent / "outside-secret.txt"
        outside.write_text("secret\n")
        (self.d / "link.txt").symlink_to(outside)
        for spec in ("lines ../outside-secret.txt", "lines /etc/hosts", "lines link.txt", "grep-count x link.txt", "json-len link.txt k"):
            self.put(f"<!-- derived: {spec} -->1\n")
            rc, out = run(str(self.d))
            self.assertEqual(rc, 1, spec)
            self.assertIn("bad marker", out)
        (self.d / "real.md").write_text("<!-- derived: files *.txt -->9\n")
        (self.d / "linked.md").symlink_to(self.d / "real.md")
        self.put("plain\n")
        self.assertEqual(run("--fix", str(self.d))[0], 0)
        self.assertTrue((self.d / "linked.md").is_symlink(), "a symlinked doc is left a symlink")
        self.assertIn("-->2", (self.d / "real.md").read_text())  # a.txt, b.txt; the symlink is not counted

    def test_counters(self):
        (self.d / "d.json").write_text('{"k": {"items": [1, 2, 3]}, "n": 4}')
        self.put("<!-- derived: lines a.txt -->2 <!-- derived: grep-count x a.txt -->1 <!-- derived: json-len d.json k.items -->3\n")
        self.assertEqual(run(str(self.d))[0], 0)
        self.put("<!-- derived: json-len d.json n -->4\n")
        self.assertEqual(run(str(self.d))[0], 1)

    def test_non_utf8_markdown_survives_fix(self):
        self.put(b"caf\xe9 <!-- derived: files *.txt -->9 \xff\n")
        self.assertEqual(run("--fix", str(self.d))[0], 0)
        self.assertEqual(self.doc.read_bytes(), b"caf\xe9 <!-- derived: files *.txt -->2 \xff\n")

    def test_crlf_survives_fix(self):
        self.put(b"a\r\n<!-- derived: files *.txt -->9\r\nb\r\n")
        self.assertEqual(run("--fix", str(self.d))[0], 0)
        self.assertEqual(self.doc.read_bytes(), b"a\r\n<!-- derived: files *.txt -->2\r\nb\r\n")

    def test_comma_or_period_after_the_number_is_not_part_of_it(self):
        self.put("Two files <!-- derived: files *.txt -->2, then more. <!-- derived: files *.txt -->2.\n")
        self.assertEqual(run(str(self.d))[0], 0)
        self.put("<!-- derived: files *.txt -->9, ok\n")
        self.assertEqual(run("--fix", str(self.d))[0], 0)
        self.assertEqual(self.doc.read_text(), "<!-- derived: files *.txt -->2, ok\n")
        self.put("<!-- derived: files *.txt -->2.5 files\n")
        self.assertIn("no number", run(str(self.d))[1])

    def test_code_is_ignored(self):
        self.put("````md\n```\n<!-- derived: files *.txt -->9\n```\n````\n    <!-- derived: files *.txt -->9\n``x ` <!-- derived: files *.txt -->9 ``\n")
        self.assertEqual(run(str(self.d)), (0, "derived_numbers: 0 claim(s), 0 finding(s)\n"))

    def test_vendored_dirs_skipped(self):
        (self.d / "node_modules").mkdir()
        (self.d / "node_modules" / "x.md").write_text("<!-- derived: files *.txt -->9\n")
        self.assertEqual(run(str(self.d))[0], 0)

    def test_pathological_glob_is_a_bad_marker_not_a_hang(self):
        for i in range(1000):
            (self.d / f"{'a' * 60}{i}.txt").write_text("x")
        self.put(f"<!-- derived: files {'**a' * 8}**Z -->1\n")
        t0 = time.monotonic()
        rc, out = run(str(self.d))
        self.assertLess(time.monotonic() - t0, 5)
        self.assertEqual(rc, 1)
        self.assertIn("wildcards", out)
        self.put("<!-- derived: files **a**a**a**Z -->0\n")  # at the cap: runs, linear
        t0 = time.monotonic()
        self.assertEqual(run(str(self.d))[0], 0)
        self.assertLess(time.monotonic() - t0, 5)

    def test_deeply_nested_json_is_a_finding(self):
        (self.d / "deep.json").write_text("[" * 200000)
        self.put("<!-- derived: json-len deep.json 0 -->1\n")
        rc, out = run(str(self.d))
        self.assertEqual(rc, 1)
        self.assertIn("bad marker", out)

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
        Path(d, "README.md").write_text("<!-- derived: files *.zzz -->3 tests\n")
        Path(d, ".gitignore").write_text("__pycache__/\n")  # CI leaves .pyc in the copied scripts dir
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
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
