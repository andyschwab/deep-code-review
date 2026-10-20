#!/usr/bin/env python3
"""Tests for token_report.py `lever_ranking` (Top levers block, `lever_ranking` in --json).

Pure-dict fixtures: the ranking only reads figures the report already computes, so the order must flip when those inputs flip.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402


def rep(pin=0.0, tail=0.0, top_tier=0.0, main_ie=1000.0, lane_ie=1000.0, shipped=250):
    """Report dict with only the fields lever_ranking/_gap_tier_lines read. pin/tail are saving input-eq (0 = lever off)."""
    return {
        "main": {"input_equivalent": main_ie}, "subagents_totals": {"input_equivalent": lane_ie},
        "main_turns": 0, "subagents_count": 0,
        "idle_rewrites": {"idle_rewrite_share": 0.9 if pin else 0.0, "idle_rewrite_saving_ie_upper": pin,
                          "idle_rewrite_saving_share_of_main_ie": pin / main_ie, "cache_write_1h_share": 0.0},
        "lane_tail": {"cap": 150, "shipped_cap": shipped, "tail_ie_over_cap": tail, "tail_ie_over_shipped_cap": tail,
                      "tail_share_over_cap": tail / lane_ie, "tail_share_over_shipped_cap": tail / lane_ie,
                      "lanes_over_cap": 1, "lanes_over_shipped_cap": 1, "p90_tool_calls": 300},
        "tier_split": {"main": {}, "subagents": {}, "main_share_of_total_ie": 0.5, "main_top_tier_share_of_total_ie": top_tier},
    }


class LeverRank(unittest.TestCase):
    def test_order_flips_with_inputs(self):
        a = tr.lever_ranking(rep(pin=400, tail=200))
        self.assertEqual([r["lever"] for r in a], ["pin main cache to 1h", "lower LANE_TOOL_CAP below 250"])
        b = tr.lever_ranking(rep(pin=200, tail=400))
        self.assertEqual([r["lever"] for r in b], ["lower LANE_TOOL_CAP below 250", "pin main cache to 1h"])

    def test_share_is_of_main_plus_lane_ie(self):
        r = tr.lever_ranking(rep(pin=400, main_ie=1000, lane_ie=3000))[0]
        self.assertEqual((r["saving_ie"], r["share_of_session_ie"]), (400, 0.1))

    def test_dollar_only_lists_after_ranked_and_is_unpriced_not_zero(self):
        r = tr.lever_ranking(rep(pin=50, tail=0, top_tier=0.9))
        self.assertEqual([x["lever"] for x in r], ["pin main cache to 1h", "orchestrator tier"])
        self.assertIsNone(r[1]["saving_ie"])
        self.assertIsNone(r[1]["saving_usd"])
        text = "\n".join(tr._gap_tier_lines({**rep(pin=50, top_tier=0.9), "lever_ranking": r}))
        self.assertIn("2. orchestrator tier: saving UNPRICED", text)
        self.assertIn("1. pin main cache to 1h: at most 50 input-eq = 2.5%", text)

    def test_nothing_firing_gives_empty_and_no_block(self):
        r = tr.lever_ranking(rep())
        self.assertEqual(r, [])
        self.assertNotIn("Top levers", "\n".join(tr._gap_tier_lines({**rep(), "lever_ranking": r})))

    def test_no_shipped_cap_uses_reference_tail(self):
        r = tr.lever_ranking(rep(tail=300, shipped=None))
        self.assertEqual(r[0]["lever"], "lower LANE_TOOL_CAP below 150")
        self.assertEqual(r[0]["saving_ie"], 300)

    def test_zero_session_ie_no_crash(self):
        r = tr.lever_ranking({**rep(tail=300, main_ie=1, lane_ie=300), "main": {"input_equivalent": 0}, "subagents_totals": {"input_equivalent": 0}})
        self.assertEqual(r[0]["share_of_session_ie"], 0.0)

    def test_lane_tail_reports_shipped_tail_ie(self):
        lt = tr.lane_tail([{"input_equivalent": 1000, "tool_calls": 300}, {"input_equivalent": 500, "tool_calls": 20}], shipped=250)
        self.assertEqual(lt["tail_ie_over_shipped_cap"], round(1000 * 50 / 300, 2))
        self.assertIsNone(tr.lane_tail([])["tail_ie_over_shipped_cap"])


if __name__ == "__main__":
    unittest.main()
