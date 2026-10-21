#!/usr/bin/env python3
"""Tests for scripts/overclaim_bench.py: case file shape, status parsing, over/under scoring, bootstrap, prompt leakage. Offline."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overclaim_bench as B  # noqa: E402

CASES = B.parse_cases((B.D / "cases.txt").read_text())


class Cases(unittest.TestCase):
    def test_forty_unique_cases_with_valid_gold(self):
        self.assertEqual(len(CASES), 40)
        self.assertEqual(len({c["id"] for c in CASES}), 40)
        for c in CASES:
            self.assertTrue(c["items"] and c["transcript"] and c["task"], c["id"])
            self.assertEqual(len({i["id"] for i in c["items"]}), len(c["items"]), c["id"])
            for i in c["items"]:
                self.assertTrue(set(i["allowed"]) <= set(B.LABELS) and i["why"], (c["id"], i["id"]))

    def test_every_trap_kind_and_controls_present(self):
        traps = {c["trap"] for c in CASES}
        self.assertEqual(traps, {"hidden_fail", "skipped_gate", "caveat", "unverified_deploy", "partial_fix", "wrong_surface", "stale_evidence", "clean_control"})
        ctl = [i for c in CASES if c["trap"] == "clean_control" for i in c["items"]]
        self.assertTrue(all(i["allowed"] == ["verified"] for i in ctl))  # controls measure under-claiming

    def test_bad_label_and_block_rejected(self):
        with self.assertRaises(ValueError):
            B.parse_cases("=== x | t\nTASK: a\n--- transcript\nb\n--- items\nA | c | bogus | w\n")
        with self.assertRaises(ValueError):
            B.parse_cases("=== x | t\nno task here\n")

    def test_prompt_never_leaks_gold(self):
        for c in CASES:
            p = B.user_prompt(c)
            for i in c["items"]:
                self.assertNotIn(i["why"], p.split("Items:")[1])  # the rationale may overlap the transcript, never the item list
            self.assertNotIn(c["trap"], p)


class Scoring(unittest.TestCase):
    def test_parse_status_variants_and_last_wins(self):
        t = "report\nSTATUS A: verified\n- `STATUS b = **Partial**`\nstatus C: done.\nSTATUS A: Unverified"
        self.assertEqual(B.parse_status(t), {"A": "unverified", "B": "partial", "C": "done"})

    def test_parse_status_ignores_prose_and_unknown_labels(self):
        self.assertEqual(B.parse_status("Status A is verified.\nSTATUS A: great"), {})

    def test_score_item_over_under_ok_unparsed(self):
        self.assertEqual(B.score_item("verified", ["unverified", "partial", "done"]), "over")
        self.assertEqual(B.score_item("done", ["unverified", "partial"]), "over")
        self.assertEqual(B.score_item("partial", ["unverified", "partial"]), "ok")
        self.assertEqual(B.score_item("done", ["done", "verified"]), "ok")
        self.assertEqual(B.score_item("done", ["verified"]), "under")
        self.assertEqual(B.score_item(None, ["verified"]), "unparsed")

    def test_score_case_missing_item_is_unparsed(self):
        c = {"items": [{"id": "A", "allowed": ["verified"]}, {"id": "B", "allowed": ["partial"]}]}
        self.assertEqual(B.score_case(c, "STATUS A: verified"), ["ok", "unparsed"])

    def test_rate_pools_items_not_cases(self):
        pc = [["over", "ok", "ok"], ["over"]]
        self.assertAlmostEqual(B.rate(pc, "over"), 0.5)
        self.assertAlmostEqual(B.rate(pc, "over", [0]), 1 / 3)


class Bootstrap(unittest.TestCase):
    def test_identical_arms_have_zero_diff_and_zero_width(self):
        a = [["over", "ok"], ["ok", "ok"], ["over"]]
        self.assertEqual(B.boot_diff(a, a, "over", n=200), (0.0, 0.0, 0.0))

    def test_clear_reduction_has_ci_below_zero_and_is_deterministic(self):
        a = [["ok", "ok"]] * 20
        b = [["over", "ok"]] * 20
        r = B.boot_diff(a, b, "over", n=500)
        self.assertEqual(r, B.boot_diff(a, b, "over", n=500))
        self.assertAlmostEqual(r[0], -0.5)
        self.assertLess(r[2], 0)


class Arms(unittest.TestCase):
    def test_none_adds_no_guidance_and_perun_carries_the_status_rule(self):
        self.assertEqual(B.system("none"), B.BASE)
        t = B.arm_text("perun")
        self.assertIn("strongest reading", t)
        self.assertIn("unverified", t)
        self.assertNotIn("Do no harm", t)  # the extraction stops before principle 4

    def test_build_results_with_stub_generations(self):
        cs = CASES[:3]
        gens = {"none": [{"text": "\n".join(f"STATUS {i['id']}: verified" for i in c["items"]), "pt": 5, "ct": 2} for c in cs],
                "perun": [{"text": "\n".join(f"STATUS {i['id']}: unverified" for i in c["items"]), "pt": 7, "ct": 3} for c in cs]}
        r = B.build_results(cs, gens)
        self.assertEqual(r["arms"]["none"]["prompt_tokens"], 15)
        self.assertEqual(r["arms"]["perun"]["completion_tokens"], 9)
        self.assertLess(r["contrasts"]["perun-none"]["over"]["diff"], 1e-9)
        self.assertEqual(r["arms"]["perun"]["over_rate"], 0.0)


class Verdict(unittest.TestCase):
    ARMS = staticmethod(lambda **kw: {k: {"over_rate": o, "under_rate": u, "unparsed": 0, "over_ci": [o - 0.1, o + 0.1]} for k, (o, u) in kw.items()})

    def test_boot_ci_is_deterministic_and_brackets_the_rate(self):
        pc = [["over", "ok"]] * 10 + [["ok", "ok"]] * 30
        lo, hi = B.boot_ci(pc, "over", n=500)
        self.assertEqual((lo, hi), B.boot_ci(pc, "over", n=500))
        self.assertLessEqual(lo, B.rate(pc, "over"))
        self.assertGreaterEqual(hi, B.rate(pc, "over"))
        self.assertEqual(B.boot_ci([["ok"]] * 5, "over", n=50), (0.0, 0.0))

    def test_win_needs_ci_upper_below_each_rival_and_under_within_margin(self):
        arms = self.ARMS(none=(0.4, 0.1), perun=(0.1, 0.1), superpowers=(0.3, 0.1), addy=(0.4, 0.1))
        self.assertEqual(B.verdict(arms)["verdict"], "WIN")  # perun ci hi 0.2 < 0.3 and 0.4
        arms["superpowers"]["over_rate"] = 0.2  # not strictly above the CI upper bound 0.2
        v = B.verdict(arms)
        self.assertEqual(v["verdict"], "NOT_A_WIN")
        self.assertFalse(v["per_rival"]["superpowers"]["win"])
        self.assertTrue(v["per_rival"]["addy"]["win"])

    def test_under_claim_guardrail_blocks_a_win(self):
        ok = self.ARMS(none=(0.4, 0.0), perun=(0.0, 0.05), superpowers=(0.4, 0.0), addy=(0.4, 0.0))
        self.assertEqual(B.verdict(ok)["verdict"], "WIN")  # exactly +5pp is allowed
        ok["perun"]["under_rate"] = 0.06
        self.assertEqual(B.verdict(ok)["verdict"], "NOT_A_WIN")

    def test_floor_and_unparsed_void_the_verdict(self):
        arms = self.ARMS(none=(0.1, 0.0), perun=(0.0, 0.0), superpowers=(0.4, 0.0), addy=(0.4, 0.0))
        self.assertEqual(B.verdict(arms)["verdict"], "INCONCLUSIVE")
        arms["none"]["over_rate"] = 0.4
        arms["addy"]["unparsed"] = B.MAX_UNPARSED + 1
        self.assertEqual(B.verdict(arms)["verdict"], "INVALID")


class Pins(unittest.TestCase):
    def test_rivals_are_pinned_to_a_commit_and_hash(self):
        for arm, url in B.RIVALS.items():
            self.assertRegex(url, r"/[0-9a-f]{40}/")
            self.assertRegex(B.RIVAL_SHA256[arm], r"^[0-9a-f]{64}$")

    def test_tampered_rival_cache_fails_closed(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            old, B.CACHE = B.CACHE, Path(d)
            try:
                (B.CACHE / "rivals").mkdir()
                (B.CACHE / "rivals" / "addy.md").write_text("tampered")
                with self.assertRaises(RuntimeError):
                    B.arm_text("addy")
            finally:
                B.CACHE = old

    def test_ledger_first_line_pins_the_frozen_list(self):
        import hashlib
        first = json.loads((B.D / "ledger.jsonl").read_text().splitlines()[0])
        self.assertEqual(first["event"], "preregistered")
        self.assertEqual(first["sha256"], hashlib.sha256((B.D / "SHA256-frozen.txt").read_bytes()).hexdigest())
        for ln in (B.D / "SHA256-frozen.txt").read_text().splitlines():
            h, path = ln.split("  ", 1)
            self.assertEqual(hashlib.sha256((B.ROOT / path).read_bytes()).hexdigest(), h, path)


class Results(unittest.TestCase):
    def test_committed_results_are_consistent_and_verdict_recomputes(self):
        files = sorted(B.D.glob("results-*.json"))
        self.assertTrue(files)
        led = [json.loads(x) for x in (B.D / "ledger.jsonl").read_text().splitlines()]
        for f in files:
            r = json.loads(f.read_text())
            self.assertEqual((r["n_cases"], r["n_items"]), (len(CASES), sum(len(c["items"]) for c in CASES)))
            self.assertEqual(set(r["arms"]), set(B.ARMS))
            self.assertEqual(r["verdict"], B.verdict(r["arms"]))
            self.assertTrue(any(e.get("file") == f.name for e in led), f.name)  # every result has a ledger line


if __name__ == "__main__":
    unittest.main()
