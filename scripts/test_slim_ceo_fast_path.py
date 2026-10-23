"""agentic-ceo SKILL.md is the slim fast path; references/full-map.md holds the full previous body.

Pins the split contract: SKILL.md stays at or under 7500 bytes, routes every reference and script with a trigger,
carries the hard rules and routing phrases a session start needs, maps cited section names to full-map.md, and the eval-measured behaviors, and no
MUST/never rule sentence of the pre-slim SKILL.md is lost from full-map.md.
"""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / ".claude/skills/agentic-ceo"
OLD_REF = "bc8762619b78d5773b17f0d487494accf24040a8"  # origin/main just before this split
RULE = re.compile(r"\b(never|must|illegal|do not|cannot|is a lie|is rejected|also rejected)\b", re.I)


def flat(text):
    return " ".join(text.split())


SKILL = flat((D / "SKILL.md").read_text(encoding="utf-8"))
MAP = flat((D / "references/full-map.md").read_text(encoding="utf-8"))

# Hard rules, as phrased in SKILL.md itself (asserted against SKILL.md alone, so full-map.md cannot satisfy them).
PINNED = [
    "never re-implements a specialist skill", "never claim a reference loaded or a command run", "never \"it depends\"",
    "no swarm", "After two equivalent failures on a lane, change approach", "never fabricate it", "never relaxes the floor",
    "**Never a second list**", "never a second source", "Owner-gated actions never self-authorize",
    "do not hand-do a specialist's delivery", "An OPEN owner priority outranks all other dispatch",
    "never downgrade a reviewer's model without an eval showing no quality loss",
    # eval-measured behaviors: ledger defer/park/questions/away/reconcile, orchestration share, chaos moves, fidelity, landings
    "`reconcile` catches a dropped ask", "`--default`", "`--park`", "zero pings while away", "`questions` is the owner's batch",
    "`away` the numbered paste-ready one", "answer it first, then append the batch once", "`answer` + `unblock`",
    "Orchestration share over 20% means hand off to a fresh session", "batch 3-5 related tasks per lane",
    "scripts/token_report.py --budget", "six moves", "name ONE next action as an A/B", "Never \"calm down\"",
    "Report backlog closed / total outstanding above lane, merge or gate counts", "one line per material landing",
]

# The fast path must carry these without loading full-map.md.
QUICK = [
    "a match skips `INDEX.md`", "Should we even do this?", "About to ask the owner", "before you draft",
    "report, plan, or summary", "status update", "Starting a session with more than one step",
    "never fabricate it", "`Figures:`", "halt trigger", "fallback trigger", "Never a second list",
    "Split a multi-ask message into one `add --ask` per ask", "answer `--same T-###` or `--new`",
    "exit 1 = open asks exist, informational", ".claude/handoff.md", "never self-authorize", "unverified-depth",
    "one agent wearing several skill-hats",
]


class SlimCeo(unittest.TestCase):
    def test_skill_is_small(self):
        self.assertLessEqual((D / "SKILL.md").stat().st_size, 7500)

    def test_every_reference_and_script_is_routed_with_a_trigger(self):
        for ref in sorted((D / "references").glob("*.md")):
            self.assertIn(f"`references/{ref.name}`:", SKILL, f"{ref.name} not routed with a trigger from SKILL.md")
        for s in sorted((D / "scripts").glob("*.py")):
            self.assertIn(f"scripts/{s.name}", SKILL, f"{s.name} not routed from SKILL.md")

    def test_registry_names_every_sibling_skill(self):
        for name in ("deep-code-review", "agentic-delivery", "idea-critic", "product-discovery", "communication-structure",
                     "growth-analytics", "positioning", "business-ops", "product-output-safety", "contribution"):
            self.assertIn(f"| `{name}` |", SKILL)

    def test_cited_section_names_map_to_full_map(self):
        for sec in ("Size effort to the project", "Stay strategic", "Output discipline", "Definition of done", "Verification"):
            self.assertIn(sec, SKILL)
            self.assertIn(f"## {sec}", MAP)
        self.assertEqual((D / "references/full-map.md").read_text(encoding="utf-8").count("\n# "), 1)

    def test_pinned_hard_rules_survive(self):
        for p in PINNED:
            self.assertIn(p, SKILL, f"hard rule missing from SKILL.md: {p}")

    def test_fast_path_carries_its_contract(self):
        for p in QUICK:
            self.assertIn(p, SKILL, f"fast path missing: {p}")

    def test_every_rule_sentence_of_pre_slim_skill_survives(self):
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_REF}:.claude/skills/agentic-ceo/SKILL.md"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest("pre-slim commit not in this clone")
        old = re.sub(r"(?s)^---.*?\n---\n", "", r.stdout)
        lost = []
        for para in re.split(r"\n\s*\n", old):
            if para.lstrip().startswith(("```", "|", "Validate:")):
                continue
            for s in re.split(r"(?<=[.;:])\s+", flat(para)):
                if RULE.search(s) and s not in MAP:
                    lost.append(s)
        self.assertEqual(lost, [], "rule sentences not carried verbatim in full-map.md")


if __name__ == "__main__":
    unittest.main()
