#!/usr/bin/env python3
"""Offline tests for token_ratchet.py using synthetic session JSONL."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/skills/agentic-ceo/scripts/token_ratchet.py"
sys.path.insert(0, str(SCRIPT.parent))
import token_ratchet as trt  # noqa: E402


def turn(rid, ts, inp=100, out=50):
    return json.dumps({"type": "assistant", "requestId": rid, "timestamp": ts,
                       "message": {"usage": {"input_tokens": inp, "output_tokens": out}}})


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


class Ratchet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "sub").mkdir()
        # main: 150 in window; nested subagent: 150; old turn before window: ignored
        (self.d / "s.jsonl").write_text(turn("a", "2026-10-02T00:00:00Z") + "\nnot json\n"
                                        + turn("old", "2026-01-01T00:00:00Z", 9999, 9999) + "\n")
        (self.d / "sub" / "agent.jsonl").write_text(turn("b", "2026-10-03T00:00:00Z") + "\n")
        self.base = str(self.d / "base.json")
        self.common = ["--dir", str(self.d), "--baseline", self.base, "--since", "2026-10-01T00:00:00Z"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_measure_window_and_subagents(self):
        since = trt.tr.parse_timestamp("2026-10-01T00:00:00Z")
        self.assertEqual(trt.measure(str(self.d), since), (300.0, 2))

    def test_write_then_ok_then_breach_then_warn(self):
        self.assertEqual(run(*self.common, "--prs", "2", "--write-baseline").returncode, 0)
        self.assertEqual(json.loads(Path(self.base).read_text())["tokens_per_pr"], 150.0)
        self.assertEqual(run(*self.common, "--prs", "2").returncode, 0)
        self.assertEqual(run(*self.common, "--prs", "1").returncode, 1)  # 300/PR = +100%
        w = run(*self.common, "--prs", "1", "--warn")
        self.assertEqual(w.returncode, 0)
        self.assertIn("WARN", w.stdout)

    def test_write_baseline_needs_force_to_overwrite(self):
        self.assertEqual(run(*self.common, "--prs", "2", "--write-baseline").returncode, 0)
        self.assertEqual(run(*self.common, "--prs", "1", "--write-baseline").returncode, 2)
        self.assertEqual(json.loads(Path(self.base).read_text())["tokens_per_pr"], 150.0)
        self.assertEqual(run(*self.common, "--prs", "1", "--write-baseline", "--force").returncode, 0)
        self.assertEqual(json.loads(Path(self.base).read_text())["tokens_per_pr"], 300.0)

    def test_zero_prs_and_bad_baseline_cannot_check(self):
        self.assertEqual(run(*self.common, "--prs", "0").returncode, 2)
        self.assertEqual(run(*self.common, "--prs", "2").returncode, 2)  # no baseline yet
        Path(self.base).write_text('{"tokens_per_pr": 0}')
        self.assertEqual(run(*self.common, "--prs", "2").returncode, 2)

    def test_ratchet_math(self):
        self.assertEqual(trt.ratchet(120, 100, 20), (20.0, False))
        self.assertTrue(trt.ratchet(121, 100, 20)[1])
        with self.assertRaises(ValueError):
            trt.ratchet(1, 0, 20)


if __name__ == "__main__":
    unittest.main()
