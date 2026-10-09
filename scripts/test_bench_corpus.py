#!/usr/bin/env python3
"""Offline tests for bench_corpus.py: split rule, parser, error paths, metrics, and the committed corpus' integrity."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
DCR = SCRIPTS.parent / ".claude/skills/deep-code-review/scripts"
sys.path.insert(0, str(DCR))
import bench_corpus as bc  # noqa: E402
import score_review as sr  # noqa: E402

BENCH = SCRIPTS / "eval-fixtures/bench"
MAN = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))
OK = {"result": '[{"file":"a.py","text":"x"}]', "total_cost_usd": 0.1, "num_turns": 2}


def proc(out, rc=0):
    return subprocess.CompletedProcess([], rc, stdout=out if isinstance(out, str) else json.dumps(out), stderr="")


def corpus_with(tmp, cid="c1", file="a.py", match="alpha"):
    (tmp / cid).mkdir(parents=True)
    (tmp / cid / "change.patch").write_text("+x\n")
    (tmp / cid / "ground-truth.json").write_text(json.dumps({"bugs": [{"id": "B1", "file": file, "bug": "b", "match": match, "example": match}]}))
    return tmp


class Split(unittest.TestCase):
    def test_deterministic_third_and_public_is_train(self):
        ids = [f"case-{i}" for i in range(12)]
        a = bc.split_ids(ids, ["pub"])
        self.assertEqual(a, bc.split_ids(list(reversed(ids)), ["pub"]))
        self.assertEqual(sum(v == "train" for k, v in a.items() if k != "pub"), 4)
        self.assertEqual(a["pub"], "train")

    def test_committed_manifest_shape(self):
        train = [m for m in MAN if m["split"] == "train"]
        test = [m for m in MAN if m["split"] == "test"]
        self.assertEqual((len(train), len(test)), (44, 90))
        self.assertTrue(all(m["id"].startswith("test-") for m in test))
        self.assertFalse(any({"fix_sha", "intro_sha"} & set(m) for m in test), "TEST SHAs point at the answer")

    def test_public_manifest_hides_test_answers_and_order(self):
        man = [{"id": f"real-{i}", "split": "test", "fix_sha": "f", "intro_sha": "i", "lang": "go", "repo_url": "u", "licence": "MIT"} for i in range(3)]
        man.append({"id": "tr", "split": "train", "fix_sha": "f", "lang": "go", "repo_url": "u", "licence": "MIT"})
        pub = bc.public_manifest(man)
        self.assertEqual(pub[0]["id"], "tr")
        self.assertEqual(pub[0]["fix_sha"], "f")
        t = pub[1:]
        self.assertEqual([m["id"] for m in t], sorted(m["id"] for m in t))
        self.assertFalse(any("real" in json.dumps(m) or "fix_sha" in m or "intro_sha" in m for m in t))
        self.assertEqual(len({m["id"] for m in t}), 3)


class Parse(unittest.TestCase):
    def test_last_array_wins_none_when_absent_and_empty_is_valid(self):
        self.assertEqual(bc.parse_array('notes [1] then [{"file":"a.py","text":"x"}]'), [{"file": "a.py", "text": "x"}])
        self.assertIsNone(bc.parse_array("no json here"))
        self.assertIsNone(bc.parse_array("[{broken"))
        self.assertEqual(bc.parse_array("nothing found: []"), [])


class ErrorPaths(unittest.TestCase):
    def err(self, **kw):
        with mock.patch.object(bc.subprocess, "run", **kw):
            return bc.claude("p", ".")[4]

    def test_claude_error_kinds_are_all_reported(self):
        self.assertEqual(self.err(side_effect=subprocess.TimeoutExpired("claude", 1)), "TimeoutExpired")
        self.assertEqual(self.err(side_effect=FileNotFoundError()), "FileNotFoundError")
        self.assertIn("unparsable", self.err(return_value=proc("not json", 1)))
        self.assertTrue(self.err(return_value=proc({**OK, "is_error": True})))
        self.assertEqual(self.err(return_value=proc({**OK, "result": "  "})), "empty output")
        self.assertTrue(self.err(return_value=proc(OK, 1)))
        self.assertEqual(self.err(return_value=proc(OK)), "")

    def test_failed_review_is_an_error_not_a_miss(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); c = corpus_with(d / "c"); out = d / "o"
            for res in [("", 0, 1, 0, "TimeoutExpired"), ("prose, no array", 0.1, 1, 1, "")]:
                with mock.patch.object(bc, "claude", return_value=res):
                    cid, msg, _ = bc.run_case(c, "c1", "plain", out, None)
                rec = json.loads((out / "plain/c1.json").read_text())
                self.assertTrue(rec["error"] and rec["findings"] == [] and str(msg).startswith("ERROR"))
            (c / "manifest.json").write_text("[]")
            r = bc.metrics(c, ["c1"], "plain", out)
            self.assertEqual((r["cases"], r["errors"], r["recall_strict"], r["bugs"]), (0, 1, None, 0))

    def test_valid_empty_review_counts_as_zero_findings(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); c = corpus_with(d / "c")
            with mock.patch.object(bc, "claude", return_value=("[]", 0.1, 1, 1, "")):
                bc.run_case(c, "c1", "plain", d / "o", None)
            r = bc.metrics(c, ["c1"], "plain", d / "o")
            self.assertEqual((r["cases"], r["errors"], r["recall_strict"]), (1, 0, 0.0))

    def test_gap_without_perun_output_is_a_clear_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); c = corpus_with(d / "c")
            cid, msg, _ = bc.run_case(c, "c1", "perun-gap", d / "o", None)
            self.assertIn("missing perun output", msg)
            self.assertIn("missing perun output", json.loads((d / "o/perun-gap/c1.json").read_text())["error"])

    def test_gap_after_errored_perun_and_verifier_failure(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); c = corpus_with(d / "c"); out = d / "o"
            (out / "perun").mkdir(parents=True)
            (out / "perun/c1.json").write_text(json.dumps({"error": "boom", "findings": []}))
            self.assertIn("perun pass errored", bc.run_case(c, "c1", "perun-gap", out, None)[1])
            (out / "plain").mkdir()
            (out / "plain/c1.json").write_text(json.dumps({"error": "", "findings": [{"file": "a.py", "text": "other"}], "cost": 0, "seconds": 0}))
            with mock.patch.object(bc, "claude", return_value=("", 0, 1, 0, "TimeoutExpired")):
                self.assertIn("ERROR", str(bc.verify_case(c, "c1", "plain", out)[1]))
            (c / "manifest.json").write_text("[]")
            self.assertEqual(bc.metrics(c, ["c1"], "plain", out)["errors"], 1)
            self.assertIn("ERROR", str(bc.verify_case(c, "c1", "tools", out)[1]))


class Metrics(unittest.TestCase):
    def test_strict_adjudicated_and_verified(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for cid, find, ver in [("c1", [{"file": "a.py", "text": "wrong mechanism entirely"}, {"file": "a.py", "text": "junk"}], {"0": {"verdict": "gt_same"}, "1": {"verdict": "not_a_bug"}}),
                                   ("c2", [{"file": "b.py", "text": "uses bad regex"}, {"file": "b.py", "text": "other real"}], {"0": {"verdict": "gt_same"}, "1": {"verdict": "real"}})]:
                (d / cid).mkdir()
                f, m = {"c1": ("a.py", "alpha"), "c2": ("b.py", "regex")}[cid]
                (d / cid / "ground-truth.json").write_text(json.dumps({"bugs": [{"id": "B1", "file": f, "match": m, "example": m}]}))
                (d / "o/perun").mkdir(parents=True, exist_ok=True)
                (d / "o/perun" / f"{cid}.json").write_text(json.dumps({"findings": find, "verdicts": ver, "cost": 0.5, "seconds": 10}))
            r = bc.metrics(d, ["c1", "c2"], "perun", d / "o")
            self.assertEqual((r["recall_strict"], r["recall_adjudicated"]), (0.5, 1.0))
            self.assertEqual((r["precision_strict"], r["precision_verified"]), (0.25, 0.75))
            self.assertEqual((r["cost_usd"], r["errors"]), (1.0, 0))


class Committed(unittest.TestCase):
    def test_train_fixtures_selftest_reject_generic_text_and_test_truth_absent(self):
        generic = "unrelated issue: missing error handling, comments and a null check on the target"
        for m in MAN:
            d = BENCH / "train" / m["id"]
            if m["split"] == "test":
                self.assertFalse(d.exists(), "TEST ground truth must not be committed: " + m["id"])
            elif not m["id"].startswith("heldout-"):
                truth = json.loads((d / "ground-truth.json").read_text(encoding="utf-8"))
                self.assertTrue(sr.selftest(truth), m["id"])
                self.assertEqual(sr.score(truth, [{"file": truth["bugs"][0]["file"], "text": generic}])["recall"], 0.0, m["id"])
                self.assertTrue((d / "change.patch").stat().st_size > 0)
            self.assertIn(m["licence"], ("MIT", "BSD-3-Clause", "Apache-2.0"))

    def test_notice_covers_every_committed_upstream(self):
        notice = (BENCH / "NOTICE").read_text(encoding="utf-8")
        for m in MAN:
            if m["split"] == "train" and not m["id"].startswith("heldout-"):
                self.assertIn(m["repo_url"], notice, m["id"])


if __name__ == "__main__":
    unittest.main()
