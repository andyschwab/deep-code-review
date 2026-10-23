"""Prose-contract checks for the small-diff fast path, guard severity, and in-use lens."""
import pathlib
import re
import unittest

R = pathlib.Path(__file__).resolve().parent.parent / ".claude/skills"
D = R / "deep-code-review"


def txt(p):
    return (R / p).read_text()


class FastPath(unittest.TestCase):
    def test_quick_path_routes_compact_mode_only(self):
        s = txt("deep-code-review/references/full-map.md")
        m = re.search(r"\*\*DIFF quick-path\*\*.*?(?=\n\n)", s, re.S)
        self.assertIsNotNone(m)
        self.assertIn("≤300", m.group(0))
        self.assertIn("compact-mode.md", m.group(0))
        self.assertTrue((D / "references/compact-mode.md").exists())

    def test_lane_preamble_keeps_build_lanes_off_review_refs(self):
        self.assertIn("do not load `deep-code-review` references", txt("agentic-delivery/templates/lane-preamble.md"))

    def test_guard_severity_rule(self):
        self.assertIn("scores as high as the invariant it guards", txt("deep-code-review/references/report-format.md"))

    def test_in_use_lens_lists_all_holders(self):
        s = txt("deep-code-review/references/concurrency-shared-state.md")
        i = s.index('"In use" is not just cwd')
        seg = s[i:i + 500]
        for w in ("cwd", "executable path", "script file descriptor", "memory-mapped", "locks"):
            self.assertIn(w, seg)


if __name__ == "__main__":
    unittest.main()
