#!/usr/bin/env python3
"""Full DIFF method carries the 80-point confidence floor, and merge_findings reads only the numeric field."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SK = ROOT / ".claude/skills/deep-code-review"
sys.path.insert(0, str(SK / "scripts"))
import merge_findings as m  # noqa: E402


class ConfidenceFloorFull(unittest.TestCase):
    def test_method_rule(self):
        t = (SK / "references/method.md").read_text()
        self.assertIn("a gap finding scored below 80", t)
        self.assertIn("Report only ≥80", t)
        self.assertIn("declined: <reason>", t)

    def test_machine_report_field(self):
        t = (SK / "references/machine-report.md").read_text()
        self.assertIn("`confidence_score`", t)

    def test_quick_path_batches_reads(self):
        self.assertIn("batch all reads in one turn", (SK / "references/full-map.md").read_text())

    def test_string_tier_not_a_score(self):
        # a string tier must not collide with the numeric score; only confidence_score gates
        row = {"id": "a", "severity": "High", "title": "t", "evidence": ["x.py:1"], "confidence": "PLAUSIBLE"}
        self.assertEqual(m.merge([dict(row)], root=".")["dropped"]["low_confidence"], 0)
        self.assertEqual(m.merge([dict(row, confidence_score=25)], root=".")["dropped"]["low_confidence"], 1)


if __name__ == "__main__":
    unittest.main()
