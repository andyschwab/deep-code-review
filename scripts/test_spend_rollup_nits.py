#!/usr/bin/env python3
"""Regression tests for three review nits on the spend rollup and the nudge watchdog.

Covers: an unreadable project dir under a rollup parent is skipped (not a crash); `--rollup auto` with no project dir errors clearly and
never falls back to a directory literally named `auto`; the nudge publishes its advise line to the watchdog before the receipt runs, so a
timeout during the receipt still caches it. Fixtures are synthetic.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_spend_nudge as n  # noqa: E402

tr = n.tr


class RollupDirs(unittest.TestCase):
    def test_unreadable_project_dir_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            for name in ("good", "locked"):
                (parent / name).mkdir()
                (parent / name / "s.jsonl").write_text("")
            (parent / "locked").chmod(0)
            try:
                if os.access(parent / "locked", os.R_OK):
                    self.skipTest("directory permissions are not enforced (running as root)")
                self.assertEqual(tr.rollup_dirs(str(parent)), [str(parent / "good")])
            finally:
                (parent / "locked").chmod(0o700)


class AutoWithoutProject(unittest.TestCase):
    def test_errors_and_never_uses_a_dir_named_auto(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "auto").mkdir()  # the old fallback would have rolled this up
            (Path(d) / "auto" / "s.jsonl").write_text("")
            err, old = io.StringIO(), os.getcwd()
            os.chdir(d)
            try:
                with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(Path(d) / "empty")}), \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    code = tr.main(["--rollup", "auto"])
            finally:
                os.chdir(old)
            self.assertEqual(code, tr.ERROR)
            self.assertIn("--rollup auto found no project directory for", err.getvalue())


class WatchdogKeepsAdviseLine(n.Base):
    def test_advise_line_is_published_before_the_receipt_runs(self):
        s = self.transcript(n.firing())
        seen = {}

        def slow_receipt(*a, **k):
            seen["line"] = tr._WATCH.get("line")
            return None

        with mock.patch.dict(tr._WATCH, {"cache": "c", "key": {"k": 1}, "line": ""}), mock.patch.object(tr, "receipt", slow_receipt):
            final = self.line(s)
        self.assertTrue(seen["line"].startswith("spend: [ctx-window] "), seen)
        self.assertEqual(seen["line"], final)

    def test_nothing_is_published_without_an_armed_watchdog(self):
        s = self.transcript(n.firing())
        with mock.patch.dict(tr._WATCH, {}, clear=True):
            self.line(s)
            self.assertNotIn("line", tr._WATCH)

    def test_alarm_caches_the_published_advise_line(self):
        cache = self.dir / "cache.json"
        key = {"k": 1}
        with mock.patch.dict(tr._WATCH, {"cache": str(cache), "key": key, "line": "spend: [x] advise"}), \
                mock.patch.object(tr.os, "_exit", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                tr._on_alarm()
        self.assertEqual(json.loads(cache.read_text()), {"key": key, "line": "spend: [x] advise"})


if __name__ == "__main__":
    unittest.main()
