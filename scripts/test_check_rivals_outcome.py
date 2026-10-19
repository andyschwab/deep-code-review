#!/usr/bin/env python3
"""Tests for scripts/check_rivals_outcome.py: every rival row needs an outcome-metric audit row. Offline."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_rivals_outcome as c  # noqa: E402

DOC = Path(__file__).resolve().parent.parent / "docs/perun-vs-rivals.md"
TOP = "| Skill | Rival | Bench dir | Verdict |\n|---|---|---|---|\n| alpha | R | `bench-a` | x |\n| beta | R | `bench-b1`, `bench-b2` | y |\n\n"
HEAD = "| Section | Metric | Type | Outcome measured | Missing |\n|---|---|---|---|---|\n"
ROWS = "| alpha `bench-a` | pref | Proxy | None | key |\n| beta `bench-b1`, `bench-b2` | pref | Outcome | Measured: merged | cost |\n"


class Check(unittest.TestCase):
    def test_committed_doc_passes(self):
        self.assertEqual(c.check(DOC.read_text()), [])

    def test_ok(self):
        self.assertEqual(c.check(TOP + HEAD + ROWS), [])

    def test_row_without_audit_row_fails(self):
        out = c.check(TOP + HEAD + ROWS.splitlines(True)[0])
        self.assertEqual(out, ["row has no outcome-metric audit row: beta bench-b1",
                               "row has no outcome-metric audit row: beta bench-b2"])

    def test_same_skill_other_bench_needs_own_row(self):
        top = TOP.replace("\n\n", "\n| alpha | R | `bench-a2` | z |\n\n")
        self.assertIn("alpha bench-a2", "\n".join(c.check(top + HEAD + ROWS)))

    def test_proxy_cannot_claim_measurement(self):
        out = c.check(TOP + HEAD + ROWS.replace("Proxy | None", "Proxy | Measured: x"))
        self.assertIn("Proxy row must start", out[0])

    def test_outcome_needs_measured(self):
        out = c.check(TOP + HEAD + ROWS.replace("Measured: merged", "None"))
        self.assertIn("must start its outcome cell with `Measured:`", out[0])

    def test_empty_cell_and_bad_type_fail(self):
        self.assertEqual(len(c.check(TOP + HEAD + ROWS.replace("Proxy | None", "Proxy | "))), 1)
        self.assertEqual(len(c.check(TOP + HEAD + ROWS.replace("Proxy", "Guess"))), 1)

    def test_every_listed_dir_needs_audit(self):
        out = c.check(TOP + HEAD + ROWS.replace(", `bench-b2`", ""))
        self.assertEqual(out, ["row has no outcome-metric audit row: beta bench-b2"])

    def test_dir_match_is_exact(self):
        top = TOP.replace("`bench-a`", "`bench-a`, `bench`")
        self.assertIn("alpha bench", "\n".join(c.check(top + HEAD + ROWS)))

    def test_empty_first_table_fails(self):
        out = c.check("| Skill | Rival | Bench dir | Verdict |\n|---|---|---|---|\n\n" + HEAD + ROWS)
        self.assertIn("has no rows", out[0])

    def test_bare_measured_and_short_row_fail(self):
        self.assertEqual(len(c.check(TOP + HEAD + ROWS.replace("Measured: merged", "Measured:"))), 1)
        self.assertIn("too few cells", c.check(TOP + HEAD + ROWS + "| gamma | pref |\n")[0])

    def test_missing_table_fails_closed(self):
        self.assertIn("missing table", c.check(TOP)[0])
        self.assertIn("missing table", c.check("no tables here")[0])


if __name__ == "__main__":
    unittest.main()
