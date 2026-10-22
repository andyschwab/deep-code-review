#!/usr/bin/env python3
"""agentic-ceo session start must not load agentic-delivery's INDEX.md (~16.6 KB, ~4.1K tokens).

Contract: ceo SKILL.md says a routing/table match skips INDEX.md, never sends the reader to
agentic-delivery's INDEX.md first, and that Task to entry table the delivery SKILL carries still
names every first-hop route ceo relies on. Offline.
"""
import re
import unittest
from pathlib import Path

S = Path(__file__).resolve().parent.parent / ".claude/skills"
CEO = (S / "agentic-ceo/SKILL.md").read_text()
DEL = (S / "agentic-delivery/SKILL.md").read_text()


class CeoStartLoad(unittest.TestCase):
    def test_match_skips_index(self):
        self.assertRegex(CEO, r"a match skips `INDEX\.md`")

    def test_no_unconditional_delivery_index_read(self):
        self.assertNotRegex(CEO, r"Read `INDEX\.md` first")
        self.assertNotIn("(delivery references: `agentic-delivery`'s `INDEX.md`)", CEO)

    def test_delivery_table_carries_the_skip_rule_and_routes(self):
        self.assertIn("a match skips `INDEX.md`", DEL)
        for route in ("merge_train.py", "gate-epistemology.md", "worktree-isolation.md", "operating-discipline.md"):
            self.assertIn(route, DEL.split("## When to Use")[0])


if __name__ == "__main__":
    unittest.main()
