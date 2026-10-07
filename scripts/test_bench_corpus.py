#!/usr/bin/env python3
"""Offline tests for bench_corpus.py: split rule, findings parser, metrics, and the committed corpus' integrity."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import bench_corpus as bc  # noqa: E402
import score_review as sr  # noqa: E402

BENCH = SCRIPTS / "eval-fixtures/bench"
MAN = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))


class Split(unittest.TestCase):
    def test_deterministic_third_and_public_is_train(self):
        ids = [f"case-{i}" for i in range(12)]
        a = bc.split_ids(ids, ["pub"])
        self.assertEqual(a, bc.split_ids(list(reversed(ids)), ["pub"]))
        self.assertEqual(sum(v == "train" for k, v in a.items() if k != "pub"), 4)
        self.assertEqual(a["pub"], "train")

    def test_committed_manifest_matches_rule(self):
        real = [m["id"] for m in MAN if not m["id"].startswith("heldout-")]
        want = bc.split_ids(real, [m["id"] for m in MAN if m["id"].startswith("heldout-")])
        self.assertEqual({m["id"]: m["split"] for m in MAN}, want)
        self.assertGreaterEqual(len(real), 24)


class Parse(unittest.TestCase):
    def test_last_array_wins_and_junk_is_empty(self):
        t = 'notes [1] then [{"file":"a.py","text":"x"}]'
        self.assertEqual(bc.parse_array(t), [{"file": "a.py", "text": "x"}])
        self.assertEqual(bc.parse_array("no json here"), [])
        self.assertEqual(bc.parse_array("[{broken"), [])


class Metrics(unittest.TestCase):
    def test_strict_adjudicated_and_verified(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for cid, find, ver in [("c1", [{"file": "a.py", "text": "wrong mechanism entirely"}, {"file": "a.py", "text": "junk"}], {"0": {"verdict": "gt_same"}, "1": {"verdict": "not_a_bug"}}),
                                   ("c2", [{"file": "b.py", "text": "uses bad regex"}, {"file": "b.py", "text": "other real"}], {"1": {"verdict": "real"}})]:
                (d / cid).mkdir()
                f, m = {"c1": ("a.py", "alpha"), "c2": ("b.py", "regex")}[cid]
                (d / cid / "ground-truth.json").write_text(json.dumps({"bugs": [{"id": "B1", "file": f, "match": m, "example": m}]}))
                (d / "o").mkdir(exist_ok=True); (d / "o/perun").mkdir(exist_ok=True)
                (d / "o/perun" / f"{cid}.json").write_text(json.dumps({"findings": find, "verdicts": ver, "cost": 0.5, "seconds": 10}))
            (d / "manifest.json").write_text("[]")
            r = bc.metrics(d, ["c1", "c2"], "perun", d / "o")
            self.assertEqual((r["recall_strict"], r["recall_adjudicated"]), (0.5, 1.0))
            self.assertEqual((r["precision_strict"], r["precision_verified"]), (0.25, 0.75))
            self.assertEqual(r["cost_usd"], 1.0)


class Committed(unittest.TestCase):
    def test_train_fixtures_selftest_and_test_truth_absent(self):
        for m in MAN:
            d = BENCH / "train" / m["id"]
            if m["split"] == "test":
                self.assertFalse(d.exists(), "TEST ground truth must not be committed: " + m["id"])
            elif not m["id"].startswith("heldout-"):
                truth = json.loads((d / "ground-truth.json").read_text(encoding="utf-8"))
                self.assertTrue(sr.selftest(truth), m["id"])
                self.assertTrue((d / "change.patch").stat().st_size > 0)
            self.assertIn(m["licence"], ("MIT", "BSD-3-Clause", "Apache-2.0"))


if __name__ == "__main__":
    unittest.main()
