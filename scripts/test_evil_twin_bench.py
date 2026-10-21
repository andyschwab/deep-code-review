#!/usr/bin/env python3
"""Tests for scripts/evil_twin_bench.py: corpus shape, judge parser, preregistered verdict(), and a cache-only replay of the committed run
that must reproduce results.json exactly. Offline: a cache miss raises instead of calling the network."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evil_twin_bench as E  # noqa: E402

CASES = E.parse_cases((E.D / "cases.txt").read_text())


def arms(n_rec=0.5, p_lo=0.8, p_fk=0.0, n_fk=0.0, b_fk=0.0, unparsed=0):
    a = {k: {"recall": 0.5, "recall_ci": (0.4, 0.6), "false_kill": 0.0, "unparsed": unparsed} for k in E.ARMS}
    a["none"].update(recall=n_rec, false_kill=n_fk)
    a["perun"].update(recall_ci=(p_lo, 0.95), false_kill=p_fk)
    a["brainstorm"].update(false_kill=b_fk)
    return a


def con(lo):
    return {"perun-brainstorm": {"lo": lo}}


class Corpus(unittest.TestCase):
    def test_shape(self):
        self.assertEqual(len(CASES), 30)
        self.assertEqual(sum(c["kind"] == "control" for c in CASES), 6)
        self.assertTrue(all(c["key"].startswith("none") for c in CASES if c["kind"] == "control"))
        self.assertFalse(any(c["key"].startswith("none") for c in CASES if c["kind"] == "flawed"))

    def test_key_never_reaches_a_generation_prompt(self):
        for c in CASES:
            for a in E.ARMS:
                self.assertNotIn(c["key"], E.system(a) + E.user_prompt(c))

    def test_bad_block_raises(self):
        with self.assertRaises(ValueError):
            E.parse_cases("=== x | flawed\nno proposal here")
        with self.assertRaises(ValueError):
            E.parse_cases("=== x | other\nPROPOSAL: a\nKEY: b")

    def test_arm_texts(self):
        self.assertEqual(E.arm_text("none"), "")
        self.assertTrue(E.arm_text("perun").startswith("---\nname: idea-critic"))
        self.assertIn("recommendation", E.arm_text("brainstorm"))


class Judge(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(E.parse_judge("REASON: x\nFLAW_CAUGHT: 1\nKILLED: 0"), (1, 0))
        self.assertEqual(E.parse_judge("FLAW_CAUGHT: 0\nKILLED: 1\nFLAW_CAUGHT: 1\nKILLED: 1"), (1, 1))  # last wins
        self.assertIsNone(E.parse_judge("FLAW_CAUGHT: 1"))
        self.assertIsNone(E.parse_judge("no scores"))


class Verdict(unittest.TestCase):
    def test_win_tie_revert(self):
        self.assertEqual(E.verdict(arms(), con(0.05)), "WIN")
        self.assertEqual(E.verdict(arms(), con(0.0)), "TIE")
        self.assertEqual(E.verdict(arms(p_lo=0.5), con(0.2)), "REVERT")  # CI lower bound must exceed the none point
        self.assertEqual(E.verdict(arms(p_fk=0.34), con(0.2)), "REVERT")  # two more false kills than none
        self.assertEqual(E.verdict(arms(p_fk=1 / 6), con(0.2)), "WIN")  # one more is allowed

    def test_invalid_and_inconclusive(self):
        self.assertEqual(E.verdict(arms(unparsed=3), con(0.2)), "INVALID")
        self.assertEqual(E.verdict(arms(unparsed=2), con(0.2)), "WIN")
        self.assertEqual(E.verdict(arms(n_rec=0.9, p_lo=0.95), con(0.2)), "INCONCLUSIVE")


class Replay(unittest.TestCase):
    def test_cache_only_replay_matches_committed_results(self):
        rows, res = E.evaluate(cache_only=True)
        saved = json.loads((E.D / "results.json").read_text())
        self.assertEqual(json.loads(json.dumps({"results": res, "rows": rows})), saved)
        self.assertEqual(res["verdict"], saved["results"]["verdict"])

    def test_cache_miss_raises_without_network(self):
        with self.assertRaises(RuntimeError):
            E.cached("gen", E.GEN_MODEL, "no such system", "no such user", True, 10)


if __name__ == "__main__":
    unittest.main()
