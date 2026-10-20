#!/usr/bin/env python3
"""Tests for token_report.py idle-gap cache rewrites and the by-model input-equivalent split.

Fixtures are synthetic transcripts (fictional model ids) generated in a temp dir; no real session is read.
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402

T0 = datetime(2026, 10, 19, 10, 0, 0, tzinfo=timezone.utc)
OPUS, SONNET, MYSTERY = "claude-opus-5", "claude-sonnet-5", "acme-model-x"


def row(i, at_s, write=100, model=OPUS, read=0, w1h=0, side=False):
    usage = {"input_tokens": 0, "cache_read_input_tokens": read, "output_tokens": 1,
             "cache_creation": {"ephemeral_5m_input_tokens": write, "ephemeral_1h_input_tokens": w1h}}
    return {"type": "assistant", "isSidechain": side, "requestId": f"r{i}", "timestamp": (T0 + timedelta(seconds=at_s)).isoformat(),
            "message": {"model": model, "usage": usage}}


def report(tmp, main, lanes=()):
    d = Path(tmp)
    (d / "s.jsonl").write_text("".join(json.dumps(r) + "\n" for r in main))
    if lanes:
        (d / "s" / "subagents").mkdir(parents=True, exist_ok=True)
        (d / "s" / "subagents" / "agent-1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lanes))
    return tr.build_report(str(d / "s.jsonl"), None, 5, tr.DEFAULT_RATES)


class IdleGap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def idle(self, offsets, **kw):
        return report(self.tmp.name, [row(i, s, **kw) for i, s in enumerate(offsets)])["idle_rewrites"]

    def test_boundary_299_is_warm_301_is_idle(self):
        self.assertEqual(self.idle([0, 299])["idle_rewrite_tokens_5m"], 0)
        self.assertEqual(self.idle([0, 300])["idle_rewrite_tokens_5m"], 0)
        self.assertEqual(self.idle([0, 301])["idle_rewrite_tokens_5m"], 100)

    def test_split_5m_1h_vs_over_1h_and_saving(self):
        i = self.idle([0, 60, 60 + 301, 60 + 301 + 3600, 60 + 301 + 3600 + 3601])
        self.assertEqual((i["idle_rewrite_tokens_5m"], i["idle_rewrite_tokens_5m_to_1h"], i["idle_rewrite_tokens_over_1h"]),
                         (300, 200, 100))
        self.assertEqual(i["idle_rewrite_share"], 0.6)  # 300 of 500 5m writes
        self.assertEqual(i["idle_rewrite_saving_ie_upper"], round(200 * 1.15 - 0.75 * 300, 2))

    def test_no_gap_no_writes(self):
        i = self.idle([0, 10, 20])
        self.assertEqual((i["idle_rewrite_share"], i["idle_rewrite_tokens_5m_to_1h"]), (0.0, 0))
        self.assertEqual(self.idle([0, 1000], write=0)["idle_rewrite_share"], 0.0)  # no division by zero

    def test_text_lever_fires_only_when_material(self):
        text = tr.render_text(report(self.tmp.name, [row(i, i * 400, model=SONNET) for i in range(6)]))
        self.assertIn("Idle-gap cache rewrites", text)
        self.assertIn("Lever: pin the main conversation cache to 1h", text)
        self.assertIn("host-enforcement.md", text)
        text = tr.render_text(report(self.tmp.name, [row(i, i * 10, model=SONNET) for i in range(6)]))
        self.assertNotIn("Lever: pin", text)


class Levers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def text(self, rows):
        r = report(self.tmp.name, rows)
        return r["idle_rewrites"], tr.render_text(r)

    def test_lever_text_names_force_override_and_version(self):
        _, text = self.text([row(i, i * 400, model=SONNET) for i in range(6)])
        self.assertIn("Lever: pin the main conversation cache to 1h", text)
        self.assertIn("v2.1.242+", text)
        self.assertIn("FORCE_PROMPT_CACHING_5M=1", text)

    def test_negative_saving_is_signed_in_json_and_says_would_not_save(self):
        i, text = self.text([row(n, n * 4000, model=SONNET) for n in range(5)])  # every gap over 1h: nothing a 1h pin would keep
        self.assertGreater(i["idle_rewrite_share"], 0.5)
        self.assertLess(i["idle_rewrite_saving_ie_upper"], 0)
        self.assertIn("a 1h pin would not save", text)
        self.assertNotIn("Lever: pin", text)

    def test_high_idle_share_but_tiny_saving_has_no_lever(self):
        # gap writes dominate, saving is positive but far below 5% of main input-eq (huge cache reads)
        i, text = self.text([row(n, n * 400, model=SONNET, read=100_000) for n in range(4)])
        self.assertGreaterEqual(i["idle_rewrite_share"], tr.IDLE_LEVER_SHARE)
        self.assertGreater(i["idle_rewrite_saving_ie_upper"], 0)
        self.assertLess(i["idle_rewrite_saving_share_of_main_ie"], tr.IDLE_LEVER_SAVING)
        self.assertNotIn("Lever: pin", text)

    def test_mostly_1h_writes_skip_lever_and_partly_1h_is_noted(self):
        i, text = self.text([row(n, n * 400, model=SONNET, w1h=1000) for n in range(6)])
        self.assertGreaterEqual(i["cache_write_1h_share"], 0.5)
        self.assertNotIn("Lever: pin", text)
        i, text = self.text([row(n, n * 400, model=SONNET, write=1000, w1h=100) for n in range(6)])
        self.assertLess(i["cache_write_1h_share"], 0.5)
        self.assertIn("Lever: pin", text)
        self.assertIn("already 1h", text)

    def test_sidechain_turns_are_not_main_turns(self):
        i, _ = self.text([row(0, 0), row(1, 10, side=True, write=999), row(2, 400)])
        self.assertEqual((i["idle_rewrite_tokens_5m"], i["idle_rewrite_share"]), (100, 0.5))


class TierSplit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_shares_unpriced_and_orchestrator_lever(self):
        main = [row(0, 0, model=OPUS, write=1000), row(1, 10, model=MYSTERY, write=1000)]
        lanes = [row(2, 20, model=SONNET, write=1000)]
        r = report(self.tmp.name, main, lanes)
        ts = r["tier_split"]
        self.assertAlmostEqual(sum(v["share"] for v in ts["main"].values()), 1.0, places=3)
        self.assertAlmostEqual(sum(v["share"] for v in ts["subagents"].values()), 1.0, places=3)
        self.assertTrue(ts["main"][OPUS]["priced"])
        self.assertFalse(ts["main"][MYSTERY]["priced"])
        self.assertAlmostEqual(ts["main_share_of_total_ie"], 2 / 3, places=3)
        self.assertAlmostEqual(ts["main_top_tier_share_of_total_ie"], 1 / 3, places=3)
        text = tr.render_text(r)
        self.assertIn(f"{MYSTERY} 50.0% UNPRICED", text)
        self.assertNotIn("Lever: orchestrator tier", text)  # top-tier main is 33% of all ie, under 40%

    def test_orchestrator_lever_when_top_tier_main_over_40pct(self):
        r = report(self.tmp.name, [row(0, 0, model=OPUS, write=3000)], [row(1, 5, model=SONNET, write=1000)])
        self.assertIn("Lever: orchestrator tier", tr.render_text(r))
        r = report(self.tmp.name, [row(0, 0, model=SONNET, write=3000)], [row(1, 5, model=SONNET, write=1000)])
        self.assertNotIn("Lever: orchestrator tier", tr.render_text(r))


if __name__ == "__main__":
    unittest.main()
