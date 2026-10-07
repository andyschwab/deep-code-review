#!/usr/bin/env python3
"""Offline tests for score_review.py: canaries, dedup, FP budget, and the pinned fixture."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import score_review as sr  # noqa: E402

FIX = SCRIPTS / "eval-fixtures/heldout/pr1354-ops-scripts"
TRUTH = json.loads((FIX / "ground-truth.json").read_text(encoding="utf-8"))


class ScoreReview(unittest.TestCase):
    def test_canaries(self):
        self.assertTrue(sr.selftest(TRUTH))

    def test_plausible_but_wrong_review_is_a_miss(self):
        wrong = [{"file": "clean_finished.sh", "text": "script lacks a usage message and unit tests"}]
        r = sr.score(TRUTH, wrong)
        self.assertEqual((r["recall"], r["unmatched"]), (0.0, 1))

    def test_dedup_and_partial(self):
        f = [{"file": "x/land_train.sh", "text": "merge failure is swallowed"}, {"file": "land_train.sh", "text": "|| true hides exit"}]
        r = sr.score(TRUTH, f)
        self.assertEqual((r["hit"], r["precision"]), (["B4"], 1.0))
        self.assertAlmostEqual(r["recall"], 1 / 6, places=3)

    def test_fixture_integrity(self):
        patch = (FIX / "prefix.patch").read_text(encoding="utf-8")
        for b in TRUTH["bugs"]:
            self.assertIn(b["file"], patch)

    def test_cli_fp_budget(self):
        fp = Path(tempfile.mkdtemp()) / "f.json"
        fp.write_text(json.dumps([{"file": "a.sh", "text": "x"}, {"file": "b.sh", "text": "y"}]))
        try:
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "score_review.py"), str(FIX / "ground-truth.json"), str(fp), *a],
                                            capture_output=True, text=True).returncode
            self.assertEqual((run(), run("--max-fp", "2"), run("--max-fp", "1")), (0, 0, 1))
        finally:
            fp.unlink()


if __name__ == "__main__":
    unittest.main()
