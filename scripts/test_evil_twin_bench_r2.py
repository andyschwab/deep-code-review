#!/usr/bin/env python3
"""Tests for scripts/evil_twin_bench_r2.py: corpus shape, calibration set disjoint from the scored corpus, the precise KILLED rule, judge
parser, preregistered verdict(), the frozen-file hashes, and cache-only replays (scored run and calibration) that must reproduce the
committed numbers. Offline: a cache miss raises instead of calling the network."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evil_twin_bench as E  # noqa: E402
import evil_twin_bench_r2 as R  # noqa: E402

CASES = E.parse_cases((R.D / "cases.txt").read_text())
CAL = E.parse_cases((R.D / "calibration/cases.txt").read_text())


def arms(n_rec=0.5, p_lo=0.8, p_fk=0.0, n_fk=0.0, unparsed=0):
    a = {k: {"recall": 0.5, "recall_ci": (0.4, 0.6), "false_kill": 0.0, "unparsed": unparsed} for k in R.ARMS}
    a["none"].update(recall=n_rec, false_kill=n_fk)
    a["perun"].update(recall_ci=(p_lo, 0.95), false_kill=p_fk)
    return a


def con(lo):
    return {"perun-brainstorm": {"lo": lo}}


def shingles(t, n=10):
    w = t.lower().split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


class Corpus(unittest.TestCase):
    def test_shape(self):
        self.assertEqual(len(CASES), 36)
        self.assertEqual(sum(c["kind"] == "control" for c in CASES), 12)
        self.assertTrue(all(c["key"].startswith("none") for c in CASES if c["kind"] == "control"))
        self.assertFalse(any(c["key"].startswith("none") for c in CASES if c["kind"] == "flawed"))
        self.assertEqual(len({c["id"] for c in CASES}), 36)

    def test_calibration_is_disjoint_and_all_flawed(self):
        self.assertEqual((len(CAL), {c["kind"] for c in CAL}), (8, {"flawed"}))
        self.assertFalse({c["id"] for c in CAL} & {c["id"] for c in CASES})
        scored = set().union(*(shingles(c["proposal"]) for c in CASES))
        self.assertFalse(any(shingles(c["proposal"]) & scored for c in CAL))

    def test_key_never_reaches_a_generation_prompt(self):
        for c in CASES:
            for a in R.ARMS:
                self.assertNotIn(c["key"], R.system(a) + E.user_prompt(c))

    def test_arm_texts_are_the_r1_snapshots(self):
        self.assertEqual(R.arm_text("none"), "")
        self.assertTrue(R.arm_text("perun").startswith("---\nname: idea-critic"))
        self.assertIn("recommendation", R.arm_text("brainstorm"))


class Judge(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(R.parse_judge("REASON: x\nFLAW_CAUGHT: 1\nKILLED: 0\nBLOCKED: 1"), (1, 0, 1))
        self.assertEqual(R.parse_judge("FLAW_CAUGHT: 0\nKILLED: 1\nBLOCKED: 1\nFLAW_CAUGHT: 1\nKILLED: 0\nBLOCKED: 0"), (1, 0, 0))  # last wins
        self.assertIsNone(R.parse_judge("FLAW_CAUGHT: 1\nKILLED: 0"))  # BLOCKED missing
        self.assertIsNone(R.parse_judge("no scores"))

    def test_revision_is_not_a_kill_in_the_judge_prompt(self):
        p = R.judge_prompt(CASES[0], "reply")
        for s in ("abandon, reject or cancel", "'do not approve yet'", "'revise'", "Asking for revision is NOT a kill"):
            self.assertIn(s, p)


class Verdict(unittest.TestCase):
    def test_win_tie_revert(self):
        self.assertEqual(R.verdict(arms(), con(0.05)), "WIN")
        self.assertEqual(R.verdict(arms(), con(0.0)), "TIE")
        self.assertEqual(R.verdict(arms(p_lo=0.5), con(0.2)), "REVERT")  # CI lower bound must exceed the none point
        self.assertEqual(R.verdict(arms(p_fk=0.17), con(0.2)), "REVERT")  # two more false kills than none (of 12)
        self.assertEqual(R.verdict(arms(p_fk=1 / 12), con(0.2)), "WIN")  # exactly one more is allowed

    def test_invalid_and_inconclusive(self):
        self.assertEqual(R.verdict(arms(unparsed=3), con(0.2)), "INVALID")
        self.assertEqual(R.verdict(arms(unparsed=2), con(0.2)), "WIN")
        self.assertEqual(R.verdict(arms(n_rec=0.85, p_lo=0.95), con(0.2)), "INCONCLUSIVE")
        self.assertEqual(R.verdict(arms(n_rec=0.84, p_lo=0.9), con(0.2)), "WIN")


class Frozen(unittest.TestCase):
    def test_frozen_list_matches_files_and_covers_the_drivers(self):
        listed = {}
        for line in (R.D / "SHA256-frozen.txt").read_text().splitlines():
            h, p = line.split(None, 1)
            self.assertEqual(hashlib.sha256((R.ROOT / p).read_bytes()).hexdigest(), h, p)
            listed[p] = h
        for p in ("scripts/evil_twin_bench_r2.py", "scripts/evil_twin_bench.py", "scripts/rival_eval.py", "docs/bench/evil-twin-r2-1021/cases.txt"):
            self.assertIn(p, listed)
        first = json.loads((R.D / "ledger.jsonl").read_text().splitlines()[0])
        self.assertEqual(first["event"], "preregistered")


class Replay(unittest.TestCase):
    def test_cache_only_replay_matches_committed_results(self):
        rows = R.evaluate(cache_only=True)
        res = R.build_results(rows)
        saved = json.loads((R.D / "results.json").read_text())
        self.assertEqual(json.loads(json.dumps({"results": res, "rows": rows})), saved)
        self.assertEqual(res["verdict"], saved["results"]["verdict"])

    def test_calibration_replay_is_at_or_below_the_ceiling(self):
        rows = R.evaluate(True, 4, R.D / "calibration/cases.txt", R.D / "calibration/cache", ("none",))["none"]
        self.assertLessEqual(E.mean(rows, "caught", "flawed"), 0.70)

    def test_cache_miss_raises_without_network(self):
        with self.assertRaises(RuntimeError):
            E.cached("gen", E.GEN_MODEL, "no such system", "no such user", True, 10)


if __name__ == "__main__":
    unittest.main()
