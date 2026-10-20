#!/usr/bin/env python3
"""Tests for two token_report.py review nits: `--apply` prints the .bak path when it creates one, and unreadable
settings do not mute any lever (isset fails closed, so muting would hide every lever)."""
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
import test_cost_advice as ca  # noqa: E402

line = ca.line


class UnreadableSettings(unittest.TestCase):
    setUp, settings, advise = ca.Advise.setUp, ca.Advise.settings, ca.Advise.advise
    ROWS = [line(i, ctx=c) for i, c in enumerate([100_000, 450_000])]

    def test_unreadable_file_mutes_only_levers_set_elsewhere(self):
        self.settings("{broken", "settings.local.json")
        out = self.advise(self.ROWS)
        self.assertEqual(out["muted"], [])
        self.assertTrue(any("some levers may already be set" in n for n in out["notes"]))
        self.settings({"autoCompactWindow": 200000})
        self.assertEqual(self.advise(self.ROWS)["muted"], ["compact"])


class ApplyBackupPath(unittest.TestCase):
    def test_bak_path_printed_once(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            sess, target = d / "s.jsonl", d / "settings.json"
            sess.write_text(json.dumps(line(0, ctx=100_000)) + "\n")
            target.write_text("{}")
            plan = {"bashOutputMaxChars": 10_000}
            advice = {"fix_plan": plan, "notes": [], "muted": []}

            def run():
                out = io.StringIO()
                with mock.patch.object(tr, "advise", return_value=advice), \
                        mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(d / "h")}), \
                        contextlib.redirect_stdout(out):
                    tr.main(["--session", str(sess), "--apply", str(target)])
                return out.getvalue()
            self.assertIn(f"backup {target.resolve()}.bak", run())
            target.write_text("{}")  # key absent again, .bak already exists
            self.assertNotIn("backup ", run())


if __name__ == "__main__":
    unittest.main()
