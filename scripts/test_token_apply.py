#!/usr/bin/env python3
"""Tests for token_report.py `fix_plan` / `apply_plan` / `--fix-plan` / `--apply` (settings patch for measured levers).

Pure-dict reports and temp-dir settings files only; no real settings file is read or written.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import token_report as tr  # noqa: E402
from test_token_lever_rank import rep  # noqa: E402

JUMPY = [0, 60_000, 120_000, 180_000]  # each main turn grows the context past ADV["jump"]


def firing():
    """Report where every mapped lever fires: 1h pin, auto-compact at 200000, lane tail with p90 200 under the cap."""
    r = rep(pin=400, tail=300)
    r["auto_compact"] = {"saving_share_of_main_ie": 0.5, "window": 200_000, "saving_ie_upper": 500.0, "compactions": 1, "restart_tokens": 30_000}
    r["lane_tail"]["p90_tool_calls"] = 200
    return r


def feat(set_=()):
    return {"ctx": JUMPY, "isset": lambda *names: any(n in set_ for n in names)}


class FixPlan(unittest.TestCase):
    def test_patch_contents(self):
        self.assertEqual(tr.fix_plan(firing(), feat()), {
            "promptCacheTtl": "1h", "autoCompactWindow": 200_000, "bashOutputMaxChars": 10_000, "env": {"LANE_TOOL_CAP": "200"}})

    def test_set_keys_are_skipped(self):
        plan = tr.fix_plan(firing(), feat({"promptCacheTtl", "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "BASH_MAX_OUTPUT_LENGTH"}))
        self.assertEqual(plan, {"env": {"LANE_TOOL_CAP": "200"}})
        self.assertEqual(tr.fix_plan(firing(), feat({"promptCacheTtl", "autoCompactWindow", "bashOutputMaxChars", "LANE_TOOL_CAP"})), {})

    def test_no_invented_values(self):
        plan = tr.fix_plan(firing(), feat())
        self.assertNotIn("CLAUDE_CODE_SUBAGENT_MODEL", json.dumps(plan))  # its rule names no value
        self.assertEqual(plan["autoCompactWindow"], firing()["auto_compact"]["window"])
        self.assertEqual(plan["env"]["LANE_TOOL_CAP"], str(firing()["lane_tail"]["p90_tool_calls"]))
        self.assertEqual(tr.fix_plan(rep(), {"ctx": [], "isset": lambda *n: False}), {})  # nothing fired -> nothing patched

    def test_lane_cap_never_raised(self):
        r = firing()
        r["lane_tail"]["p90_tool_calls"] = 300  # above the shipped 250: "lowering" to it would raise the cap
        self.assertNotIn("env", tr.fix_plan(r, feat()))


class Apply(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        self.path = self.dir / "settings.json"
        self.bak = Path(str(self.path) + ".bak")
        self.plan = tr.fix_plan(firing(), feat())

    def test_merges_only_absent_keys_and_backs_up(self):
        orig = {"promptCacheTtl": "5m", "env": {"X": "\u00e9"}}
        self.path.write_text(json.dumps(orig))
        wrote, created = tr.apply_plan(str(self.path), self.plan)
        self.assertEqual((wrote, created), (["autoCompactWindow", "bashOutputMaxChars", "env.LANE_TOOL_CAP"], False))
        got = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(got["promptCacheTtl"], "5m")  # existing value kept
        self.assertEqual(got["env"], {"X": "\u00e9", "LANE_TOOL_CAP": "200"})
        self.assertIn("\u00e9", self.path.read_text(encoding="utf-8"))  # ensure_ascii=False
        self.assertEqual(json.loads(self.bak.read_text()), orig)

    def test_idempotent_and_first_backup_survives(self):
        self.path.write_text('{"a": 1}')
        self.assertTrue(tr.apply_plan(str(self.path), self.plan)[0])
        first = self.path.read_text()
        self.assertEqual(tr.apply_plan(str(self.path), self.plan), ([], False))
        self.assertEqual(self.path.read_text(), first)
        self.assertEqual(self.bak.read_text(), '{"a": 1}')
        # a later run that adds a key must not overwrite the first original
        tr.apply_plan(str(self.path), {"newKey": 1})
        self.assertEqual(self.bak.read_text(), '{"a": 1}')
        self.assertEqual(json.loads(self.path.read_text())["newKey"], 1)

    def test_modes_preserved(self):
        self.path.write_text("{}")
        os.chmod(self.path, 0o600)
        tr.apply_plan(str(self.path), self.plan)
        self.assertEqual((self.path.stat().st_mode & 0o777, self.bak.stat().st_mode & 0o777), (0o600, 0o600))
        self.assertEqual([p.name for p in self.dir.iterdir() if p.name.endswith(".tmp")], [])  # temp file replaced away

    def test_symlink_target_is_edited_not_the_link(self):
        sub = self.dir / "real"
        sub.mkdir()
        (sub / "s.json").write_text("{}")
        link = self.dir / "link.json"
        link.symlink_to(sub / "s.json")
        tr.apply_plan(str(link), self.plan)
        self.assertTrue(link.is_symlink())
        self.assertIn("promptCacheTtl", json.loads((sub / "s.json").read_text()))
        self.assertTrue((sub / "s.json.bak").exists())

    def test_invalid_json_refused_untouched(self):
        for text in ("{not json", "[1]", '{"env": 3}'):
            self.path.write_text(text)
            with self.assertRaises(ValueError):
                tr.apply_plan(str(self.path), self.plan)
            self.assertEqual(self.path.read_text(), text)
            self.assertFalse(self.bak.exists())

    def test_oserror_becomes_valueerror(self):
        self.path.write_text("{}")
        real = os.replace
        os.replace = lambda *a: (_ for _ in ()).throw(OSError("disk full"))
        self.addCleanup(setattr, os, "replace", real)
        with self.assertRaisesRegex(ValueError, "disk full"):
            tr.apply_plan(str(self.path), self.plan)
        self.assertEqual(self.path.read_text(), "{}")
        self.assertEqual([p.name for p in self.dir.iterdir() if p.name.endswith(".tmp")], [])  # temp cleaned up

    def test_missing_path_created_only_if_dir_exists(self):
        wrote, created = tr.apply_plan(str(self.path), self.plan)
        self.assertTrue(created and wrote)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.path.read_text())["promptCacheTtl"], "1h")
        self.assertFalse(self.bak.exists())  # nothing to back up
        with self.assertRaises(ValueError):
            tr.apply_plan(str(self.dir / "nodir" / "s.json"), self.plan)
        self.assertEqual(tr.apply_plan(str(self.dir / "empty.json"), {}), ([], False))  # empty plan creates nothing
        self.assertFalse((self.dir / "empty.json").exists())

    def test_round_trip_through_load_settings(self):
        home = self.dir / "home"
        home.mkdir()
        tr.apply_plan(str(home / "settings.json"), self.plan)
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(home)}):
            cfg, env, _mcp, bad = tr.load_settings(str(self.dir))
        self.assertEqual(bad, [])
        f = {"ctx": JUMPY, "isset": lambda *n: any(x in cfg or x in env for x in n)}
        self.assertEqual(tr.fix_plan(firing(), f), {})

    def test_set_levers_leave_lever_lines_and_ranking(self):
        r = firing()  # main_turns and subagents_count are 0, so the info lines are skipped
        text = "\n".join(tr._gap_tier_lines({**r, "lever_ranking": tr.lever_ranking(r)}))
        self.assertIn("Lever: pin the main", text)
        self.assertEqual(len(tr.lever_ranking(r)), 3)
        r["advice"] = {"muted": ["pin", "compact", "tail"]}
        text = "\n".join(tr._gap_tier_lines({**r, "lever_ranking": tr.lever_ranking(r)}))
        self.assertEqual((tr.lever_ranking(r), "Lever: pin" in text, "Lever: auto-compact" in text, "Lever: lower LANE" in text),
                         ([], False, False, False))

    def test_cli_unmocked_plan_apply_and_rerun(self):
        sess = self.dir / "s.jsonl"
        sess.write_text(json.dumps({"type": "assistant", "requestId": "m", "timestamp": "2026-10-19T10:00:00+00:00",
                                    "message": {"model": "claude-sonnet-5", "usage": {"input_tokens": 1, "output_tokens": 1}}}) + "\n")
        (self.dir / "s" / "subagents").mkdir(parents=True)

        def lane(calls, ie):
            blk = [{"type": "tool_use", "id": f"t{i}"} for i in range(calls)]
            return json.dumps({"type": "assistant", "requestId": "r", "timestamp": "2026-10-19T10:00:01+00:00",
                               "message": {"model": "claude-sonnet-5", "content": blk, "usage": {"input_tokens": ie, "output_tokens": 1}}}) + "\n"
        for i in range(9):
            (self.dir / "s" / "subagents" / f"a{i}.jsonl").write_text(lane(100, 10))
        (self.dir / "s" / "subagents" / "big.jsonl").write_text(lane(1000, 100_000))  # tail beyond 250, p90 = 100
        home = self.dir / "home"
        home.mkdir()
        proj = self.dir / "proj"
        proj.mkdir()

        def run(*extra):
            out, err = io.StringIO(), io.StringIO()
            env = {k: v for k, v in os.environ.items() if k != "LANE_TOOL_CAP"}
            with mock.patch.dict(os.environ, {**env, "CLAUDE_CONFIG_DIR": str(home)}, clear=True), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = tr.main(["--session", str(sess), "--project", str(proj), *extra])
            return code, out.getvalue(), err.getvalue()

        code, out, _ = run("--fix-plan")
        self.assertEqual((code, json.loads(out)), (tr.OK, {"env": {"LANE_TOOL_CAP": "100"}}))
        self.assertIn("Lever: lower LANE_TOOL_CAP", run("--advise")[1])
        target = home / "settings.json"
        code, out, _ = run("--apply", str(target))
        self.assertEqual(code, tr.OK)
        self.assertIn("created", out)
        self.assertIn("wrote env.LANE_TOOL_CAP", out)
        self.assertIn("re-run token_report --advise next session to measure", out)
        self.assertEqual(json.loads(target.read_text()), {"env": {"LANE_TOOL_CAP": "100"}})
        code, out, _ = run("--apply", str(target))  # now set -> plan empty, lever muted
        self.assertEqual((code, out.strip()), (tr.OK, "nothing to apply"))
        self.assertNotIn("Lever: lower LANE_TOOL_CAP", run("--advise")[1])
        (proj / ".claude").mkdir()
        (proj / ".claude" / "settings.json").write_text("{bad")  # unreadable settings: plan empty, but say why
        target.unlink()
        code, out, err = run("--apply", str(target))
        self.assertEqual((code, out, target.exists()), (tr.OK, "nothing to apply\n", False))
        self.assertIn("unreadable", err)
        target.write_text("{bad")  # an unusable target itself is refused
        self.assertEqual(run("--apply", str(target))[0], tr.ERROR)
        code, out, err = run("--apply", str(self.dir / "nodir" / "s.json"))
        self.assertEqual((code, out), (tr.ERROR, ""))


if __name__ == "__main__":
    unittest.main()
