#!/usr/bin/env python3
"""Tests for scripts/bizops_fab_bench.py: edit application, usefulness checks, bait file shape, control arithmetic. Offline."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bizops_fab_bench as B  # noqa: E402

BAITS = json.loads((B.D / "baits.json").read_text())


class Edit(unittest.TestCase):
    def test_edit_changes_only_the_edited_arm(self):
        s = B.systems("alpha beta gamma", [["beta", "BETA"]])
        self.assertEqual((s["CURRENT"], s["EDITED"]), ("alpha beta gamma", "alpha BETA gamma"))

    def test_missing_or_repeated_anchor_fails(self):
        with self.assertRaises(ValueError):
            B.systems("alpha", [["zzz", "x"]])
        with self.assertRaises(ValueError):
            B.systems("beta beta", [["beta", "x"]])


class Useful(unittest.TestCase):
    long = "Recommend taking plan A. " + "word " * 100

    def test_call_needs_length_and_decision_word(self):
        self.assertTrue(B.useful({"kind": "S"}, self.long)[0])
        self.assertFalse(B.useful({"kind": "S"}, "Recommend A.")[0])
        self.assertFalse(B.useful({"kind": "S"}, "xyz " * 200)[0])

    def test_control_needs_every_expected_figure(self):
        c = {"kind": "K", "expect": ["\\b14\\b", "\\b8\\b"]}
        self.assertTrue(B.useful(c, self.long + " 14 months, start in 8")[1])
        self.assertFalse(B.useful(c, self.long + " 14 months")[1])


class Baits(unittest.TestCase):
    def test_shape_and_disjoint_ids(self):
        ids = [c["id"] for s in ("cal", "heldout") for c in BAITS[s]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in ("cal", "heldout"):
            self.assertTrue({"S", "C", "A", "K"} <= {c["kind"] for c in BAITS[s]})
        for c in BAITS["heldout"]:
            self.assertEqual("sym" in c, c["kind"] == "A")
            self.assertEqual("expect" in c, c["kind"] == "K")

    def test_prompts_not_reused_from_differentiator_bench(self):
        old = json.loads((B.ROOT / "docs/bench/differentiator-1019/baits.json").read_text())
        seen = {c["prompt"] for s in ("cal", "heldout") for c in old[s]}
        self.assertFalse(seen & {c["prompt"] for s in ("cal", "heldout") for c in BAITS[s]})

    def test_control_expectations_match_a_computed_answer(self):
        # yk1: LTV = 80 * 0.75 / 0.04 = 1500, LTV:CAC = 2.5; yk2: 385000 / 27500 = 14
        by = {c["id"]: c for c in BAITS["heldout"]}
        self.assertTrue(B.useful(by["yk1"], "LTV is $1,500 so LTV:CAC is 2.5")[1])
        self.assertAlmostEqual(80 * 0.75 / 0.04, 1500)
        self.assertEqual(385000 / 27500, 14)
        self.assertFalse(B.useful(by["yk2"], "about 12 months")[1])


if __name__ == "__main__":
    unittest.main()
