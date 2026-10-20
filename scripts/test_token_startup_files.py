#!/usr/bin/env python3
"""Tests for token_report.py `startup_files`: per-file startup cost across lanes, ranking, lever, and the --json key.

Fixtures are synthetic (temp dirs, one main turn, lanes of known turn counts); no real session or config is read.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
import token_report as tr  # noqa: E402


def turn(n, rid):
    return {"type": "assistant", "requestId": rid, "timestamp": f"2026-10-19T10:00:{n:02d}+00:00",
            "message": {"model": "claude-sonnet-5", "usage": {"input_tokens": 1000, "output_tokens": 1}}}


class Env:
    """Temp project + config dir + session with lanes of the given turn counts; cleaned up by the test."""

    def __init__(self, tc, lanes=(3, 1), files=None, user=None, mem=None):
        self.d = tempfile.TemporaryDirectory()
        tc.addCleanup(self.d.cleanup)
        root = Path(self.d.name)
        self.proj, self.cfg = root / "proj", root / "cfg"
        (self.proj / ".claude").mkdir(parents=True)
        self.cfg.mkdir()
        for name, n in (files or {}).items():
            (self.proj / name).write_text("x" * n)
        if user:
            (self.cfg / "CLAUDE.md").write_text("x" * user)
        if mem:
            m = self.cfg / "projects" / tr.re.sub(r"[^A-Za-z0-9]", "-", str(self.proj.resolve())) / "memory"
            m.mkdir(parents=True)
            (m / "MEMORY.md").write_text("x" * mem)
        (root / "s.jsonl").write_text(json.dumps(turn(0, "m")) + "\n")
        (root / "s" / "subagents").mkdir(parents=True)
        for i, n in enumerate(lanes):
            (root / "s" / "subagents" / f"agent-{i}.jsonl").write_text("".join(json.dumps(turn(i + 1, f"r{i}-{k}")) + "\n" for k in range(n)))
        self.session = str(root / "s.jsonl")

    def report(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.cfg)}):
            return tr.build_report(self.session, None, 5, tr.DEFAULT_RATES, project=str(self.proj))


class StartupFiles(unittest.TestCase):
    def test_arithmetic(self):
        # lanes of 3 and 1 turns: weight = 1.25*2 starts + 0.1*(2 + 0) later turns = 2.7; 400 bytes = 100 tokens est
        r = Env(self, files={"CLAUDE.md": 400}).report()
        [row] = r["startup_files"]
        self.assertEqual((row["file"], row["tokens_est"], row["ie_upper"], row["if_loaded"]), ("CLAUDE.md", 100, 270.0, False))
        session_ie = r["main"]["input_equivalent"] + r["subagents_totals"]["input_equivalent"]
        self.assertAlmostEqual(row["share_of_session_ie"], 270 / session_ie, places=4)

    def test_missing_files_skipped_and_no_project_or_lanes(self):
        e = Env(self, files={"CLAUDE.md": 40})
        self.assertEqual([r["file"] for r in e.report()["startup_files"]], ["CLAUDE.md"])
        self.assertEqual(tr.startup_files(None, [{"turns": 1}], 1), [])
        self.assertEqual(Env(self, lanes=(), files={"CLAUDE.md": 40}).report()["startup_files"], [])

    def test_ranking_order_and_if_loaded(self):
        r = Env(self, files={"CLAUDE.md": 400, "AGENTS.md": 800, ".claude/CLAUDE.md": 40}, user=1200, mem=80).report()
        self.assertEqual([x["file"] for x in r["startup_files"]],
                         ["user-level CLAUDE.md", "AGENTS.md", "CLAUDE.md", "project memory MEMORY.md", ".claude/CLAUDE.md"])
        self.assertEqual({x["file"] for x in r["startup_files"] if x["if_loaded"]}, {"AGENTS.md", "project memory MEMORY.md"})

    def test_largest_feeds_lever_ranking_and_text(self):
        r = Env(self, files={"CLAUDE.md": 400}, user=40000).report()
        top = r["lever_ranking"][0]
        self.assertEqual((top["lever"], top["saving_ie"], top["estimate"]),
                         ("trim user-level CLAUDE.md (estimate: 50% of its cost)", r["startup_files"][0]["ie_upper"] * tr.TRIM_FRACTION, True))
        text = tr.render_text(r)
        self.assertIn("Lever: trim or split user-level CLAUDE.md (est 10000 tokens): up to 27000.0 ie contributed, an estimated 13500.0 ie saved if 50% is cut", text)
        self.assertNotIn(str(Path(r["session"]).parent), text.split("Token report")[1].split("\n", 1)[1])

    def test_every_ranking_row_has_estimate_flag(self):
        from test_token_lever_rank import rep  # pure-dict report builder
        rows = tr.lever_ranking(rep(pin=400, tail=200, top_tier=0.9))
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["estimate"] for r in rows], [False, False, False])

    def test_small_file_does_not_fire_lever(self):
        r = Env(self, files={"CLAUDE.md": 40}).report()
        self.assertEqual(r["lever_ranking"], [])
        self.assertNotIn("Lever: trim", tr.render_text(r))

    def test_json_key_via_cli(self):
        e = Env(self, files={"CLAUDE.md": 400})
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(e.cfg)}), contextlib.redirect_stdout(buf):
            self.assertEqual(tr.main(["--session", e.session, "--json", "--project", str(e.proj)]), 0)
        self.assertEqual(json.loads(buf.getvalue())["startup_files"][0]["file"], "CLAUDE.md")

    def test_remainder(self):
        # each lane's first turn is 1000 startup tokens; 400 bytes = 100 file tokens -> 900/lane. weights: lane0 (3 turns) 1.45, lane1 1.25
        r = Env(self, files={"CLAUDE.md": 400}).report()
        sr = r["startup_remainder"]
        self.assertEqual((sr["tokens"], sr["ie_upper"], sr["share_of_startup"]), (1800, 900 * 1.45 + 900 * 1.25, 0.9))
        lane_ie = r["subagents_totals"]["input_equivalent"]
        self.assertAlmostEqual(sr["share_of_lane_ie"], sr["ie_upper"] / lane_ie, places=4)
        self.assertIn("system prompt, tool/MCP definitions, skill listing, brief", sr["label"])
        text = tr.render_text(r)
        self.assertIn("Startup remainder", text)
        self.assertIn("Lever: the remainder dominates lane startup", text)

    def test_remainder_floors_at_zero_and_not_dominant(self):
        sr = tr.startup_remainder([{"startup_tokens": 50, "turns": 1, "input_equivalent": 50}], [{"tokens_est": 80}])
        self.assertEqual((sr["tokens"], sr["ie_upper"]), (0, 0))
        self.assertIsNone(tr.startup_remainder([], []))
        r = Env(self, files={"CLAUDE.md": 3600}).report()  # 900 file tokens of 1000 -> remainder 10%
        self.assertNotIn("Lever: the remainder dominates", tr.render_text(r))

    def test_remainder_below_lane_ie_floor_does_not_fire(self):
        # one 40-turn lane: remainder is 90% of startup but 900 x (1.25 + 0.1 x 39) = 4635 ie of 40000 lane ie = 11.6% < REMAINDER_LEVER_SHARE
        r = Env(self, lanes=(40,), files={"CLAUDE.md": 400}).report()
        sr = r["startup_remainder"]
        self.assertGreater(sr["share_of_startup"], 0.5)
        self.assertLess(sr["share_of_lane_ie"], tr.REMAINDER_LEVER_SHARE)
        text = tr.render_text(r)
        self.assertIn("Startup remainder", text)
        self.assertNotIn("Lever: the remainder dominates", text)

    def test_since_skips_files_and_remainder(self):
        e = Env(self, files={"CLAUDE.md": 400})
        since = tr.parse_timestamp("2026-10-19T09:00:00+00:00")
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(e.cfg)}):
            r = tr.build_report(e.session, since, 5, tr.DEFAULT_RATES, project=str(e.proj))
        self.assertEqual((r["startup_files"], r["startup_remainder"], r["startup_files_skipped"]), ([], None, "--since"))
        self.assertIn("Startup files not priced under --since", tr.render_text(r))
        self.assertIsNone(Env(self).report()["startup_files_skipped"])

    def test_file_contents_never_surface(self):
        e = Env(self)
        (e.proj / "CLAUDE.md").write_text("SENTINEL-do-not-print " * 50)
        r = e.report()
        self.assertTrue(r["startup_files"])
        self.assertNotIn("SENTINEL", tr.render_text(r) + json.dumps(r))

    def test_remainder_in_json_and_absent_without_project(self):
        e = Env(self, files={"CLAUDE.md": 400})
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(e.cfg)}), contextlib.redirect_stdout(buf):
            tr.main(["--session", e.session, "--json", "--project", str(e.proj)])
        self.assertEqual(json.loads(buf.getvalue())["startup_remainder"]["tokens"], 1800)
        self.assertIsNone(tr.build_report(e.session, None)["startup_remainder"])

    def test_default_build_report_has_empty_key(self):
        self.assertEqual(Env(self, files={"CLAUDE.md": 400}).report() and tr.build_report(
            Env(self).session, None)["startup_files"], [])


if __name__ == "__main__":
    unittest.main()
