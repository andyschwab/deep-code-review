#!/usr/bin/env python3
"""Offline tests for communication-structure status_update_lint.py (leadership status update shape)."""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINT = os.path.join(ROOT, ".claude/skills/communication-structure/scripts/status_update_lint.py")
sys.path.insert(0, os.path.dirname(LINT))
import status_update_lint as L  # noqa: E402

GOOD = """Bottom line: 2026-10-12 14:30 PT: 20 of 21 requests fixed (was 12, +8).

What moved:
- Requests fixed: 12 → 20 (+8)

What users can now do:
- Export their data from the dashboard (verified-on-production export page).

Health: On track; next milestone completes 2026-10-15.

Slipped: none.

Decision needed: Recommend A (ship now) over B (wait for redesign). Reply A or B.

Detail: https://example.com/project
"""


def problems(text):
    return [p for _, p in L.lint(text)]


class StatusUpdate(unittest.TestCase):
    def test_good_is_clean(self):
        self.assertEqual(L.lint(GOOD), [])

    def test_bottom_line_needs_timestamp_and_number(self):
        self.assertTrue(any("timestamp" in p for p in problems(GOOD.replace("2026-10-12 14:30 PT", "today"))))
        self.assertTrue(any("timestamp" in p for p in problems(GOOD.replace("14:30 PT", "14:30"))))
        bad = GOOD.replace("20 of 21 requests fixed (was 12, +8)", "most requests fixed")
        self.assertTrue(any("number" in p for p in problems(bad)))

    def test_what_moved_needs_before_after(self):
        self.assertTrue(any("What moved" in p for p in problems(GOOD.replace("12 → 20 (+8)", "20 fixed"))))
        self.assertEqual(L.lint(GOOD.replace("12 → 20 (+8)", "12 -> 20 (+8)")), [])

    def test_jargon_effort_promise_before_detail(self):
        for bad in ("Fixed in PR 12", "see #123", "on branch feat/x", "CI is green", "the pipeline ran",
                    "14 commits", "9 tasks done", "saved filters coming next week"):
            self.assertTrue(L.lint(GOOD.replace("Slipped: none.", "Slipped: " + bad)), bad)

    def test_detail_may_hold_jargon_but_must_be_last_with_link(self):
        self.assertEqual(L.lint(GOOD.replace("project", "pull/123 PR #123 CI")), [])
        self.assertTrue(L.lint(GOOD + "Footer line\n"))
        self.assertTrue(L.lint(GOOD.replace("https://example.com/project", "see tracker")))

    def test_decision_needs_recommendation(self):
        self.assertTrue(L.lint(GOOD.replace("Recommend A (ship now) over B (wait for redesign). Reply A or B.", "A or B?")))
        self.assertEqual(L.lint(GOOD.replace("Recommend A (ship now) over B (wait for redesign). Reply A or B.", "none.")), [])

    def test_missing_section_and_unverified_live(self):
        self.assertTrue(any("missing section: health" in p for p in problems(GOOD.replace("Health:", "Mood:"))))
        self.assertTrue(any("verified-on" in p for p in problems(GOOD.replace("(verified-on-production export page)", "is live"))))

    def test_cli_exit_codes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, dir=os.environ.get("TMPDIR")) as f:
            f.write(GOOD)
        try:
            ok = subprocess.run([sys.executable, LINT, "--file", f.name], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            self.assertEqual(subprocess.run([sys.executable, LINT], capture_output=True).returncode, 2)
            self.assertEqual(subprocess.run([sys.executable, LINT, "--file", f.name + ".x"], capture_output=True).returncode, 2)
        finally:
            os.unlink(f.name)


FX = os.path.join(ROOT, "scripts/status-update-fixtures")
EXPECT = {"timestamp": "timestamp", "number": "number", "before-after": "What moved", "jargon": "jargon",
          "effort": "effort count", "promise": "promise", "decision": "Decision", "detail": "Detail",
          "live": "verified-on", "section": "missing section"}


class Fixtures(unittest.TestCase):
    def test_owner_format_passes(self):
        self.assertEqual(L.lint(open(os.path.join(FX, "good.txt"), encoding="utf-8").read()), [])

    def test_each_rule_has_a_failing_fixture(self):
        for rule, want in EXPECT.items():
            text = open(os.path.join(FX, f"red-{rule}.txt"), encoding="utf-8").read()
            self.assertTrue(any(want in p for p in problems(text)), rule)

    def test_natural_variants(self):
        for ts in ("Oct 12 16:20 PT", "12 Oct, 16:20 CEST", "2026-10-12 14:30 UTC"):
            self.assertEqual(L.lint(GOOD.replace("2026-10-12 14:30 PT", ts)), [], ts)
        self.assertEqual(L.lint(GOOD.replace("12 → 20 (+8)", "12 → 20")), [])
        self.assertEqual(L.lint(GOOD.replace("Recommend A (ship now) over B (wait for redesign). Reply A or B.", "Recommendation: A.")), [])


if __name__ == "__main__":
    unittest.main()
