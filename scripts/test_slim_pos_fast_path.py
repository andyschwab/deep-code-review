"""product-output-safety SKILL.md is the slim fast path; references/full-map.md holds the full method.

Pins the split contract: SKILL.md stays at or under 6000 bytes, routes every reference with a trigger, carries the
hard rules a single output-safety pass needs, and no rule sentence of the pre-slim SKILL.md is lost.
"""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / ".claude/skills/product-output-safety"
OLD_REF = "caee19738f6e4565ef3b7af7ad9d60e35df1c665"  # origin/main just before this split


def flat(text):
    return " ".join(text.split())


SKILL = flat((D / "SKILL.md").read_text(encoding="utf-8"))
MAP = flat((D / "references/full-map.md").read_text(encoding="utf-8"))

# The quick path must carry these without loading full-map.md.
QUICK = [
    "An empty inventory is not a pass", "Do not declare a system \"safe\", \"unbiased\", \"fair\" or \"compliant\"",
    "the ship decision is the owner's", "full autonomous execution of it is the failure", "The floor never relaxes",
    "never an invented \"0% bias\"", "`UNVERIFIED`", "One test row per harm", "owner-set pass threshold",
    "stop condition", "goes to counsel", "never assert that one binds and never encode a date or version",
    "never a bare \"87%\"", "defined coarse tier", "model / data card", "A bare \"do not ship\" never answers the ask",
    "`references/full-map.md`:", "`evals/evals.json`:",
]


class SlimPos(unittest.TestCase):
    def test_skill_is_small(self):
        self.assertLessEqual((D / "SKILL.md").stat().st_size, 6000)

    def test_frontmatter_unchanged_and_single_h1(self):
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_REF}:.claude/skills/product-output-safety/SKILL.md"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest("pre-slim commit not in this clone")
        fm = lambda t: re.match(r"(?s)---\n.*?\n---\n", t).group(0)
        self.assertEqual(fm((D / "SKILL.md").read_text(encoding="utf-8")), fm(r.stdout))
        for rel in ("SKILL.md", "references/full-map.md"):
            self.assertEqual(len(re.findall(r"(?m)^# ", (D / rel).read_text(encoding="utf-8"))), 1, rel)

    def test_every_reference_and_script_is_routed_with_a_trigger(self):
        for ref in sorted((D / "references").glob("*.md")):
            self.assertIn(f"`references/{ref.name}`:", SKILL, f"{ref.name} not routed with a trigger from SKILL.md")
        for s in sorted((D / "scripts").glob("*.*")) if (D / "scripts").is_dir() else []:
            self.assertIn(f"`scripts/{s.name}`", SKILL, f"{s.name} not routed from SKILL.md")

    def test_quick_path_carries_its_contract(self):
        for p in QUICK:
            self.assertIn(p, SKILL, f"quick path missing: {p}")

    def test_old_body_moved_verbatim(self):
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_REF}:.claude/skills/product-output-safety/SKILL.md"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest("pre-slim commit not in this clone")
        body = re.sub(r"(?s)^---.*?\n---\n\s*# Product output safety\n", "", r.stdout)
        self.assertIn(flat(body), MAP, "old SKILL.md body is not carried verbatim in full-map.md")

    def test_every_pre_slim_hard_rule_is_pinned_to_the_fast_path(self):
        # (old rule phrase, which must survive verbatim in full-map.md) -> (its fast-path form, which must be in SKILL.md itself)
        pairs = [
            ("An\nempty inventory is not a pass", "An empty inventory is not a pass"),
            ("**Never certify.**", "**Never certify.**"),
            ("the **ship decision is the owner's**", "the ship decision is the owner's"),
            ("full autonomous execution of such an action is the\n  failure, not the feature", "full autonomous execution of it is the failure"),
            ("**floor never relaxes**", "The floor never relaxes"),
            ("never an invented \"0% bias\"", "never an invented \"0% bias\""),
            ("No invented harm metric, incident\n  rate, benchmark, or regulatory threshold", "No invented incident rate, benchmark or regulatory threshold"),
            ("one test row per inventoried harm", "One test row per harm"),
            ("zero tolerance for failures of a gated irreversible action and never invent a \"typical\" rate", "zero tolerance only for a gated irreversible action; never invent a \"typical\" rate"),
            ("prompt injection via retrieved or\n  user-supplied content, leakage of other users' or private data, and excess agency", "prompt injection, leakage of other users' data and excess agency"),
            ("**route to counsel**", "goes to counsel"),
            ("Never assert the duty here", "never assert that one binds"),
            ("encode **no\n  dates or version numbers**", "never encode a date or version"),
            ("never a bare \"87%\"", "never a bare \"87%\""),
            ("A bare \"do not ship\" never answers the ask", "A bare \"do not ship\" never answers the ask"),
            ("a card stating an **unmeasured** metric", "a card stating an unmeasured metric"),
            ("composition, provenance, consent/licensing, known gaps", "data composition, provenance and consent"),
            ("owner + model version", "owner and model version"),
            ("out-of-scope uses", "out-of-scope uses"),
            ("A one-person team still writes the owner down", "Name an owner for each shipped output-harm"),
        ]
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_REF}:.claude/skills/product-output-safety/SKILL.md"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest("pre-slim commit not in this clone")
        for old, new in pairs:
            self.assertIn(old, r.stdout, f"stale pair, not in the pre-slim SKILL.md: {old}")
            self.assertIn(flat(old), MAP, f"rule not carried in full-map.md: {old}")
            self.assertIn(new, SKILL, f"fast path lost the rule: {new}")


if __name__ == "__main__":
    unittest.main()
