#!/usr/bin/env python3
"""Tests for the active-window part of cost_statusline.py: `win <left> | <pct> | <rate>` from the transcript tail via
token_report.burn_blocks, the tail-computed cache fallback, the `~` clip mark, the plain-output fallbacks, fail-silence,
and a CPU bound on a 50 MB transcript. Fixtures are generated in a temp dir from fictional data.
"""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/skills/agentic-delivery/scripts/cost_statusline.py"
sys.path.insert(0, str(SCRIPT.parent))
import cost_statusline as cs  # noqa: E402

NOW = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)


def turn(ts, i, pad=0):
    """One main-thread assistant line: 100k input + 300k cache read (input-eq 130k), `pad` filler chars."""
    u = {"input_tokens": 100000, "cache_read_input_tokens": 300000, "cache_creation_input_tokens": 0, "output_tokens": 0}
    return json.dumps({"type": "assistant", "requestId": f"r{i}", "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                       "message": {"model": "claude-sonnet-5", "usage": u, "content": "x" * pad}})


class Window(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def transcript(self, stamps, pad=0):
        p = Path(self.d.name) / "t.jsonl"
        p.write_text("\n".join(turn(t, i, pad) for i, t in enumerate(stamps)) + "\n")
        return str(p)

    @staticmethod
    def last_bytes(path, n):
        return sum(len(ln) + 1 for ln in Path(path).read_bytes().split(b"\n")[-n - 1:-1])

    def mins(self, *offsets):
        return [NOW - timedelta(minutes=m) for m in offsets]

    def test_window_line(self):
        p = self.transcript(self.mins(100, 70, 40, 10))  # window opens 10:00, ends 15:00; 4 x 130k over 100 min
        data = {"transcript_path": p, "rate_limits": {"five_hour": {"used_percentage": 62.4}}}
        self.assertEqual(cs.render(data, now=NOW), "tail cache 75% | win 2h30m left | 62% | +5k/min")

    def test_host_hit_ratio_wins_and_resets_at_is_exact(self):
        p = self.transcript(self.mins(100, 10))
        data = {"transcript_path": p, "prompt_cache": {"hit_ratio": 0.5},
                "rate_limits": {"five_hour": {"resets_at": NOW.timestamp() + 3600}}}
        self.assertTrue(cs.render(data, now=NOW).startswith("cache 50% | win 1h00m left"))

    def test_early_window_has_no_rate_and_short_left(self):
        p = self.transcript(self.mins(5))  # 5 min in: under ACTIVE_MIN_ELAPSED, no projection
        self.assertEqual(cs.render({"transcript_path": p, "rate_limits": {"five_hour": {"resets_at": NOW.timestamp() + 600}}}, now=NOW),
                         "tail cache 75% | win 10m left")

    def test_clipped_tail_marks_window_unsure(self):
        p = self.transcript(self.mins(100, 70, 40, 10), pad=300)
        with mock.patch.object(cs, "TAIL", self.last_bytes(p, 2) + 5):  # keeps 2 whole turns, all newer than 5h
            self.assertIn("win ~", cs.render({"transcript_path": p}, now=NOW))
        p = self.transcript([NOW - timedelta(hours=7), NOW - timedelta(minutes=70), NOW - timedelta(minutes=10)], pad=300)
        with mock.patch.object(cs, "TAIL", self.last_bytes(p, 3) + 5):  # clipped, but a 5h gap inside the tail anchors the chain
            out = cs.render({"transcript_path": p}, now=NOW)
        self.assertIn("win 3h30m left", out)
        self.assertNotIn("~", out)

    def test_reaching_back_past_5h_without_a_gap_is_not_enough(self):
        now = datetime(2026, 1, 1, 12, 42, tzinfo=timezone.utc)  # 21 hourly turns at :42; the full-file chain opens a block every 5th turn
        p = self.transcript([now - timedelta(hours=h) for h in range(20, -1, -1)], pad=300)
        self.assertIn("win 4h18m left", cs.render({"transcript_path": p}, now=now))
        with mock.patch.object(cs, "TAIL", self.last_bytes(p, 4) + 5):  # clipped to the last 4 turns: the chain restarts mid-block
            out = cs.render({"transcript_path": p}, now=now)
        self.assertIn("win ~1h18m left", out)
        self.assertNotIn("4h18m", out)

    def test_rate_keeps_the_mark_when_resets_at_gives_the_time(self):
        p = self.transcript(self.mins(100, 70, 40, 10), pad=300)
        with mock.patch.object(cs, "TAIL", self.last_bytes(p, 3) + 5):
            out = cs.render({"transcript_path": p, "rate_limits": {"five_hour": {"resets_at": NOW.timestamp() + 3600}}}, now=NOW)
        self.assertEqual(out, "tail cache 75% | win 1h00m left | ~+6k/min")

    def test_insane_resets_at_falls_back_to_the_model(self):
        p = self.transcript(self.mins(100, 70, 40, 10))
        for bad in (NOW.timestamp() + 10 * 3600, float("inf"), float("nan"), NOW.timestamp() - 60):
            out = cs.render({"transcript_path": p, "rate_limits": {"five_hour": {"resets_at": bad}}}, now=NOW)
            self.assertIn("win 2h30m left", out, bad)

    def test_window_failure_keeps_the_tail_cache_share(self):
        p = self.transcript(self.mins(100, 10))
        import token_report as tr
        with mock.patch.object(tr, "burn_blocks", side_effect=RuntimeError("x")):
            self.assertEqual(cs.render({"transcript_path": p}, now=NOW), "tail cache 75%")

    def test_import_leaves_the_bytecode_flag_alone(self):
        p = self.transcript(self.mins(10))
        sys.dont_write_bytecode = False
        cs.render({"transcript_path": p}, now=NOW)
        self.assertFalse(sys.dont_write_bytecode)

    def test_idle_window_is_left_out(self):
        p = self.transcript([NOW - timedelta(hours=9)])
        self.assertEqual(cs.render({"transcript_path": p}, now=NOW), "tail cache 75%")

    def test_plain_output_without_token_report_or_transcript(self):
        p = self.transcript(self.mins(100, 10))
        base = {"cost": {"total_cost_usd": 0.5}, "prompt_cache": {"hit_ratio": 0.9}}
        with mock.patch.dict(sys.modules, {"token_report": None}):  # import fails: the 3-field line, tail ratio not computed
            self.assertEqual(cs.render({**base, "transcript_path": p}, now=NOW), "est $0.50 | cache 90%")
            self.assertEqual(cs.render({"cost": {"total_cost_usd": 0.5}, "transcript_path": p}, now=NOW), "est $0.50")
        for bad in (str(Path(self.d.name)), str(Path(self.d.name) / "none"), 7, None):
            self.assertEqual(cs.render({**base, "transcript_path": bad}, now=NOW), "est $0.50 | cache 90%")

    def test_garbage_transcript_never_raises(self):
        p = Path(self.d.name) / "g.jsonl"
        p.write_bytes(b'{"usage"\n\xff\xfe"usage"\n{"message": 3, "usage": 1}\n' + turn(NOW, 1).encode()[:40])
        self.assertEqual(cs.render({"transcript_path": str(p)}, now=NOW), "")

    def run_script(self, stdin):
        return subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True), None

    def test_cli_fail_silent(self):
        for bad in ("{", "[]", '{"transcript_path": {}}'):
            r, _ = self.run_script(bad)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""), bad)

    def test_bounded_cpu_on_50mb_transcript(self):
        """CPU, not wall time: wall time flakes on a loaded runner. Only the tail is read, so cost does not grow with the file."""
        now = datetime.now(timezone.utc)
        p = Path(self.d.name) / "big.jsonl"
        old = (turn(now - timedelta(hours=3), 0) + "\n").encode()  # ~330 B, like a real usage-only line; no 5h gap in the tail
        with open(p, "wb") as fh:
            for _ in range(50_000_000 // len(old) // 1000 + 1):
                fh.write(old * 1000)
            fh.write(b"".join((turn(now - timedelta(minutes=60 - i), 90000 + i) + "\n").encode() for i in range(40)))
        self.assertGreater(p.stat().st_size, 50_000_000)
        data = {"transcript_path": str(p)}
        with mock.patch.dict(sys.modules):
            sys.modules.pop("token_report", None)  # include the import in the measure
            t = time.process_time()
            out = cs.render(data)
            cpu = time.process_time() - t
        self.assertIn("win ~", out)
        self.assertLess(cpu, 0.5, f"render used {cpu * 1000:.0f} ms CPU on a 50 MB transcript")
        r, _ = self.run_script(json.dumps(data))
        self.assertIn("win ~", r.stdout)


if __name__ == "__main__":
    unittest.main()
