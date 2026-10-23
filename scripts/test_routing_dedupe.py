#!/usr/bin/env python3
"""Routing-only text that a full deep-code-review loads must live in one home (SKILL.md), and the load must not creep back.

Pins: the A-W domain->file table is not restated in domain-checklists.md while SKILL.md's Domain map still routes
every domain-<letter>.md; branch-and-merge-hygiene.md and method-situational.md do not restate routers; the
language table stays (the Shell trigger has no other home); the measured real load stays under its ceiling. Offline.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import review_load_bytes as r  # noqa: E402

D = ROOT / ".claude/skills/deep-code-review"
SKILL = (D / "references/full-map.md").read_text()  # the Domain map lives in the map behind the slim SKILL.md
REF = D / "references"
REAL_BYTES_CEILING = 235400  # REAL_FULL bytes after the routing dedupe (was 237750); raise only with a stated reason


class RoutingDedupe(unittest.TestCase):
    def test_real_load_stays_under_ceiling(self):
        b = sum(len((D / f).read_bytes()) for f in r.REAL_FULL)
        self.assertLessEqual(b, REAL_BYTES_CEILING, f"real full-DIFF load grew to {b} bytes ({b // 4} tokens est)")

    def test_domain_table_has_one_home(self):
        text = (REF / "domain-checklists.md").read_text()
        self.assertNotIn("| Domain | Checklist |", text)
        self.assertIn("Domain map", text)
        for f in sorted(REF.glob("domain-[a-z].md")):
            self.assertIn(f"`{f.name}`", SKILL, f"{f.name} not routed from SKILL.md's Domain map")
            self.assertNotIn(f"`{f.name}`", text)

    def test_hygiene_pointer_sections_gone_checks_kept(self):
        text = (REF / "branch-and-merge-hygiene.md").read_text()
        self.assertNotIn("## Cross-references", text)
        self.assertIn("docs/standards-index.md", text)
        for kept in ("## 7 — Severity discipline", "rotation, not deletion (§6)", "detached-HEAD fast-forward"):
            self.assertIn(kept, text)

    def test_method_situational_trigger_has_router_and_unique_clause(self):
        line3 = (REF / "method-situational.md").read_text().splitlines()[2]
        self.assertTrue(line3.startswith("Read this when `method.md` routes here"))
        self.assertIn("file split", line3)  # the size-ratchet trigger has no router elsewhere
        method = (REF / "method.md").read_text()
        self.assertIn("Situational Phase 1 checks", method)
        self.assertIn("Perceived-absent or", method)

    def test_language_table_kept_for_shell_trigger(self):
        text = (REF / "language-stack-redflags.md").read_text()
        self.assertTrue(re.search(r"^\| Shell .*CI \(`run:`\).*\| `lang-shell.md` \|$", text, re.M))


class RealLoadReported(unittest.TestCase):
    def test_full_route_reports_real_load(self):
        self.assertIn("references/domain-checklists.md", r.REAL_FULL)
        self.assertNotIn("INDEX.md", r.REAL_FULL)
        for f in r.REAL_FULL:
            self.assertTrue((D / f).is_file(), f)


if __name__ == "__main__":
    unittest.main()
