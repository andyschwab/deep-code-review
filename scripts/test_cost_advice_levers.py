#!/usr/bin/env python3
"""Tests for the `token_report.py --advise` rules idle-resume, cache-bust and effort.

Each rule fires from synthetic usage, timestamp and model fields only and stays silent on the healthy look-alike.
Fixtures are fictional models and temp dirs; settings come from a temp project and a temp CLAUDE_CONFIG_DIR.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402

SONNET, OPUS = "claude-sonnet-5", "claude-opus-5"
T0 = datetime(2026, 10, 21, 9, 0, 0, tzinfo=timezone.utc)
BIG = 150_000


def turn(i, at, read, write, model=SONNET, out=50):
    """One assistant line `at` seconds after T0 with `read` cache-read and `write` 5m cache-write tokens."""
    usage = {"input_tokens": 10, "cache_read_input_tokens": read, "cache_creation_input_tokens": write,
             "cache_creation": {"ephemeral_5m_input_tokens": write, "ephemeral_1h_input_tokens": 0}, "output_tokens": out}
    return {"type": "assistant", "requestId": f"r{i}", "timestamp": (T0 + timedelta(seconds=at)).isoformat().replace("+00:00", "Z"),
            "message": {"model": model, "usage": usage, "content": [{"type": "text", "text": "SECRET-BODY"}]}}


def warm(n, start=0, step=30, model=SONNET, out=50):
    """n healthy turns: a big context read from cache, a little appended."""
    return [turn(start + k, (start + k) * step, BIG, 500, model, out) for k in range(n)]


class Levers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "proj" / ".claude").mkdir(parents=True)
        self.sess = self.dir / "s.jsonl"
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_EFFORT_LEVEL",)}
        env["CLAUDE_CONFIG_DIR"] = str(self.dir / "home")
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def advice(self, rows):
        return self.advice_raw("".join(json.dumps(r) + "\n" for r in rows))

    def advice_raw(self, text):
        self.sess.write_text(text)
        report = tr.build_report(str(self.sess), None, 5, tr.DEFAULT_RATES)
        return {a["id"]: a for a in tr.advise(report, None, tr.DEFAULT_RATES, str(self.dir / "proj"))["advice"]}

    def settings(self, obj):
        (self.dir / "proj" / ".claude" / "settings.json").write_text(json.dumps(obj))

    # -- idle-resume -------------------------------------------------------
    def cold_resumes(self, n, gap, size=BIG):
        rows, at = warm(3), 60  # last warm turn is at 60s, so every gap below is exact
        for k in range(n):
            at += gap
            rows += [turn(10 + k, at, 0, size)]  # cold: the whole context re-written, nothing read
        return rows

    def test_idle_resume_fires_on_two_cold_resumes_after_over_an_hour(self):
        got = self.advice(self.cold_resumes(2, 3700))
        self.assertIn("idle-resume", got)
        self.assertIn("2 main turns", got["idle-resume"]["evidence"])
        self.assertIsInstance(got["idle-resume"]["at_stake_usd"], float)

    def test_idle_resume_floor_boundary_is_inclusive_at_100k_context(self):
        for size, fires in ((99_989, False), (99_990, True)):  # resumed context is size + 10 input tokens
            self.assertEqual("idle-resume" in self.advice(self.cold_resumes(2, 3700, size=size)), fires, size)

    def test_idle_resume_silent_for_one_resume(self):
        self.assertNotIn("idle-resume", self.advice(self.cold_resumes(1, 3700)))

    def test_idle_resume_gap_boundary_is_strictly_over_one_hour(self):
        for gap, fires in ((3599, False), (3600, False), (3601, True)):
            self.assertEqual("idle-resume" in self.advice(self.cold_resumes(2, gap)), fires, gap)

    def test_idle_resume_silent_when_the_cache_was_read(self):
        rows, at = warm(3), 90
        for k in range(2):
            at += 3700
            rows.append(turn(10 + k, at, BIG, 500))  # long gap but the cache survived (a read, not a rewrite)
        self.assertNotIn("idle-resume", self.advice(rows))

    def test_idle_resume_silent_for_a_small_context(self):
        rows, at = [turn(0, 0, 5000, 100)], 0
        for k in range(2):
            at += 3700
            rows.append(turn(1 + k, at, 0, 5000))
        self.assertNotIn("idle-resume", self.advice(rows))

    # -- cache-bust --------------------------------------------------------
    def busts(self, n, gap=30, model_b=SONNET, size=BIG, read_b=0, grow=0):
        """n bust turns on a `size`-token warm context: only `read_b` of it is read back and `grow` new tokens are appended."""
        rows, at = [turn(k, 30 * k, size, 500) for k in range(3)], 60  # last warm turn is at 60s, so every gap below is exact
        for k in range(n):
            at += gap
            rows.append(turn(10 + 2 * k, at, read_b, size + 500 + grow - read_b, model_b))
            at += gap
            rows.append(turn(11 + 2 * k, at, size, 500, model_b))  # recovered: cache read again
        return rows

    def test_cache_bust_fires_on_two_rebuilds_inside_the_ttl(self):
        got = self.advice(self.busts(2))
        self.assertIn("cache-bust", got)
        self.assertIn("2 main turns", got["cache-bust"]["evidence"])

    def test_cache_bust_silent_for_one_rebuild(self):
        self.assertNotIn("cache-bust", self.advice(self.busts(1)))

    def test_cache_bust_gap_boundary_is_inclusive_at_150s(self):
        for gap, fires in ((149, True), (150, True), (151, False)):
            self.assertEqual("cache-bust" in self.advice(self.busts(2, gap=gap)), fires, gap)

    def test_cache_bust_silent_on_a_model_switch(self):
        rows = warm(3)
        for k in range(2):  # sonnet -> opus -> sonnet: a model switch rebuilds by design, other rules cover it
            m = (OPUS, SONNET)[k % 2]
            rows.append(turn(10 + k, 100 + 30 * k, 0, BIG + 500, m))  # same-size rebuilds: only the model check can silence them
        self.assertNotIn("cache-bust", self.advice(rows))

    def test_cache_bust_floor_boundary_is_inclusive_at_100k_context(self):
        for size, fires in ((99_489, False), (99_490, True)):  # warm context is size + 510 tokens
            self.assertEqual("cache-bust" in self.advice(self.busts(2, size=size)), fires, size)

    def test_cache_bust_read_fraction_boundary_is_5_percent_of_the_old_context(self):
        # size 99_490 makes the old context exactly 100_000 tokens, so 5% is the integer 5_000 and the test is strict (<)
        for read_b, fires in ((4_999, True), (5_000, False)):
            self.assertEqual("cache-bust" in self.advice(self.busts(2, size=99_490, read_b=read_b)), fires, read_b)

    def test_cache_bust_known_blind_spot_collapse_with_net_shrink_is_silent(self):
        # documented: a real collapse (read 0) whose context shrinks 150k -> 120k looks like compaction, so it stays silent
        rows = [turn(k, 30 * k, BIG, 500) for k in range(3)]
        for k in range(2):
            rows += [turn(10 + 2 * k, 120 + 60 * k, 0, 120_000), turn(11 + 2 * k, 150 + 60 * k, BIG, 500)]
        self.assertNotIn("cache-bust", self.advice(rows))

    def test_cache_bust_advice_text_discloses_the_blind_spots(self):
        rec = {rid: r for rid, _c, r, _d in tr.ADVICE_RULES}["cache-bust"]
        self.assertIn("heuristic", rec)
        self.assertIn("shrinks the context", rec)

    def test_cache_bust_silent_on_clearing_with_net_growth(self):
        # tool-result clearing keeps the prefix before the cleared results (20k read) while new content grows the context
        self.assertNotIn("cache-bust", self.advice(self.busts(3, read_b=20_000, grow=5_000)))

    def test_cache_bust_silent_on_a_context_that_only_grew(self):
        rows = [turn(k, 30 * k, BIG + 40_000 * k, 40_000) for k in range(6)]  # big tool results, previous context still read
        self.assertNotIn("cache-bust", self.advice(rows))

    def test_cache_bust_silent_after_two_compactions(self):
        rows = warm(3)
        for k in range(2):  # warm -> compaction (context falls to 20k, nothing read) -> grows back; two events reach the count
            at = 120 + 120 * k
            rows += [turn(10 + 3 * k, at, 0, 20_000), turn(11 + 3 * k, at + 30, 20_000, BIG - 20_000), turn(12 + 3 * k, at + 60, BIG, 500)]
        self.assertNotIn("cache-bust", self.advice(rows))

    def test_cache_bust_silent_on_tool_result_clearing_shaped_shrinks(self):
        rows = []
        for k in range(2):  # warm, then a 10% smaller context re-written (clearing): an expected rebuild, not a changed prefix
            rows += [turn(2 * k, 60 * k, BIG, 500), turn(2 * k + 1, 60 * k + 30, 0, int(BIG * 0.9))]
        self.assertNotIn("cache-bust", self.advice(rows + [turn(9, 400, BIG, 500)]))

    # -- effort ------------------------------------------------------------
    def heavy(self, n=12, out=3000):
        return [turn(k, 30 * k, 20_000, 500, out=out) for k in range(n)]

    def test_effort_fires_on_output_heavy_main_with_no_effort_set(self):
        got = self.advice(self.heavy())
        self.assertIn("effort", got)
        self.assertIn("3000 tokens per turn", got["effort"]["evidence"])
        self.assertIsInstance(got["effort"]["at_stake_usd"], float)

    def lean(self, n=12, out=3000):
        """Zero cache reads and a tiny write, so output is a large share of weighted tokens whatever the per-turn size."""
        return [turn(k, 30 * k, 0, 500, out=out) for k in range(n)]

    def test_effort_per_turn_and_turn_count_boundaries(self):
        for rows, fires in ((self.lean(out=1000), False), (self.lean(out=1499), False), (self.lean(out=1500), True),
                            (self.lean(n=9, out=3000), False), (self.lean(n=10, out=3000), True)):
            self.assertEqual("effort" in self.advice(rows), fires)

    def test_effort_share_boundary_is_inclusive_at_30_percent(self):
        # per turn: input-eq = 10 + 1.25 * write, output 3000; write 5592 makes output exactly 30% of input-eq plus output
        for write, fires in ((5_592, True), (5_593, False)):
            rows = [turn(k, 30 * k, 0, write, out=3000) for k in range(10)]
            self.assertEqual("effort" in self.advice(rows), fires, write)

    def test_effort_silent_when_light_short_or_already_set(self):
        self.assertNotIn("effort", self.advice(self.heavy(out=300)))
        self.assertNotIn("effort", self.advice(self.heavy(n=9)))
        self.assertNotIn("effort", self.advice([turn(k, 30 * k, BIG, 500, out=3000) for k in range(12)]))  # output is a small share
        self.settings({"effortLevel": "medium"})
        self.assertNotIn("effort", self.advice(self.heavy()))

    def test_effort_silent_when_env_or_saved_model_level_set(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_EFFORT_LEVEL": "low"}):
            self.assertNotIn("effort", self.advice(self.heavy()))
        self.settings({"modelSettings": {SONNET: {"effortLevel": "low"}}})
        self.assertNotIn("effort", self.advice(self.heavy()))

    def test_rules_never_echo_message_text(self):
        for rows in (self.cold_resumes(2, 3700), self.busts(2), self.heavy()):
            self.assertNotIn("SECRET-BODY", json.dumps(self.advice(rows)))

    def test_every_new_rule_cites_a_tip_that_names_it(self):
        tips = (ROOT / "docs/token-cost-tips.md").read_text()
        docs = {rid: doc for rid, _c, _r, doc in tr.ADVICE_RULES}
        for rid, num in (("idle-resume", 11), ("cache-bust", 6), ("effort", 3)):
            self.assertIn(f"tip {num}", docs[rid])
            block = tips.split(f"\n{num}. **", 1)[1].split(f"\n{num + 1}. **", 1)[0]
            self.assertIn(f"`{rid}`", block)

    # -- degenerate transcripts: no crash, no advice -----------------------
    def test_degenerate_transcripts_do_not_raise_or_fire(self):
        good = self.cold_resumes(2, 3700)
        nots = json.loads(json.dumps(good))
        for r in nots:
            del r["timestamp"]
        nousage = json.loads(json.dumps(good))
        for r in nousage:
            del r["message"]["usage"]
        nocc = json.loads(json.dumps(good))
        for r in nocc:
            del r["message"]["usage"]["cache_creation"]
        text = "".join(json.dumps(r) + "\n" for r in good)
        cases = {"empty": "", "single": json.dumps(good[0]) + "\n", "no timestamp": "".join(json.dumps(r) + "\n" for r in nots),
                 "no usage": "".join(json.dumps(r) + "\n" for r in nousage), "malformed line": "{not json\n" + text[:text.index("\n") + 1]}
        for name, raw in cases.items():
            got = self.advice_raw(raw)
            for rid in ("idle-resume", "cache-bust", "effort"):
                self.assertNotIn(rid, got, name)
        self.advice_raw("".join(json.dumps(r) + "\n" for r in nocc))  # legacy usage without the cache_creation split: must not raise


if __name__ == "__main__":
    unittest.main()
