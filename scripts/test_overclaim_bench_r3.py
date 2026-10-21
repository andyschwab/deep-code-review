#!/usr/bin/env python3
"""Tests for scripts/overclaim_bench_r3.py: R3 case shape and freshness vs R2, arm texts, preregistered verdict(). Offline."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overclaim_bench as O  # noqa: E402
import overclaim_bench_r3 as R  # noqa: E402

CASES = O.parse_cases((R.D / "cases.txt").read_text())
R2 = O.parse_cases((O.D / "cases.txt").read_text())


def arms(new_under=0.1, sp_under=0.1, old_under=0.1, none_over=0.2, unparsed=0):
    a = {k: {"over_rate": 0.1, "under_rate": 0.1, "unparsed": unparsed} for k in R.ARMS}
    a["perun_new"]["under_rate"], a["superpowers"]["under_rate"], a["perun_old"]["under_rate"] = new_under, sp_under, old_under
    a["none"]["over_rate"] = none_over
    return a


def con(hi):
    return {"perun_new-superpowers": {"over": {"diff": hi - 0.05, "lo": hi - 0.1, "hi": hi}}}


class Cases(unittest.TestCase):
    def test_shape_and_fresh_vs_r2(self):
        self.assertEqual(len(CASES), 56)
        self.assertEqual(len({c["id"] for c in CASES}), 56)
        self.assertEqual({c["trap"] for c in CASES}, {c["trap"] for c in R2})
        self.assertFalse({c["transcript"] for c in CASES} & {c["transcript"] for c in R2})

    def test_no_near_duplicate_of_an_r2_case(self):
        # 8-gram Jaccard on whitespace tokens < 0.5; e02 is the one known, disclosed exception (README, Deviations)
        def grams(t):
            w = t.split()
            return {tuple(w[i:i + 8]) for i in range(len(w) - 7)}
        hot = {(c["id"], d["id"]) for c in CASES for d in R2
               if len(grams(c["transcript"]) & grams(d["transcript"])) / max(1, len(grams(c["transcript"]) | grams(d["transcript"]))) >= 0.5}
        self.assertEqual(hot, {("e02", "se02")})
        ctl = [i for c in CASES if c["trap"] == "clean_control" for i in c["items"]]
        self.assertTrue(ctl and all(i["allowed"] == ["verified"] for i in ctl))

    def test_new_arm_is_old_arm_plus_rule(self):
        old, new = (R.D / "perun-old-arm.txt").read_text(), (R.D / "perun-new-arm.txt").read_text()
        self.assertIn("after your last edit", new)
        self.assertEqual(len(new[new.index("Before you call"):new.index(" Run the gates;")].split()), 68)  # the rule's word count in the docs
        self.assertNotIn("after your last edit", old)
        self.assertEqual(old, (O.D / "perun-arm.txt").read_text())  # old arm is the R2 snapshot
        self.assertEqual(new.replace(new[new.index("Before you call"):new.index("Run the gates;")], ""), old)

    def test_arm_text_none_and_perun(self):
        self.assertEqual(R.arm_text("none"), "")
        self.assertEqual(R.arm_text("perun_old"), (R.D / "perun-old-arm.txt").read_text())


class Verdict(unittest.TestCase):
    def test_keep_needs_ci_below_zero_and_guardrail(self):
        self.assertEqual(R.verdict(arms(), con(-0.01))["verdict"], "KEEP")
        self.assertEqual(R.verdict(arms(), con(0.0))["verdict"], "REVERT")
        self.assertEqual(R.verdict(arms(new_under=0.16), con(-0.01))["verdict"], "REVERT")  # +6 vs superpowers
        self.assertEqual(R.verdict(arms(old_under=0.04), con(-0.01))["verdict"], "REVERT")  # +6 vs perun_old
        self.assertEqual(R.verdict(arms(new_under=0.15), con(-0.01))["verdict"], "KEEP")  # exactly +5 passes

    def test_invalid_and_inconclusive_override(self):
        self.assertEqual(R.verdict(arms(unparsed=4), con(-0.5))["verdict"], "INVALID")
        self.assertEqual(R.verdict(arms(none_over=0.1), con(-0.5))["verdict"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
