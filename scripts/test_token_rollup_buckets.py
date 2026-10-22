#!/usr/bin/env python3
"""Tests for `token_report.py --rollup DIR --by day|week`: UTC buckets that partition the rollup total.

Synthetic fixture (fictional models, generated in a temp dir). Hand-computed with the default rates
(claude-opus-5 in 5 / out 25 USD per 1M; claude-sonnet-5 in 2 / out 10; `acme-x` has no rate):
  r1  03-01 23:59:59Z opus   1M in + 100k out = $5 + $2.5  = $7.50      (copied again into s2: counts once)
  r2  03-02 00:00:01Z sonnet 2M in            = $4.00      (two blocks, only the max-apiBlockIndex line counts)
  r3  03-02 12:00:00Z acme-x 500 in + 500 out = UNPRICED
  r5  03-02 08:00:00Z sonnet 1M out (a lane)  = $10.00
  r4  03-09 10:00:00Z opus   1M out           = $25.00
  r6  no timestamp   sonnet 1k in             = $0.002
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402

OPUS, SONNET, ACME = "claude-opus-5", "claude-sonnet-5", "acme-x"


def line(req, ts, model, inp=0, out=0, block=None):
    row = {"type": "assistant", "requestId": req,
           "message": {"model": model, "usage": {"input_tokens": inp, "output_tokens": out}, "content": []}}
    if ts:
        row["timestamp"] = ts
    if block is not None:
        row["apiBlockIndex"] = block
    return row


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def fixture(root):
    r1 = line("r1", "2026-03-01T23:59:59Z", OPUS, 1_000_000, 100_000)
    write(root / "s1.jsonl", [r1,
                              line("r2", "2026-03-02T00:00:01Z", SONNET, 999, 999, block=0),
                              line("r2", "2026-03-02T00:00:01Z", SONNET, 2_000_000, 0, block=1),
                              line("r3", "2026-03-02T12:00:00Z", ACME, 500, 500)])
    write(root / "s1" / "subagents" / "agent-a.jsonl", [line("r5", "2026-03-02T08:00:00Z", SONNET, 0, 1_000_000)])
    write(root / "s2.jsonl", [r1, line("r4", "2026-03-09T10:00:00Z", OPUS, 0, 1_000_000), line("r6", None, SONNET, 1000)])


def run(root, by, since=None):
    return tr.build_rollup(str(root), since, by=by)


def total_ok(test, roll):
    """Tokens sum exactly; unrounded bucket spend rounds (4 dp, as the total does) to exactly the total."""
    test.assertEqual(sum(b["raw_tokens"] for b in roll["buckets"]), sum(s["raw_tokens"] for s in roll["sessions"]))
    test.assertEqual(round(sum(b["usd"] or 0 for b in roll["buckets"]), 4), roll["total_usd"])


class RollupBuckets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        fixture(cls.root)
        cls.day, cls.week, cls.plain = run(cls.root, "day"), run(cls.root, "week"), run(cls.root, None)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_buckets_sum_to_rollup_total(self):
        for roll in (self.day, self.week):
            total_ok(self, roll)
            self.assertEqual(sorted({m for b in roll["buckets"] for m in b["unpriced_models"]}), roll["unpriced_models"])

    def test_hand_computed_day_buckets(self):
        got = [(b["bucket"], b["raw_tokens"], b["usd"], b["unpriced_models"]) for b in self.day["buckets"]]
        self.assertEqual(got, [("2026-03-01", 1_100_000, 7.5, []), ("2026-03-02", 3_001_000, 14.0, [ACME]),
                               ("2026-03-09", 1_000_000, 25.0, []), ("undated", 1000, 0.002, [])])
        self.assertEqual(self.plain["total_usd"], 46.502)
        self.assertEqual(sum(s["raw_tokens"] for s in self.plain["sessions"]), 5_102_000)

    def test_hand_computed_week_buckets_and_delta(self):
        got = [(b["bucket"], b["raw_tokens"], b["usd"], b["delta"]) for b in self.week["buckets"]]
        self.assertEqual(got, [("2026-02-23", 1_100_000, 7.5, None),
                               ("2026-03-02", 3_001_000, 14.0, {"raw_tokens": 1_901_000, "usd": None}),
                               ("2026-03-09", 1_000_000, 25.0, {"raw_tokens": -2_001_000, "usd": None}),
                               ("undated", 1000, 0.002, None)])

    def test_delta_usd_needs_same_unpriced_models(self):
        # 03-01 names no unpriced model, 03-02 names acme-x: the priced subtotals are not comparable
        self.assertEqual(self.day["buckets"][1]["delta"], {"raw_tokens": 1_901_000, "usd": None})
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "s.jsonl", [line("a", "2026-03-01T10:00:00Z", ACME, 1), line("b", "2026-03-02T10:00:00Z", ACME, 3),
                                        line("c", "2026-03-01T11:00:00Z", SONNET, 1_000_000),
                                        line("d", "2026-03-02T11:00:00Z", SONNET, 3_000_000)])
            b = run(d, "day")["buckets"]
        self.assertEqual(b[1]["delta"], {"raw_tokens": 2_000_002, "usd": 4.0})  # same unpriced set: 6.0 - 2.0

    def test_many_buckets_sum_exactly(self):
        # 40 days x 7 sonnet input tokens = $0.000014 a day: rounding each bucket to 4 dp would sum to 0, not $0.00056
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "s.jsonl", [line(f"q{i}", f"2026-04-{i % 28 + 1:02d}T10:00:00Z" if i < 28 else f"2026-05-{i - 27:02d}T10:00:00Z",
                                             SONNET, 7) for i in range(40)])
            for by, n in (("day", 40), ("week", 7)):
                roll = run(d, by)
                self.assertEqual(len(roll["buckets"]), n)
                total_ok(self, roll)
                self.assertEqual(roll["total_usd"], 0.0006)

    def test_year_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "s.jsonl", [line("a", "2026-12-31T10:00:00Z", SONNET, 1_000_000),
                                        line("b", "2027-01-01T10:00:00Z", SONNET, 2_000_000),
                                        line("c", "2027-01-04T10:00:00Z", SONNET, 4_000_000)])
            day, week = run(d, "day")["buckets"], run(d, "week")["buckets"]
        self.assertEqual([b["bucket"] for b in day], ["2026-12-31", "2027-01-01", "2027-01-04"])
        self.assertEqual(day[1]["delta"], {"raw_tokens": 1_000_000, "usd": 2.0})  # across New Year
        self.assertIsNone(day[2]["delta"])
        self.assertEqual([(b["bucket"], b["raw_tokens"]) for b in week], [("2026-12-28", 3_000_000), ("2027-01-04", 4_000_000)])
        self.assertEqual(week[1]["delta"], {"raw_tokens": 1_000_000, "usd": 2.0})

    def test_non_utc_offset_is_bucketed_in_utc(self):
        with tempfile.TemporaryDirectory() as d:  # 23:30 at -05:00 is 04:30 UTC the next day
            write(Path(d) / "s.jsonl", [line("a", "2026-03-01T23:30:00-05:00", SONNET, 10), line("b", "2026-03-02T01:00:00+02:00", SONNET, 20)])
            b = run(d, "day")["buckets"]
        self.assertEqual([(x["bucket"], x["raw_tokens"]) for x in b], [("2026-03-01", 20), ("2026-03-02", 10)])

    def test_turn_across_midnight_lands_in_its_last_block_day(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "s.jsonl", [line("a", "2026-03-01T23:59:59Z", SONNET, 1, block=0), line("a", "2026-03-02T00:00:01Z", SONNET, 5, block=1)])
            b = run(d, "day")["buckets"]
        self.assertEqual([(x["bucket"], x["raw_tokens"]) for x in b], [("2026-03-02", 5)])

    def test_lane_requestid_dup_counts_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane = line("l1", "2026-03-02T08:00:00Z", SONNET, 0, 1_000_000)
            write(root / "s1.jsonl", [line("m1", "2026-03-02T07:00:00Z", SONNET, 1000)])
            write(root / "s1" / "subagents" / "a.jsonl", [lane])
            write(root / "s2.jsonl", [line("m1", "2026-03-02T07:00:00Z", SONNET, 1000), line("m2", "2026-03-03T07:00:00Z", SONNET, 2000)])
            write(root / "s2" / "subagents" / "a.jsonl", [lane, line("m1", "2026-03-02T07:00:00Z", SONNET, 1000)])  # lane copies of seen ids
            roll = run(root, "day")
        self.assertEqual([(b["bucket"], b["raw_tokens"]) for b in roll["buckets"]], [("2026-03-02", 1_001_000), ("2026-03-03", 2000)])
        total_ok(self, roll)

    def test_since_drops_undated_turns_like_the_totals(self):
        roll = run(self.root, "day", since=tr.parse_timestamp("2026-03-02T00:00:00Z"))
        self.assertEqual([b["bucket"] for b in roll["buckets"]], ["2026-03-02", "2026-03-09"])  # r1 and the undated turn are out
        total_ok(self, roll)
        self.assertEqual(roll["total_usd"], 39.0)

    def test_gap_has_no_delta(self):
        self.assertIsNone(self.day["buckets"][2]["delta"])  # 03-09 follows 03-02, not an adjacent day

    def test_model_share(self):
        shares = self.day["buckets"][1]["models"]
        self.assertEqual({m: v["share"] for m, v in shares.items()}, {SONNET: 0.9997, ACME: 0.0003})
        self.assertEqual(shares[SONNET]["usd"], 14.0)
        self.assertIsNone(shares[ACME]["usd"])  # unpriced model never reads as $0

    def test_all_unpriced_bucket_is_none_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "s.jsonl", [line("a", "2026-03-01T10:00:00Z", ACME, 10, 10)])
            b = run(d, "day")["buckets"][0]
        self.assertIsNone(b["usd"])
        self.assertEqual(b["unpriced_models"], [ACME])

    def test_default_has_no_buckets_and_cli(self):
        self.assertNotIn("buckets", self.plain)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(tr.main(["--rollup", str(self.root), "--by", "week", "--top", "0"]), tr.OK)
            self.assertEqual(tr.main(["--by", "day"]), tr.ERROR)
        text = out.getvalue()
        self.assertIn("2026-03-02 $14.00 + UNPRICED (acme-x) raw=3001000 (+1901000 tok)", text)
        self.assertIn("--by needs --rollup", err.getvalue())


if __name__ == "__main__":
    unittest.main()
