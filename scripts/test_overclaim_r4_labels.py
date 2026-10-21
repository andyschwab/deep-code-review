#!/usr/bin/env python3
"""Tests for scripts/overclaim_r4_labels.py: deterministic output, a real cache miss raises "cache miss" with no fetch and no file written,
and (when the local cache exists) the committed file. Offline. The last test skips without the local generation cache."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overclaim_bench as O  # noqa: E402
import overclaim_r4_labels as L  # noqa: E402

STATUS = "STATUS A: verified\nSTATUS B: unverified\n"
SCRIPT = Path(L.__file__)


class Labels(unittest.TestCase):
    def setUp(self):
        self.saved = (O.generate, O.arm_text, O.chat, O.MODEL, O.CACHE, O.fetch, L.R3.D, L.R3.ARMS)

    def tearDown(self):
        O.generate, O.arm_text, O.chat, O.MODEL, O.CACHE, O.fetch, L.R3.D, L.R3.ARMS = self.saved

    def test_deterministic_and_shaped(self):
        O.generate = lambda arm, c: {"text": STATUS}  # canned generation: no cache, no network
        a, b = L.dumps(L.build()), L.dumps(L.build())
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("}\n"))
        out = L.build()
        self.assertEqual(list(out), list(L.MODELS))
        self.assertEqual(set(out[L.MODELS[0]]), set(L.R.ARMS))
        self.assertEqual(len(out[L.MODELS[0]]["perun_new"]), 56)

    def test_empty_cache_raises_cache_miss_and_writes_nothing(self):
        def no_fetch(*_a, **_k):
            raise AssertionError("network fetch attempted")
        with tempfile.TemporaryDirectory() as d:
            O.CACHE, O.fetch = Path(d) / "cache", no_fetch
            out = Path(d) / "labels.json"
            with self.assertRaisesRegex(RuntimeError, "cache miss"):
                L.main(out)
            self.assertFalse(out.exists())
            self.assertFalse((Path(d) / "cache").exists())  # nothing was cached either
            with self.assertRaisesRegex(RuntimeError, "cache miss"):
                L.cached_arm_text("superpowers")  # the rival loader does not fetch

    def test_script_with_empty_overclaim_cache_fails_and_leaves_committed_file(self):
        committed = L.R.D / "per-case-labels.json"
        before = committed.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPT)], env={**os.environ, "OVERCLAIM_CACHE": d}, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cache miss", r.stderr)
        self.assertEqual(committed.read_bytes(), before)


class Committed(unittest.TestCase):
    def test_committed_file_matches_cache_when_present(self):
        if not (O.CACHE / "gen" / "perun_new").is_dir() or not (O.CACHE / "rivals" / "superpowers.md").is_file():
            self.skipTest("no local generation cache")
        self.assertEqual((L.R.D / "per-case-labels.json").read_text(), L.dumps(L.build()))


if __name__ == "__main__":
    unittest.main()
