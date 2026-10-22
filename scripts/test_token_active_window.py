#!/usr/bin/env python3
"""Tests for token_report.py `burn_blocks().active`: the live 5-hour window view (time left, burn so far, projection, optional limit, lever).

Synthetic, fictional turns only; every figure is hand-computed from the documented formula (weighted = input + 0.1 x cache_read + output).
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402


def T(day, hh, mm, inp=0, cr=0):
    return {"timestamp": datetime(2026, 10, day, hh, mm, tzinfo=timezone.utc), "model": "m", "input_tokens": inp,
            "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": cr, "output_tokens": 0}


def at(hh, mm=0, day=2):
    return datetime(2026, 10, day, hh, mm, tzinfo=timezone.utc)


def prior(w):  # two earlier windows of weight w each: median w
    return [T(1, 10, 0, w), T(1, 16, 0, w)]


# window 09:00-13:59 on day 2; at 10:00 it holds 6000 weighted: 60 min elapsed -> 100/min, 240 min left -> projected 6000 + 24000 = 30000
LIVE = [T(2, 9, 0, 3000), T(2, 10, 0, 3000)]


class ActiveWindow(unittest.TestCase):
    def test_hand_computed_projection_and_pace_lever(self):
        a = tr.burn_blocks(prior(10_000) + LIVE, [], now=at(10))["active"]
        self.assertEqual((a["start"], a["remaining_min"], a["weighted"], a["burn_per_min"], a["projected"], a["vs_median_x"]),
                         ("2026-10-02T09:00:00+00:00", 240.0, 6000.0, 100.0, 30000.0, 3.0))
        self.assertIn("on pace for 30000.0 weighted by the reset in 240.0 min, 3.0x the median of earlier windows; pause new lanes", a["advice"])
        self.assertEqual((a["limit"], a["pct_limit"], a["eta_min"]), (None, None, None))

    def test_limit_gives_percent_eta_and_overrides_the_median_rule(self):
        a = tr.burn_blocks(prior(10_000) + LIVE, [], now=at(10), limit=20_000)["active"]
        self.assertEqual((a["pct_limit"], a["eta_min"]), (30.0, 140.0))  # (20000 - 6000) / 100
        self.assertIn("over your 20000 limit (reached in ~140.0 min)", a["advice"])
        ok = tr.burn_blocks(prior(10_000) + LIVE, [], now=at(10), limit=40_000)["active"]  # 3x the median, but under the user's own limit
        self.assertEqual((ok["pct_limit"], ok["eta_min"], ok["advice"]), (15.0, 340.0, None))
        over = tr.burn_blocks(prior(10_000) + LIVE, [], now=at(10), limit=5_000)["active"]
        self.assertEqual((over["pct_limit"], over["eta_min"]), (120.0, 0.0))
        self.assertIn("reached in ~0.0 min", over["advice"])

    def test_median_threshold_is_two_times_inclusive(self):
        self.assertIsNotNone(tr.burn_blocks(prior(15_000) + LIVE, [], now=at(10))["active"]["advice"])  # 30000 = 2 x 15000
        below = tr.burn_blocks(prior(15_100) + LIVE, [], now=at(10))["active"]
        self.assertEqual((below["vs_median_x"], below["advice"]), (1.99, None))

    def test_fewer_than_two_earlier_windows_has_no_baseline(self):
        a = tr.burn_blocks([T(1, 10, 0, 100)] + LIVE, [], now=at(10))["active"]
        self.assertEqual((a["vs_median_x"], a["advice"]), (None, None))
        self.assertEqual(tr.burn_blocks(LIVE, [], now=at(10))["active"]["projected"], 30000.0)

    def test_idle_time_lowers_the_burn_rate(self):
        a = tr.burn_blocks(prior(10_000) + LIVE, [], now=at(13))["active"]  # 240 min since 09:00 -> 25/min, 60 min left
        self.assertEqual((a["burn_per_min"], a["projected"], a["advice"]), (25.0, 7500.0, None))

    def test_window_bounds(self):
        for now in (at(14), at(8, 59), at(15)):  # the window ends at 14:00 exclusive; before the first turn nothing is live
            self.assertIsNone(tr.burn_blocks(prior(10_000) + LIVE, [], now=now)["active"])
        self.assertIsNotNone(tr.burn_blocks(prior(10_000) + LIVE, [], now=at(13, 59))["active"])
        self.assertIsNone(tr.burn_blocks(prior(10_000) + LIVE, [])["active"])  # the real clock is long past these 2026-10 windows

    def test_driver_picks_the_lever(self):
        big = tr.burn_blocks(prior(10_000) + [T(2, 9, 0, cr=250_000), T(2, 10, 0, cr=250_000)], [], now=at(10))["active"]
        self.assertIn("main context averages 250000 (over the 200000 window): /compact at a task boundary", big["advice"])
        lane = tr.burn_blocks(prior(10_000) + [T(2, 9, 0, 100)], [("Fictional lane", [T(2, 10, 0, 5900)])], now=at(10))["active"]
        self.assertIn("lane 'Fictional lane' drives 98%: trim or split it", lane["advice"])

    def test_end_to_end_json_and_text_with_limit(self):
        def line(ts, rid, n):
            return {"type": "assistant", "timestamp": ts, "requestId": rid, "message": {"model": "m", "usage": {"input_tokens": n}}}
        rows = [line("2026-10-01T10:00:00Z", "a", 10_000), line("2026-10-01T16:00:00Z", "b", 10_000),
                line("2026-10-02T09:00:00Z", "c", 3000), line("2026-10-02T10:00:00Z", "d", 3000)]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "s.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            rep = tr.build_report(str(Path(d) / "s.jsonl"), None, 5, tr.DEFAULT_RATES, now=at(10), limit=20_000)
        self.assertEqual(rep["burn_blocks"]["active"]["eta_min"], 140.0)
        json.dumps(rep)
        text = tr.render_text(rep)
        self.assertIn("Active window (opened 2026-10-02T09:00:00+00:00, 240.0 min left): 6000.0 weighted at 100.0/min, projected 30000.0 at reset; 30.0% of limit 20000", text)
        self.assertIn("Lever: active window on pace for 30000.0 weighted", text)

    def test_cli_limit_flag_reaches_the_report(self):
        self.assertEqual(tr.build_parser().parse_args(["--limit", "20000"]).limit, 20000.0)

    def test_first_minutes_give_no_projection_or_lever(self):
        one = [T(2, 9, 0, 20_000)]
        a = tr.burn_blocks(prior(10_000) + one, [], now=at(9, 0) + timedelta(seconds=10), limit=1000)["active"]  # 20000 in 10 s would project 6M
        self.assertEqual((a["early"], a["burn_per_min"], a["projected"], a["vs_median_x"], a["eta_min"], a["advice"]), (True, None, None, None, None, None))
        self.assertEqual(a["pct_limit"], 2000.0)  # what is already spent is a fact, so it still shows
        text = tr.render_text({**tr.build_report(self._empty(), None), "burn_blocks": {"blocks": [{"start": "s", "weighted": 1, "burn_per_min": 1, "lane_share": 0,
                               "peak_lanes": 0}], "peak": {"start": "s", "weighted": 1, "burn_per_min": 1, "lane_share": 0, "peak_lanes": 0}, "spike_x": None,
                               "advice": None, "active": a}})
        self.assertIn("20000.0 weighted too early to project (under 15 min of data); 2000.0% of limit 1000", text)
        self.assertNotIn("Lever: active window", text)

    def test_projection_starts_at_fifteen_minutes_inclusive(self):
        base = prior(10_000) + [T(2, 9, 0, 3000)]
        self.assertTrue(tr.burn_blocks(base, [], now=at(9, 14, 2) + timedelta(seconds=59))["active"]["early"])
        a = tr.burn_blocks(base, [], now=at(9, 15))["active"]
        self.assertEqual((a["early"], a["burn_per_min"], a["projected"]), (False, 200.0, 3000 + 200 * 285.0))

    def _empty(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "s.jsonl"
        p.write_text("")
        return str(p)

    def test_limit_must_be_finite_and_positive(self):
        for bad in ("inf", "nan", "0", "-5", "1e400"):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(tr.main(["--limit", bad, "--session", "x.jsonl"]), tr.ERROR, bad)
            self.assertIn("--limit must be a finite number above 0", err.getvalue())

    def test_limit_with_no_live_window_prints_a_note(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tr.main(["--limit", "100", "--session", self._empty()]), tr.OK)
        self.assertIn("--limit ignored: no live 5-hour window now", err.getvalue())


if __name__ == "__main__":
    unittest.main()
