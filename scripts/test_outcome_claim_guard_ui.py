#!/usr/bin/env python3
"""Tests for the "unseen UI" Stop claim class in outcome_claim_guard.py, replayed against synthetic transcripts.

A transcript is JSONL of assistant tool_use entries (the shape Claude Code writes); only tool names and input
paths/commands matter. Fixtures are generic (Acme, example.com, localhost); nothing real is read.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / ".claude/skills/agentic-delivery/scripts"
sys.path.insert(0, str(SC))
import outcome_claim_guard as ocg  # noqa: E402

CLAIM = "The new reports page now shows at http://localhost:3000/reports."
EDIT = ("Edit", {"file_path": "app/reports/page.tsx"})
SHOT = ("Read", {"file_path": "shots/reports-desktop.png"})
SERVER = ("Bash", {"command": "pnpm dev"})


class UiClaim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ocg-ui-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def transcript(self, *calls):
        path = os.path.join(self.tmp, "t.jsonl")
        with open(path, "w") as f:
            for name, inp in calls:
                f.write(json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "text", "text": "SECRET-BODY"}, {"type": "tool_use", "name": name, "input": inp}]}}) + "\n")
        return path

    def check(self, text, *calls):
        return ocg.ui_violation(text, self.transcript(*calls))

    def test_claim_without_screenshot_is_flagged(self):
        self.assertIn("no screenshot", self.check(CLAIM, EDIT, ("Bash", {"command": "curl -s localhost:3000/reports"}))[1])

    def test_screenshot_after_edit_passes(self):
        self.assertIsNone(self.check(CLAIM, EDIT, SHOT))
        self.assertIsNone(self.check(CLAIM, EDIT, ("mcp__browser__take_screenshot", {})))

    def test_screenshot_before_last_edit_is_flagged(self):
        self.assertIn("older than the last edit", self.check(CLAIM, EDIT, SHOT, EDIT)[1])

    def test_screenshot_before_server_restart_is_stale_server(self):
        self.assertIn("stale server", self.check(CLAIM, EDIT, SHOT, SERVER)[1])
        self.assertIsNone(self.check(CLAIM, EDIT, SERVER, SHOT))

    def test_non_image_read_and_non_ui_edit_do_not_count(self):
        self.assertTrue(self.check(CLAIM, EDIT, ("Read", {"file_path": "app/reports/page.tsx"})))
        self.assertIsNone(self.check("The view layer refactor is done.", ("Edit", {"file_path": "lib/db.py"})))

    def test_hedge_in_the_same_sentence_passes(self):
        self.assertIsNone(self.check("The reports page now shows data, not visually checked.", EDIT))
        self.assertIsNone(self.check("Not visually checked: the reports page shows data.", EDIT))

    def test_hedge_exempts_only_its_own_sentence(self):
        self.assertTrue(self.check("Not visually checked. Desktop page now shows data.", EDIT))
        self.assertIsNone(self.check("Not visually checked. The unit tests pass.", EDIT))

    def test_inline_code_url_is_still_a_claim(self):
        self.assertTrue(self.check("`localhost:3111/x` - it now shows data.", EDIT))
        self.assertIsNone(self.check("```\nthe page now shows data on localhost\n```\nLog above is from last week.", EDIT))

    def test_more_claim_words(self):
        for text in ("localhost:3111/x is up.", "The chart is visible on localhost:3111.", "The page is rendered.",
                     "The dashboard is live.", "The layout works."):
            with self.subTest(text=text):
                self.assertTrue(self.check(text, EDIT))

    def test_ambiguous_nouns_need_a_visual_verb(self):
        self.assertIsNone(self.check("The board loaded 40 PRs.", EDIT))
        self.assertIsNone(self.check("The route works with the new token.", EDIT))
        self.assertTrue(self.check("The board now shows 40 PRs.", EDIT))
        self.assertTrue(self.check("The new route renders.", EDIT))

    def test_any_source_edit_after_the_shot_makes_it_stale(self):
        self.assertIn("older than the last edit", self.check(CLAIM, EDIT, SHOT, ("Write", {"file_path": "lib/data.py"}))[1])
        self.assertIn("older than the last edit",
                      self.check(CLAIM, EDIT, SHOT, ("Bash", {"command": "sed -i '' 's/a/b/' lib/data.py"}))[1])
        self.assertTrue(self.check(CLAIM, EDIT, SHOT, ("Bash", {"command": "perl -pi -e 's/a/b/' lib/data.py"})))
        self.assertIsNone(self.check(CLAIM, EDIT, SHOT, ("Edit", {"file_path": "docs/notes.md"})))

    def test_more_server_restarts_make_the_shot_stale(self):
        for cmd in ("make dev", "docker compose up -d", "turbo run dev", "bun dev", "rails s", "python3 -m http.server 8000"):
            with self.subTest(cmd=cmd):
                self.assertIn("stale server", self.check(CLAIM, EDIT, SHOT, ("Bash", {"command": cmd}))[1])
        self.assertIsNone(self.check(CLAIM, EDIT, ("Bash", {"command": "git commit -m 'make it so'"}), SHOT))

    def test_lint_and_build_commands_are_not_restarts(self):
        for cmd in ("make lint", "turbo run lint", "docker compose build", "make test", "vite build", "npx vite build"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.check(CLAIM, EDIT, SHOT, ("Bash", {"command": cmd})))

    def test_a_screenshot_path_is_not_a_capture(self):
        for cmd in ("ls shots/screenshot-1.png", "cat docs/screenshot.md", "cp screenshot.png /tmp/x.png"):
            with self.subTest(cmd=cmd):
                self.assertTrue(self.check(CLAIM, EDIT, ("Bash", {"command": cmd})))
        self.assertIsNone(self.check(CLAIM, EDIT, ("Bash", {"command": "node -e \"page.screenshot({path:'a.png'})\""})))

    def test_set_up_and_ui_compounds_are_not_claims(self):
        self.assertIsNone(self.check("I set up the page routing.", EDIT))
        self.assertIsNone(self.check("The UI-claim guard is ready.", EDIT))
        self.assertIsNone(self.check("The ui-kit is done.", EDIT))
        self.assertTrue(self.check("The UI is ready.", EDIT))
        self.assertTrue(self.check("The dashboard is up.", EDIT))

    def test_bash_and_action_screenshots_count(self):
        for call in (("Bash", {"command": "npx playwright screenshot http://localhost:3000 out.png"}),
                     ("Bash", {"command": "screencapture -x out.png"}),
                     ("Bash", {"command": "chrome --headless --screenshot=out.png http://localhost:3000"}),
                     ("mcp__computer__use", {"action": "screenshot"})):
            with self.subTest(call=call):
                self.assertIsNone(self.check(CLAIM, EDIT, call))

    def test_only_the_transcript_tail_is_read(self):
        path = self.transcript(EDIT)
        with open(path, "a") as f:
            f.write("x" * (ocg.TAIL + 10) + "\n")
        self.assertIsNone(ocg.ui_violation("The settings page is done.", path), "an edit outside the tail is not seen")

    def test_non_claims_pass(self):
        for text in ("Is the page ready?", "The page is not ready yet.", "The page would show it once data lands.",
                     "Tests pass and the lint is clean."):
            with self.subTest(text=text):
                self.assertIsNone(self.check(text, EDIT))

    def test_no_ui_work_in_transcript_only_localhost_claims_count(self):
        self.assertIsNone(self.check("The settings page is done.", ("Read", {"file_path": "README.md"})))
        self.assertTrue(self.check(CLAIM, ("Read", {"file_path": "README.md"})))

    def test_bad_transcript_fails_open(self):
        missing = os.path.join(self.tmp, "missing.jsonl")
        with self.assertRaises(OSError):
            ocg.ui_violation(CLAIM, missing)
        self.assertIsNone(ocg.ui_violation(CLAIM, None))
        stdin = json.dumps({"hook_event_name": "Stop", "last_assistant_message": CLAIM, "transcript_path": missing})
        p = subprocess.run([sys.executable, str(SC / "outcome_claim_guard.py")], input=stdin, capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_warn_notes_and_nudges_block_blocks_once(self):
        t = self.transcript(EDIT)
        with mock.patch.dict(os.environ, {"PERUN_OUTCOME_DIR": self.tmp}):
            ev = {"hook_event_name": "Stop", "last_assistant_message": CLAIM, "transcript_path": t, "session_id": "s1"}
            self.assertIn("Unseen UI claim", ocg.handle(ev, "warn", ())["systemMessage"])
            nudge = ocg.handle({"hook_event_name": "UserPromptSubmit", "session_id": "s1"}, "warn", ())
            self.assertIn("UI check", nudge["hookSpecificOutput"]["additionalContext"])
            self.assertEqual(ocg.handle(ev, "block", ())["decision"], "block")
            self.assertIsNone(ocg.handle(ev | {"stop_hook_active": True}, "block", ()))
            self.assertIsNone(ocg.handle(ev, "off", ()))


if __name__ == "__main__":
    unittest.main()
