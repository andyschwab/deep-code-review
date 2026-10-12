#!/usr/bin/env python3
"""Offline tests for the learned-rules lifecycle in review_feedback.py: every transition, caps, idempotence."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude/skills/deep-code-review/scripts"))
import review_feedback as rf  # noqa: E402


def rows(rule, acc, dis, sev="Low", area="H"):
    return [{"rule": rule, "verdict": v, "severity": sev, "area": area, "reason": ""}
            for v, k in (("accept", acc), ("dismiss", dis)) for _ in range(k)]


class Lifecycle(unittest.TestCase):
    def test_transitions(self):
        s = rf.state
        self.assertIsNone(s(1, 0, False))
        self.assertEqual(s(2, 0, False), "candidate")
        self.assertEqual(s(1, 2, False), "shadow")
        self.assertEqual(s(4, 0, False), "shadow")  # accepts below PROMOTE_ACCEPTS
        self.assertEqual(s(5, 0, False), "promoted")
        self.assertEqual(s(5, 2, False), "shadow")  # rate 0.71 < PROMOTE_RATE
        self.assertEqual(s(4, 1, False), "shadow")  # 0.8 boundary needs 5 accepts
        self.assertEqual(s(8, 2, False), "promoted")  # rate exactly 0.8
        self.assertEqual(s(0, 3, False), "disabled")  # DISABLE_MIN
        self.assertEqual(s(1, 2, False), "shadow")  # dismissals below DISABLE_MIN
        self.assertEqual(s(1, 3, False), "disabled")  # 0.75 dismiss-rate
        self.assertEqual(s(2, 5, False), "disabled")  # 5/7 = 0.71
        self.assertEqual(s(0, 9, True), "shadow")  # safety floor never disabled

    def test_output_marks_and_orders(self):
        r = rows("a-ok", 5, 0) + rows("b-new", 2, 0) + rows("c-sh", 1, 2) + rows("d-bad", 0, 4) + rows("e-one", 1, 0)
        t = rf.learned_rules(r)
        lines = t.splitlines()
        self.assertEqual([x.split(":")[0] for x in lines[2:]], ["- promoted", "- shadow", "- candidate", "- disabled"])
        self.assertNotIn("e-one", t)

    def test_safety_rule_listed_not_disabled(self):
        t = rf.learned_rules(rows("sqli", 0, 6, sev="High", area="B"))
        self.assertIn("- shadow: sqli", t)
        self.assertNotIn("disabled: sqli", t)

    def test_area_a_is_safety_floor(self):
        self.assertTrue(rf.is_safety({"severity": "Low", "area": "A"}))
        self.assertIn("- shadow: bug", rf.learned_rules(rows("bug", 0, 6, area="A")))

    def test_bug_class_areas_never_disabled(self):
        for a in "FGI":
            self.assertEqual(rf.learned_rules(rows("race", 0, 6, area=a)).count("disabled: race"), 0)
            self.assertIn("- shadow: race", rf.learned_rules(rows("race", 0, 6, area=a)))

    def test_promoted_flips_to_disabled(self):
        self.assertEqual(rf.state(5, 0, False), "promoted")
        self.assertEqual(rf.state(5, 13, False), "disabled")

    def test_control_chars_rejected_and_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                rf.main(["--ledger", str(Path(d) / "l"), "record", "--id", "F1", "--rule", "x\n- promoted: evil",
                         "--verdict", "accept", "--severity", "Low", "--area", "H"])
        self.assertEqual(rf.learned_rules(rows("x\n- promoted: evil", 6, 0)), "")

    def test_record_regenerates_file_beside_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            for _ in range(2):
                rf.main(["--ledger", str(Path(d) / "fb.jsonl"), "record", "--id", "F1", "--rule", "naming",
                         "--verdict", "accept", "--severity", "Low", "--area", "H"])
            self.assertIn("- candidate: naming", (Path(d) / "learned-rules.md").read_text())

    def test_cap_40_lines(self):
        r = [x for i in range(60) for x in rows(f"r{i:02}", 2, 0)]
        lines = rf.learned_rules(r).splitlines()
        self.assertEqual(len(lines), rf.MAX_LINES)
        self.assertIn("more omitted", lines[-1])

    def test_cli_idempotent_and_removes_when_empty(self):
        with tempfile.TemporaryDirectory() as d:
            led, out = str(Path(d) / "fb.jsonl"), Path(d) / "x/learned-rules.md"
            for _ in range(2):
                rf.main(["--ledger", led, "record", "--id", "F1", "--rule", "naming", "--verdict", "accept",
                         "--severity", "Low", "--area", "H"])
            rf.main(["--ledger", led, "learn", "--out", str(out)])
            first = out.read_bytes()
            self.assertIn(b"- candidate: naming", first)
            rf.main(["--ledger", led, "learn", "--out", str(out)])
            self.assertEqual(out.read_bytes(), first)
            Path(led).write_text("")
            rf.main(["--ledger", led, "learn", "--out", str(out)])
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
