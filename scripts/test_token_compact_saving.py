#!/usr/bin/env python3
"""Tests for token_report.py `compact_saving` (auto-compact counterfactual, `auto_compact` in --json, ranked as a lever).

Synthetic context sizes only; the saving is hand-computed from the documented formula.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import token_report as tr  # noqa: E402
from test_token_lever_rank import rep  # noqa: E402


def turns(ctxs):
    """Main-turn dicts whose context (input + cache_read) equals each size."""
    return [{"timestamp": 1, "model": "m", "input_tokens": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": c} for c in ctxs]


class CompactSaving(unittest.TestCase):
    def test_no_compaction_needed(self):
        r = tr.compact_saving(turns([50_000, 90_000, 150_000, 200_000]), 1000.0)
        self.assertEqual((r["skipped"], r["compactions"], r["saving_ie_upper"]), ("never passes window", 0, 0.0))

    def test_already_compacting_session_is_skipped(self):
        r = tr.compact_saving(turns([100_000, 300_000, 500_000, 120_000, 200_000]), 1000.0)
        self.assertEqual((r["skipped"], r["compactions"], r["saving_ie_upper"]), ("already compacts", 0, 0.0))

    def test_growth_case_hand_computed(self):
        # ctx 100k..550k step 50k, window 200k, restart 30k: simulated 100,150,200,30,80,130,180,30,80,130 (k).
        # sum(observed - simulated) = 2140k -> 0.1x = 214000; minus 2 compactions x 1.25 x 30000 = 75000.
        r = tr.compact_saving(turns(range(100_000, 600_000, 50_000)), 1_000_000.0, window=200_000, restart=30_000)
        self.assertEqual((r["compactions"], r["saving_ie_upper"], r["skipped"]), (2, 139_000.0, None))
        self.assertEqual(r["saving_share_of_main_ie"], 0.139)

    def test_partial_drop_cannot_push_simulated_context_negative(self):
        # 500k -> 260k is a 48% drop (not "already compacts"); simulated 100,30,80,30,30(clamped, not -210),40 (k) -> 137000 - 75000.
        r = tr.compact_saving(turns([100_000, 250_000, 300_000, 500_000, 260_000, 270_000]), 1_000_000.0, window=200_000, restart=30_000)
        self.assertEqual((r["compactions"], r["saving_ie_upper"], r["skipped"]), (2, 62_000.0, None))

    def test_empty_and_synthetic_and_iter_turns_ignored(self):
        self.assertEqual(tr.compact_saving([], 0)["skipped"], "never passes window")
        junk = [{**t, "iter": True} for t in turns([900_000])] + [{**t, "model": "<synthetic>"} for t in turns([900_000])]
        self.assertEqual(tr.compact_saving(junk, 1.0)["compactions"], 0)

    def test_feeds_ranking_and_lever_line(self):
        ac = tr.compact_saving(turns(range(100_000, 600_000, 50_000)), 400_000.0)
        r = {**rep(pin=30_000, main_ie=400_000), "auto_compact": ac}
        r["lever_ranking"] = tr.lever_ranking(r)
        self.assertEqual([x["lever"] for x in r["lever_ranking"]], ["auto-compact at 200000", "pin main cache to 1h"])
        text = "\n".join(tr._gap_tier_lines(r))
        self.assertIn("Lever: auto-compact the main thread at 200000 tokens", text)
        self.assertIn("`/autocompact 200k`", text)
        self.assertNotIn("skip if", text)
        self.assertIn("quality lost to compaction is not modelled", text)

    def test_below_threshold_does_not_fire(self):
        ac = tr.compact_saving(turns(range(100_000, 600_000, 50_000)), 1e9)
        self.assertEqual(tr.lever_ranking({**rep(), "auto_compact": ac}), [])


class RankingEndToEnd(unittest.TestCase):
    def test_build_report_orders_levers_by_saving(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "s.jsonl")
            with open(path, "w", encoding="utf-8") as fh:
                for i in range(10):  # 10-minute gaps, 5000 fresh 5m-write tokens per turn, context growing 50k per turn
                    usage = {"input_tokens": 0, "cache_creation_input_tokens": 5000, "cache_read_input_tokens": 95_000 + 50_000 * i, "output_tokens": 1}
                    fh.write(json.dumps({"type": "assistant", "timestamp": f"2026-01-01T{i // 6:02d}:{i % 6 * 10:02d}:00Z", "requestId": f"r{i}",
                                         "apiBlockIndex": 0, "message": {"usage": usage, "content": []}}) + "\n")
            rep_ = tr.build_report(path, None)
        rank = rep_["lever_ranking"]
        self.assertEqual([x["lever"] for x in rank], ["auto-compact at 200000", "pin main cache to 1h"])
        self.assertGreater(rank[0]["saving_ie"], rank[1]["saving_ie"])
        self.assertEqual(rep_["auto_compact"]["compactions"], 2)
        self.assertIn("Top levers", tr.render_text(rep_))


def write_session(path, ctxs, field, extra=()):
    """Main-transcript fixture carrying each context in `field` (cache_read or cache_creation_input_tokens), plus raw `extra` lines."""
    with open(path, "w", encoding="utf-8") as fh:
        for i, c in enumerate(ctxs):
            usage = {"input_tokens": 0, field: c, "output_tokens": 1}
            fh.write(json.dumps({"type": "assistant", "timestamp": f"2026-01-01T00:{i:02d}:00Z", "requestId": f"r{i}",
                                 "apiBlockIndex": 1, "message": {"usage": usage, "content": []}}) + "\n")
        for line in extra:
            fh.write(json.dumps(line) + "\n")


class ContextSources(unittest.TestCase):
    CTX = list(range(100_000, 600_000, 50_000))

    def auto(self, field, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "s.jsonl")
            write_session(path, self.CTX, field, extra)
            return tr.build_report(path, None)["auto_compact"]

    def test_context_in_cache_writes_equals_context_in_reads(self):
        w, r = self.auto("cache_creation_input_tokens"), self.auto("cache_read_input_tokens")
        self.assertIsNone(w["skipped"])
        self.assertEqual((w["compactions"], w["saving_ie_upper"]), (r["compactions"], r["saving_ie_upper"]))
        self.assertEqual(w["compactions"], 2)

    def test_duplicate_request_and_sidechain_lines_do_not_change_result(self):
        base = self.auto("cache_read_input_tokens")
        dupe = {"type": "assistant", "timestamp": "2026-01-01T00:01:00Z", "requestId": "r1", "apiBlockIndex": 0,
                "message": {"usage": {"input_tokens": 0, "cache_read_input_tokens": 900_000, "output_tokens": 1}, "content": []}}
        side = {**dupe, "requestId": "side", "apiBlockIndex": 1, "isSidechain": True}
        self.assertEqual(self.auto("cache_read_input_tokens", [dupe, side]), base)


class TieOrder(unittest.TestCase):
    def test_equal_savings_keep_declared_order(self):
        # pin, compact and tail all save 100 input-eq: sorted() is stable, so the order is pin, compact, tail.
        ac = {"window": 200_000, "saving_ie_upper": 100.0, "saving_share_of_main_ie": 0.1}
        r = tr.lever_ranking({**rep(pin=100, tail=100), "auto_compact": ac})
        self.assertEqual([x["lever"] for x in r], ["pin main cache to 1h", "auto-compact at 200000", "lower LANE_TOOL_CAP below 250"])


if __name__ == "__main__":
    unittest.main()
