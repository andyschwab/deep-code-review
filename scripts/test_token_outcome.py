#!/usr/bin/env python3
"""Tests for `token_report.py --outcome` (weekly input-equivalent per turn, cache-hit %, lever-applied share, before/after split).

Synthetic transcripts, usage/timestamp/model only. ie = input + 0.1 * cache_read (no writes); prompt = input + read.
Week of Mon 2026-03-02 (session A, D):
  A (opus): ctx 100k, 250k, 40k -> passes the 200k window then drops over 50% = compact triggered + applied;
    input 1000 each, read 99k/249k/39k: ie 1000*3 + 0.1*387000 = 41700, prompt 390000.
  D (opus only, 1000 in + 1000 read): downshift triggered, never applied: ie 1100, prompt 2000.
  week: 4 turns, ie 42800 -> 10700.0/turn, cache-hit 388000/392000 = 0.9898, 2 lever sessions, 1 applied = 0.5.
Week of Mon 2026-03-09 (session B, C):
  B: opus (2000 in + 8000 read) then sonnet (2000 in + 18000 read) = downshift applied: ie 6600, prompt 30000.
  C (sonnet, 1000 in + 4000 read): no trigger: ie 1400, prompt 5000.
  week: 3 turns, ie 8000 -> 2666.7/turn, cache-hit 30000/35000 = 0.8571, 1 lever session, 1 applied = 1.0.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402

OPUS, SONNET = "claude-opus-5", "claude-sonnet-5-5"


def turn(req, ts, model, inp, read, **extra):
    usage = {"input_tokens": inp, "cache_read_input_tokens": read, "output_tokens": 5}
    return {"type": "assistant", "requestId": req, "timestamp": ts, "message": {"model": model, "usage": usage, "content": "SECRET"}, **extra}


SESSIONS = {
    "a": [turn("a1", "2026-03-02T10:00:00Z", OPUS, 1000, 99_000), turn("a2", "2026-03-02T10:05:00Z", OPUS, 1000, 249_000),
          turn("a3", "2026-03-02T10:10:00Z", OPUS, 1000, 39_000),
          turn("side", "2026-03-02T10:11:00Z", OPUS, 9_000_000, 0, isSidechain=True),  # lane line: not main
          turn("syn", "2026-03-02T10:12:00Z", "<synthetic>", 9_000_000, 0), {"type": "user", "message": {"content": "SECRET"}}],
    "d": [turn("d1", "2026-03-03T10:00:00Z", OPUS, 1000, 1000)],
    "b": [turn("b1", "2026-03-09T10:00:00Z", OPUS, 2000, 8000), turn("b2", "2026-03-09T10:05:00Z", SONNET, 2000, 18000)],
    "c": [turn("c1", "2026-03-10T09:00:00Z", SONNET, 1000, 4000)],
}
WEEK1 = {"turns": 4, "sessions": 2, "ie_per_turn": 10700.0, "cache_hit": 0.9898, "lever_sessions": 2, "applied_sessions": 1, "applied_share": 0.5}
WEEK2 = {"turns": 3, "sessions": 2, "ie_per_turn": 2666.7, "cache_hit": 0.8571, "lever_sessions": 1, "applied_sessions": 1, "applied_share": 1.0}


def outcome(since=None, sessions=None, raw=None):
    """build_outcome over a temp dir of `sessions` ({name: rows}, each file ends in one unparsable line) plus `raw` ({name: bytes})."""
    with tempfile.TemporaryDirectory() as d:
        for name, rows in (SESSIONS if sessions is None else sessions).items():
            (Path(d) / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json\n")
        for name, data in (raw or {}).items():
            (Path(d) / f"{name}.jsonl").write_bytes(data)
        return tr.build_outcome(d, since)


UTC = timezone.utc


class Outcome(unittest.TestCase):
    def test_weekly_rows_hand_computed(self):
        o = outcome()
        self.assertEqual(o["weeks"], [{"week": "2026-03-02", **WEEK1}, {"week": "2026-03-09", **WEEK2}])
        self.assertNotIn("before", o)

    def test_before_after_split(self):
        o = outcome(datetime(2026, 3, 9, tzinfo=timezone.utc))
        self.assertEqual((o["before"], o["after"], o["straddling_sessions"]), (WEEK1, WEEK2, 0))
        self.assertNotIn("straddle", tr.render_outcome(o))

    def test_empty_side_is_none_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(tr.build_outcome(d, datetime(2026, 3, 9, tzinfo=timezone.utc))["before"],
                             {"turns": 0, "sessions": 0, "ie_per_turn": None, "cache_hit": None,
                              "lever_sessions": 0, "applied_sessions": 0, "applied_share": None})

    def test_levers(self):
        self.assertEqual(tr.session_levers([]), ([], []))
        # reaches the window, never drops: triggered, not applied; a sonnet-only session never triggers downshift
        t = [{"input_tokens": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": c, "model": SONNET} for c in (100_000, 250_000, 300_000)]
        self.assertEqual(tr.session_levers(t), (["compact"], []))

    def test_cache_writes_in_denominator_and_multipliers_and_iterations_not_turns(self):
        # input 1000 + 5m write 2000 * 1.25 + 1h write 4000 * 2 + read 10000 * 0.1 = 12500; prompt 1000+2000+4000+10000 = 17000.
        # The advisor iteration (50000 input) is nested spend, not a turn: it must change neither turns nor ie/turn.
        w = turn("w1", "2026-03-02T10:00:00Z", OPUS, 1000, 10_000)
        w["message"]["usage"].update({"cache_creation": {"ephemeral_5m_input_tokens": 2000, "ephemeral_1h_input_tokens": 4000},
                                      "iterations": [{"type": "advisor_message", "model": OPUS, "input_tokens": 50_000, "output_tokens": 10}]})
        row = outcome(sessions={"w": [w]})["weeks"][0]
        self.assertEqual((row["turns"], row["ie_per_turn"], row["cache_hit"]), (1, 12500.0, 0.5882))

    def test_utc_week_boundary(self):
        # Sun 23:59:59Z and +02:00 01:00 Mon local (= Sun 23:00Z) are the week of 03-02; Mon 00:00:00Z starts 03-09.
        rows = [turn("k1", "2026-03-08T23:59:59Z", SONNET, 100, 0), turn("k2", "2026-03-09T00:00:00Z", SONNET, 100, 0),
                turn("k3", "2026-03-09T01:00:00+02:00", SONNET, 100, 0)]
        weeks = outcome(sessions={"k": rows})["weeks"]
        self.assertEqual([(w["week"], w["turns"], w["sessions"], w["ie_per_turn"], w["cache_hit"]) for w in weeks],
                         [("2026-03-02", 2, 1, 100.0, 0.0), ("2026-03-09", 1, 0, 100.0, 0.0)])

    def test_session_straddling_since_splits_turns_but_counts_once_by_first_turn(self):
        rows = [turn("s1", "2026-03-08T23:00:00Z", OPUS, 100, 0), turn("s2", "2026-03-09T01:00:00Z", SONNET, 100, 0)]
        o = outcome(datetime(2026, 3, 9, tzinfo=UTC), sessions={"s": rows})
        self.assertEqual((o["before"]["turns"], o["before"]["sessions"], o["before"]["lever_sessions"], o["before"]["applied_sessions"]), (1, 1, 1, 1))
        self.assertEqual((o["after"]["turns"], o["after"]["sessions"], o["after"]["lever_sessions"], o["after"]["applied_share"]), (1, 0, 0, None))
        self.assertEqual(o["straddling_sessions"], 1)
        self.assertIn("1 session(s) straddle --since: counted in before (first turn)", tr.render_outcome(o))

    def test_straddle_uses_latest_timestamp_not_last_line(self):
        rows = [turn("s1", "2026-03-08T23:00:00Z", OPUS, 100, 0), turn("s2", "2026-03-09T01:00:00Z", OPUS, 100, 0), turn("s3", "2026-03-08T23:30:00Z", OPUS, 100, 0)]
        self.assertEqual(outcome(datetime(2026, 3, 9, tzinfo=UTC), sessions={"s": rows})["straddling_sessions"], 1)

    def test_resumed_copy_counts_once_in_the_longest_transcript(self):
        # "a" sorts first but holds only the prefix; "b" is the resume (same two requestIds + one new turn). By name order
        # a = compact triggered not applied, b = r3 alone; the longest-owns rule keeps one session whose drop is seen.
        pre = [turn("r1", "2026-03-02T10:00:00Z", OPUS, 1000, 99_000), turn("r2", "2026-03-02T10:05:00Z", OPUS, 1000, 249_000)]
        r3 = turn("r3", "2026-03-02T10:10:00Z", OPUS, 1000, 39_000)
        row = outcome(sessions={"a": pre, "b": pre + [r3]})["weeks"][0]
        self.assertEqual((row["turns"], row["sessions"], row["lever_sessions"], row["applied_sessions"]), (3, 1, 1, 1))

    def test_unreadable_files_are_counted_and_named_empty_is_not(self):
        o = outcome(sessions={"ok": SESSIONS["d"]}, raw={"bad": b"\xff\xfe\x00", "junk": b"garbage\n", "empty": b""})
        self.assertEqual(o["unreadable_sessions"], 2)
        self.assertEqual(o["unreadable_files"], ["bad.jsonl", "junk.jsonl"])
        self.assertIn("2 session(s) unreadable: bad.jsonl, junk.jsonl", tr.render_outcome(o))

    def test_no_turns_and_proxy_caveat_visible(self):
        o = outcome(sessions={})
        text = tr.render_outcome(o)
        self.assertIn("no turns", text)
        self.assertIn("proxy triggers — correlation, not cause", text)
        self.assertEqual((o["proxy"], o["note"] == tr.OUTCOME_NOTE), (True, True))
        self.assertIn("no turns", tr.render_outcome(outcome(datetime(2030, 1, 1, tzinfo=UTC))).split("after")[-1])
        self.assertIn("PROXY", tr.build_parser().format_help())

    def test_since_without_offset_is_local_time(self):
        # Fixed zone UTC+02:00 (POSIX "Etc/GMT-2" is east of UTC, no DST): a naive --since keeps that literal offset, "Z" stays UTC.
        script = str(ROOT / ".claude/skills/agentic-ceo/scripts/token_report.py")
        with tempfile.TemporaryDirectory() as d:
            for since, want in (("2026-03-09T00:00:00", "2026-03-09T00:00:00+02:00"), ("2026-03-09T00:00:00Z", "2026-03-09T00:00:00+00:00")):
                r = subprocess.run([sys.executable, script, "--outcome", d, "--since", since, "--json"],
                                   env={**os.environ, "TZ": "Etc/GMT-2"}, capture_output=True, text=True)
                self.assertEqual((r.returncode, json.loads(r.stdout)["since"]), (0, want), r.stderr)

    def test_outcome_refuses_to_mix_with_other_modes(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()) as err:
            for extra in (["--rollup", d], ["--session", d + "/x.jsonl"], ["--by", "week"], ["--group", "model"], ["--advise"], ["--nudge"], ["--limit", "5"],
                          ["--top", "3"], ["--rates", d], ["--project", d], ["--nudge-cache", d + "/f"]):
                err.truncate(0)
                self.assertEqual(tr.main(["--outcome", d, *extra]), tr.ERROR, extra)
                self.assertIn("stands alone", err.getvalue(), extra)
            self.assertEqual(tr.main(["--outcome", ""]), tr.ERROR)  # empty DIR is an error, not "mode off"

    def test_outcome_refuses_other_modes_even_with_default_or_empty_values(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()) as err:
            for extra in (["--top", "5"], ["--project", "."], ["--rollup", ""], ["--session", ""], ["--rates", ""], ["--nudge-cache", ""], ["--apply", ""]):
                err.truncate(0)
                self.assertEqual(tr.main(["--outcome", d, *extra]), tr.ERROR, extra)
                self.assertIn("stands alone", err.getvalue(), extra)

    def test_cli_json_and_text_never_echo_content(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.jsonl").write_text("".join(json.dumps(r) + "\n" for r in SESSIONS["a"]))
            for argv, key in ((["--json"], '"weeks"'), ([], "ie/turn=13900.0")):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = tr.main(["--outcome", d, "--since", "2026-03-01T00:00:00Z", *argv])
                self.assertEqual(rc, 0)
                self.assertIn(key, buf.getvalue())
                self.assertNotIn("SECRET", buf.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tr.main(["--outcome", d + "/missing"]), tr.ERROR)
                self.assertEqual(tr.main(["--outcome", d, "--since", "nope"]), tr.ERROR)


if __name__ == "__main__":
    unittest.main()
