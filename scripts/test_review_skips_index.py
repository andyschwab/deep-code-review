#!/usr/bin/env python3
"""A deep-code-review run must not load its INDEX.md (~21.8 KB, ~5.4K tokens by chars/4) when SKILL.md routes the work.

Contract: SKILL.md says a routing match skips INDEX.md and still carries the archetype map, phase table and
read-when triggers that route without it; the load counter drops INDEX.md from the full-method set exactly when that
marker is present. Mirrors scripts/test_ceo_start_load.py. Offline.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import review_load_bytes as r  # noqa: E402

D = ROOT / ".claude/skills/deep-code-review"
SKILL = (D / "SKILL.md").read_text()


class ReviewSkipsIndex(unittest.TestCase):
    def test_skill_says_match_skips_index(self):
        self.assertIn(r.SKIP, SKILL)
        self.assertNotIn("Lookup table: `INDEX.md`; read it", SKILL)

    def test_skill_still_routes_without_index(self):
        for route in ("Archetype → load map", "`method.md`", "`compact-mode.md`", "`domain-checklists.md`", "`security-appsec.md`"):
            self.assertIn(route, SKILL)

    def test_index_only_scripts_stay_routed(self):
        shell = (D / "references/lang-shell.md").read_text()
        for script in ("gate_cache.py", "gate_map.py"):
            self.assertIn(script, shell)

    def test_full_method_load_drops_index_only_with_marker(self):
        self.assertEqual(r.load_set(SKILL, 301), ("full", ["SKILL.md", "references/method.md"]))
        self.assertEqual(r.load_set("no marker", 301)[1], ["SKILL.md", "INDEX.md", "references/method.md"])

    def test_shipped_load_sets_exclude_index(self):
        for n in (10, 300, 301, 5000):
            self.assertNotIn("INDEX.md", r.load_set(SKILL, n)[1])


if __name__ == "__main__":
    unittest.main()
