"""deep-code-review SKILL.md is the slim small-DIFF fast path; references/full-map.md holds the full map.

Pins the split contract: SKILL.md stays small, names full-map.md, and sends everything else there; the routing
gate accepts a reference routed only through full-map.md but still requires full-map.md itself to be routed from SKILL.md.
"""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / ".claude/skills/deep-code-review"
GATES = ROOT / "scripts/ci-gates.sh"


def routing(skill_md, refs):
    """Run `ci-gates.sh routing` on a throwaway skill dir; refs maps basename to text. Returns (rc, stderr)."""
    with tempfile.TemporaryDirectory() as t:
        s = pathlib.Path(t) / "s"
        (s / "references").mkdir(parents=True)
        (s / "SKILL.md").write_text(skill_md)
        for name, text in refs.items():
            (s / "references" / name).write_text(text)
        p = subprocess.run(["bash", str(GATES), "routing", str(s)], capture_output=True, text=True)
        return p.returncode, p.stderr


class SlimSkill(unittest.TestCase):
    def test_skill_md_is_the_fast_path(self):
        s = (D / "SKILL.md").read_text()
        body = s.split("\n---\n", 1)[1]
        self.assertLess(len(body.encode()), 4000)
        self.assertIn("300 changed lines", body)
        self.assertIn("references/full-map.md", body)
        self.assertIn("file:line", body)
        self.assertNotIn("JSON array", body)

    def test_fast_path_carries_compact_mode_floor(self):
        body = (D / "SKILL.md").read_text().split("\n---\n", 1)[1]
        for needle in ("at most 8", "confidence 80", "re-reading the cited lines", "name the test",
                       "auth, crypto, payments, data deletion"):
            self.assertIn(needle, body)

    def test_full_map_is_routed_and_self_describing(self):
        first = (D / "references/full-map.md").read_text().split("\n", 1)[0]
        self.assertTrue(first.startswith("Read this when"))
        self.assertIn("full-map.md", (D / "SKILL.md").read_text())

    def test_full_map_keeps_the_map_sections(self):
        m = (D / "references/full-map.md").read_text()
        for h in ("## Operating principles", "## Domain map", "## Severity rubric", "## Definition of done",
                  "| Archetype | Default domains | Must-load refs |", "| Phase | Does | Load |"):
            self.assertIn(h, m)

    def test_routing_accepts_reference_routed_via_full_map(self):
        rc, err = routing("see references/full-map.md\n", {"full-map.md": "Read this when x. `a.md`\n", "a.md": "a\n"})
        self.assertEqual((rc, err), (0, ""))

    def test_routing_rejects_unrouted_reference(self):
        rc, err = routing("see references/full-map.md\n", {"full-map.md": "nothing\n", "a.md": "a\n"})
        self.assertEqual(rc, 1)
        self.assertIn("UNROUTED: references/a.md", err)

    def test_routing_requires_full_map_routed_from_skill_md(self):
        rc, err = routing("no map here\n", {"full-map.md": "`a.md`\n", "a.md": "a\n"})
        self.assertEqual(rc, 1)
        self.assertIn("UNROUTED: references/full-map.md", err)

    def test_routing_rejects_dangling_route_in_full_map(self):
        rc, err = routing("see references/full-map.md\n", {"full-map.md": "references/gone.md\n"})
        self.assertEqual(rc, 1)
        self.assertIn("DANGLING ROUTE: references/gone.md", err)

    def test_review_load_set_models_slim_skill(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import review_load_bytes as r
        s = (D / "SKILL.md").read_text()
        self.assertEqual(r.load_set(s, 300), ("quick", ["SKILL.md"]))
        self.assertEqual(r.load_set(s, 301)[1][:2], ["SKILL.md", "references/full-map.md"])


if __name__ == "__main__":
    unittest.main()
