#!/usr/bin/env python3
"""Tests for `token_report.py --rollup` across projects: `--group project|agent|model`, `--by month`, cache hit %, `--rollup auto`.

Fake transcripts only (fictional models and ids, generated in a temp dir). Hand-computed with the default rates
(claude-opus-5: in 5 / 5m-write 6.25 / read 0.5 / out 25 USD per 1M; claude-sonnet-5: 2 / 2.5 / 0.2 / 10; `acme-x` has no rate):
  proj-a/s1 main  a1 02-28 opus   100k in + 300k read                  = $0.50 + $0.15 = $0.65   (copied again into proj-b: counts once)
  proj-a/s1 main  a2 03-01 sonnet 200k 5m-write + 100k out             = $0.50 + $1.00 = $1.50
  proj-a/s1 lane  b1 03-01 sonnet (agentType builder)  50k in + 150k read = $0.10 + $0.03 = $0.13
  proj-a/s1 lane  e1 03-01 acme-x (agentType reviewer) 1k in           = UNPRICED
  proj-b/s2 main  c1 03-02 opus 40k out = $1.00;  f1 2025-12-15 sonnet 10k out = $0.10;  g1 2026-01-31 sonnet 10k out = $0.10
  proj-b/s2 lane  d1 03-02 sonnet (agentType builder) 50k out          = $0.50
Priced total $3.98. Every transcript also carries sentinel message text and meta descriptions that must never surface.
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402

OPUS, SONNET, ACME = "claude-opus-5", "claude-sonnet-5", "acme-x"
SECRET = "SECRET-SENTINEL"


def line(req, ts, model, inp=0, w5=0, cr=0, out=0):
    usage = {"input_tokens": inp, "cache_read_input_tokens": cr, "output_tokens": out,
             "cache_creation": {"ephemeral_5m_input_tokens": w5}, "cache_creation_input_tokens": w5}
    return {"type": "assistant", "requestId": req, "timestamp": ts,
            "message": {"model": model, "usage": usage, "content": [{"type": "text", "text": SECRET}]}}


def write(path, rows, meta=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    if meta:
        path.with_suffix(".meta.json").write_text(json.dumps({"agentType": meta, "description": SECRET}))


def fixture(projects):
    a1 = line("a1", "2026-02-28T10:00:00Z", OPUS, inp=100_000, cr=300_000)
    a, b = projects / "proj-a", projects / "proj-b"
    write(a / "s1.jsonl", [a1, line("a2", "2026-03-01T10:00:00Z", SONNET, w5=200_000, out=100_000)])
    write(a / "s1/subagents/agent-1.jsonl", [line("b1", "2026-03-01T11:00:00Z", SONNET, inp=50_000, cr=150_000)], "builder")
    write(a / "s1/subagents/agent-2.jsonl", [line("e1", "2026-03-01T12:00:00Z", ACME, inp=1000)], "reviewer")
    write(b / "s2.jsonl", [a1, line("c1", "2026-03-02T09:00:00Z", OPUS, out=40_000),
                           line("f1", "2025-12-15T09:00:00Z", SONNET, out=10_000),
                           line("g1", "2026-01-31T23:00:00Z", SONNET, out=10_000)])
    write(b / "s2/subagents/agent-1.jsonl", [line("d1", "2026-03-02T10:00:00Z", SONNET, out=50_000)], "builder")


def rows(roll):
    return [(g["group"], g["usd"], g["unpriced_models"], g["share"], g["raw_tokens"], g["cache_hit"]) for g in roll["groups"]]


class SpendRollupGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls._tmp.name).resolve()
        cls.projects = cls.base / "projects"
        fixture(cls.projects)
        cls.roll = {g: tr.build_rollup(str(cls.projects), None, by="month", group=g) for g in ("project", "agent", "model")}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_parent_dir_prices_every_project_once(self):
        r = self.roll["project"]
        self.assertEqual((r["projects"], r["total_usd"], r["unpriced_models"], r["lanes"]), (2, 3.98, [ACME], 3))
        self.assertEqual(sorted((s["project"], s["session"]) for s in r["sessions"]), [("proj-a", "s1"), ("proj-b", "s2")])
        self.assertEqual(tr.rollup_dirs(str(self.projects / "proj-a")), [str(self.projects / "proj-a")])

    def test_group_project(self):
        self.assertEqual(rows(self.roll["project"]), [
            ("proj-a", 2.28, [ACME], 0.5729, 901_000, 0.5618),
            ("proj-b", 1.7, [], 0.4271, 110_000, None)])  # the a1 copy in proj-b counts once, in proj-a; no prompt tokens = no hit %

    def test_group_agent_lane_types_and_unpriced(self):
        self.assertEqual(rows(self.roll["agent"]), [
            ("main", 3.35, [], 0.8417, 760_000, 0.5),
            ("builder", 0.63, [], 0.1583, 250_000, 0.75),
            ("reviewer", None, [ACME], None, 1000, 0.0)])

    def test_group_model(self):
        self.assertEqual(rows(self.roll["model"]), [
            (SONNET, 2.33, [], 0.5854, 570_000, 0.375),
            (OPUS, 1.65, [], 0.4146, 440_000, 0.75),
            (ACME, None, [ACME], None, 1000, 0.0)])

    def test_groups_partition_tokens_and_share(self):
        for g, roll in self.roll.items():
            self.assertEqual(sum(x["raw_tokens"] for x in roll["groups"]), 1_011_000, g)
            self.assertEqual(round(sum(x["share"] or 0 for x in roll["groups"]), 3), 1.0, g)

    def test_month_buckets_and_adjacency(self):
        got = [(b["bucket"], b["raw_tokens"], b["unpriced_models"], b["cache_hit"], b["delta"] and b["delta"]["raw_tokens"])
               for b in self.roll["project"]["buckets"]]
        self.assertEqual(got, [("2025-12-01", 10_000, [], None, None), ("2026-01-01", 10_000, [], None, 0),  # Dec -> Jan crosses the year
                               ("2026-02-01", 400_000, [], 0.75, 390_000), ("2026-03-01", 591_000, [ACME], 0.3741, 191_000)])
        usd = [b["usd"] for b in self.roll["project"]["buckets"]]
        self.assertAlmostEqual(usd[0], 0.1)
        self.assertAlmostEqual(usd[3], 3.13)
        self.assertAlmostEqual(self.roll["project"]["buckets"][2]["delta"]["usd"], 0.55)
        self.assertIsNone(self.roll["project"]["buckets"][3]["delta"]["usd"])  # Feb names no unpriced model, Mar does

    def test_month_gap_is_not_adjacent(self):
        turns = [{"timestamp": tr.parse_timestamp(t), "model": SONNET, "input_tokens": 1, "cache_write_5m": 0, "cache_write_1h": 0,
                  "cache_read": 0, "output_tokens": 0} for t in ("2026-01-05T00:00:00Z", "2026-03-05T00:00:00Z")]
        self.assertEqual([b["delta"] for b in tr.bucket_turns(turns, "month", tr.DEFAULT_RATES)], [None, None])

    def test_cache_hit_formula_and_rows(self):
        z = dict(tr.ZERO_USAGE)
        self.assertIsNone(tr.cache_hit(z))
        self.assertEqual(tr.cache_hit({**z, "input_tokens": 1, "cache_write_5m": 2, "cache_write_1h": 3, "cache_read": 4}), 0.4)
        self.assertEqual(tr.cache_hit({**z, "cache_read": 5}, {**z, "input_tokens": 5}), 0.5)
        r = self.roll["project"]
        self.assertEqual(r["cache_hit"], 0.5618)
        self.assertEqual(sorted((s["session"], s["cache_hit"]) for s in r["sessions"]), [("s1", 0.5618), ("s2", None)])

    def test_render_text_hit(self):
        report = tr.build_report(str(self.projects / "proj-a" / "s1.jsonl"), None, 5, tr.DEFAULT_RATES)
        text = tr.render_text(report)
        self.assertIn("cacheR=300000 out=100000 input-eq=", text)
        self.assertIn("hit=50.0%", text)  # main: 300k / (100k + 200k + 300k)
        self.assertIn("raw=201000 hit=74.6% session hit=56.2%", text)  # lanes 150k / 201k; whole session 450k / 801k
        solo = tr.render_text(tr.build_report(str(self.projects / "proj-b" / "s2.jsonl"), None, 5, tr.DEFAULT_RATES))
        self.assertIn("raw=50000 hit=n/a session hit=75.0%", solo)  # a lane with no prompt tokens: n/a, never 0%

    def test_render_rollup_unpriced_and_na(self):
        text = tr.render_rollup(self.roll["agent"], 5)
        self.assertIn("; cache hit 56.2%", text.splitlines()[0])
        self.assertIn("by agent:\n  main $3.35 84% raw=760000 hit=50.0%\n  builder $0.63 16% raw=250000 hit=75.0%\n  reviewer UNPRICED raw=1000 hit=0.0%", text)
        self.assertIn("  proj-b $1.70 43% raw=110000 hit=n/a", tr.render_rollup(self.roll["project"], 5))
        self.assertIn("2026-03-01 $3.13 + UNPRICED (acme-x) raw=591000 (+191000 tok) claude-sonnet-5", tr.render_rollup(self.roll["model"], 5))

    def test_no_transcript_content_in_output(self):
        for g, roll in self.roll.items():
            self.assertNotIn(SECRET, json.dumps(roll) + tr.render_rollup(roll, 0), g)


class Cli(unittest.TestCase):
    def run_cli(self, *argv, home=None, cwd=None):
        out, err, old = io.StringIO(), io.StringIO(), os.getcwd()
        env = {"CLAUDE_CONFIG_DIR": str(home)} if home else {}
        try:
            if cwd:
                os.chdir(cwd)
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = tr.main(list(argv))
        finally:
            os.chdir(old)
        return code, out.getvalue(), err.getvalue()

    def test_auto_reads_the_cwd_project_and_parent_reads_all(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d).resolve()
            cwd = base / "work.dir"
            cwd.mkdir()
            home = base / "home"
            fixture(home / "projects")
            enc = re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
            (home / "projects" / enc).mkdir()
            for n in ("s1.jsonl", "s1"):  # proj-a's session now sits directly in the cwd's encoded project dir
                os.rename(home / "projects" / "proj-a" / n, home / "projects" / enc / n)
            code, out, _ = self.run_cli("--rollup", "auto", "--group", "model", "--json", home=home, cwd=cwd)
            self.assertEqual(code, tr.OK)
            roll = json.loads(out)
            self.assertEqual((roll["dir"], roll["projects"], roll["total_usd"]), (str(home / "projects" / enc), 1, 2.28))
            self.assertEqual([g["group"] for g in roll["groups"]], [SONNET, OPUS, ACME])
            code, out, _ = self.run_cli("--rollup", str(home / "projects"), "--group", "project", "--by", "month")
            self.assertEqual(code, tr.OK)
            self.assertIn(f"by project:\n  {enc} $2.28 + UNPRICED (acme-x) 57% raw=901000 hit=56.2%\n  proj-b $1.70 43% raw=110000 hit=n/a", out)

    def test_auto_without_project_and_group_without_rollup_fail(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, err = self.run_cli("--rollup", "auto", home=Path(d), cwd=d)
            self.assertEqual((code, "found no project directory" in err), (tr.ERROR, True))
        code, _, err = self.run_cli("--group", "agent")
        self.assertEqual((code, "needs --rollup" in err), (tr.ERROR, True))


if __name__ == "__main__":
    unittest.main()
