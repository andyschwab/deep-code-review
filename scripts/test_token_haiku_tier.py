#!/usr/bin/env python3
"""Tests for per-turn Haiku 5.5 tier pricing in `token_report.py` (session, rollup, buckets share `price`).

Synthetic fixture. Rates USD per 1M (input / 5m write / 1h write / read / output):
  claude-haiku-5-5 prompt <= 100,000: 0.10 / 0.125 / 0.20 / 0.01 / 0.50;  prompt > 100,000: 0.50 / 0.625 / 1 / 0.05 / 2.50
  claude-opus-5 stays flat 5 / 6.25 / 10 / 0.5 / 25 whatever the prompt size.
Prompt = input + cache write + cache read (output excluded). Hand-computed micro-dollars (usd * 1e6):
  at    prompt 100,000 = 20,000 in + 10,000 write + 70,000 read, 1,000 out: 2000 + 1250 + 700 + 500            = 4450
  over  prompt 100,001 = 20,001 in + 10,000 write + 70,000 read, 1,000 out: 10000.5 + 6250 + 3500 + 2500      = 22250.5
  small prompt   1,000 in, 100 out:                                          100 + 50                          = 150
  mixed session = at + over + small = 26850.5 ; opus 200,000 in (flat) = 1,000,000
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402

HAIKU, OPUS = "claude-haiku-5-5", "claude-opus-5"


def turn(req, ts, model, inp, write=0, read=0, out=0):
    usage = {"input_tokens": inp, "cache_creation_input_tokens": write, "cache_read_input_tokens": read, "output_tokens": out}
    return {"type": "assistant", "requestId": req, "timestamp": ts, "message": {"model": model, "usage": usage, "content": []}}


AT = turn("at", "2026-03-01T10:00:00Z", HAIKU, 20_000, 10_000, 70_000, 1_000)
OVER = turn("over", "2026-03-02T10:00:00Z", HAIKU, 20_001, 10_000, 70_000, 1_000)
SMALL = turn("small", "2026-03-02T11:00:00Z", HAIKU, 1_000, out=100)
BIG_OPUS = turn("opus", "2026-03-02T12:00:00Z", OPUS, 200_000)


def roll(rows, by=None):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "s.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        return tr.build_rollup(d, None, by=by)


def by_model(rows):
    return tr.model_stats(tr.extract_turns(rows, main=True))[2]


def haiku_usd(rows):
    """Exact (unrounded) price of the rows through the shared pricing path."""
    return tr.price(by_model(rows), tr.DEFAULT_RATES, None)[0]


class HaikuTier(unittest.TestCase):
    def test_threshold_is_inclusive_in_the_base_tier(self):
        self.assertAlmostEqual(haiku_usd([AT]), 0.00445, places=9)

    def test_one_token_over_pays_the_long_tier_for_every_token_class(self):
        self.assertAlmostEqual(haiku_usd([OVER]), 0.0222505, places=9)

    def test_mixed_session_prices_each_turn_in_its_own_tier(self):
        self.assertAlmostEqual(haiku_usd([AT, OVER, SMALL]), 0.0268505, places=9)
        # merged totals (rollup path) price identically to the per-session path
        r = roll([AT, OVER, SMALL])
        self.assertEqual(r["total_usd"], 0.0269)
        self.assertEqual(r["unpriced_models"], [])

    def test_buckets_split_tiers_by_day_and_sum_to_total(self):
        r = roll([AT, OVER, SMALL], by="day")
        self.assertAlmostEqual(r["buckets"][0]["usd"], 0.00445, places=9)
        self.assertAlmostEqual(r["buckets"][1]["usd"], 0.0224005, places=9)  # over + small

    def test_other_models_stay_flat_regardless_of_prompt_size(self):
        self.assertEqual(roll([BIG_OPUS])["total_usd"], 1.0)

    def test_long_key_only_for_tiered_models(self):
        self.assertNotIn("long", by_model([BIG_OPUS])[OPUS])
        self.assertNotIn("long", by_model([AT, SMALL])[HAIKU])
        self.assertEqual(by_model([OVER])[HAIKU]["long"]["input_tokens"], 20_001)

    def test_user_rates_file_stays_flat(self):
        flat = {HAIKU: dict(zip(tr.ZERO_USAGE, (0.1, 0.125, 0.2, 0.01, 0.5)))}
        want = (20_001 * 0.1 + 10_000 * 0.125 + 70_000 * 0.01 + 1_000 * 0.5) / 1e6
        self.assertAlmostEqual(tr.price(by_model([OVER]), flat, None)[0], want, places=9)


if __name__ == "__main__":
    unittest.main()
