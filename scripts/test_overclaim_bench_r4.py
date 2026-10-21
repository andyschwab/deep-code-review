#!/usr/bin/env python3
"""Tests for scripts/overclaim_bench_r4.py: corpus and old arm are byte-identical to R3, the R4 rule is inserted and within 60 words, verdict(). Offline."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overclaim_bench_r3 as R3  # noqa: E402
import overclaim_bench_r4 as R  # noqa: E402


def arms(new_over=0.10, sp_over=0.10, old_over=0.15, new_under=0.1, sp_under=0.1, old_under=0.1, unparsed=0):
    a = {k: {"over_rate": 0.1, "under_rate": 0.1, "unparsed": unparsed} for k in R.ARMS}
    a["perun_new"].update(over_rate=new_over, under_rate=new_under)
    a["superpowers"].update(over_rate=sp_over, under_rate=sp_under)
    a["perun_old"].update(over_rate=old_over, under_rate=old_under)
    return a


class Inputs(unittest.TestCase):
    def test_corpus_and_old_arm_are_the_r3_files(self):
        for f in ("cases.txt", "perun-old-arm.txt"):
            self.assertEqual((R.D / f).read_bytes(), (R3.D / f).read_bytes())

    def test_new_arm_is_old_arm_plus_rule(self):
        old, new = (R.D / "perun-old-arm.txt").read_text(), (R.D / "perun-new-arm.txt").read_text()
        head = "2. **Verify, don't trust.** "
        rule = new[len(head):new.index("Run the gates;")]
        self.assertTrue(new.startswith(head) and old.startswith(head))
        self.assertEqual(head + new[new.index("Run the gates;"):], old)
        self.assertLessEqual(len(rule.split()), 60)


class Recompute(unittest.TestCase):
    """per-case-labels.json (case id -> labels, no text) reproduces every number in the results files, bootstrap seed 2. Offline."""

    def test_labels_reproduce_results(self):
        labels = json.loads((R.D / "per-case-labels.json").read_text())
        ids = [c["id"] for c in R.O.parse_cases((R.D / "cases.txt").read_text())]
        for model, fname in (("Mistral-Small-3.2:24b", "results-Mistral-Small-3.2-24b.json"), ("Qwen3.5-397B-A17B", "results-Qwen3.5-397B-A17B.json")):
            res = json.loads((R.D / fname).read_text())
            per = {a: [labels[model][a][i] for i in ids] for a in R.ARMS}
            for a, pc in per.items():
                for k in ("over", "under"):
                    self.assertAlmostEqual(R.O.rate(pc, k), res["arms"][a][k + "_rate"], places=12)
                    self.assertTrue(all(abs(x - y) < 1e-12 for x, y in zip(R.O.boot_ci(pc, k, seed=R.SEED), res["arms"][a][k + "_ci"])))
            for key, c in res["contrasts"].items():
                a, b = key.split("-")
                for k in ("over", "under"):
                    got = R.O.boot_diff(per[a], per[b], k, seed=R.SEED)
                    self.assertTrue(all(abs(x - c[k][f]) < 1e-12 for x, f in zip(got, ("diff", "lo", "hi"))), (model, key, k))


class Verdict(unittest.TestCase):
    def test_keep_needs_both_over_conditions_and_guardrail(self):
        self.assertEqual(R.verdict(arms())["verdict"], "KEEP")  # new == superpowers (<=) and < old
        self.assertEqual(R.verdict(arms(new_over=0.11))["verdict"], "REVERT")  # worse than superpowers
        self.assertEqual(R.verdict(arms(old_over=0.10))["verdict"], "REVERT")  # not below perun_old
        self.assertEqual(R.verdict(arms(new_under=0.16))["verdict"], "REVERT")  # +6 under vs superpowers
        self.assertEqual(R.verdict(arms(new_under=0.15))["verdict"], "KEEP")  # exactly +5 passes
        self.assertEqual(R.verdict(arms(new_under=0.12, old_under=0.06))["verdict"], "REVERT")  # +6 vs perun_old

    def test_invalid_overrides(self):
        self.assertEqual(R.verdict(arms(unparsed=4))["verdict"], "INVALID")


if __name__ == "__main__":
    unittest.main()
