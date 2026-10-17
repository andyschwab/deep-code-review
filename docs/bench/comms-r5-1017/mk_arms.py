#!/usr/bin/env python3
"""Build the arm system prompts from the skill text at the bench base commit (docs/bench/comms-r5-1017, see PREREGISTERED.md).
V0 = unedited SKILL.md; E1..E3 = V0 plus one decision-brief mode wording each, by exact replacement. Refuses to overwrite."""
import subprocess
from pathlib import Path

D = Path(__file__).resolve().parent
BASE = subprocess.run(["git", "-C", str(D), "show", "3d9a30ff:.claude/skills/communication-structure/SKILL.md"], capture_output=True, text=True, check=True).stdout
OLD_TIME = "- **Under 30 seconds.** ~150 words by default; the budgets in the reference\n  are the ceilings. Longer needs a reason per block, or a cut.\n"
NEW_TIME = ("- **Under 30 seconds.** ~150 words by default; the budgets in the reference\n  are the ceilings. Longer needs a reason per block, or a cut. The one exception is a\n"
            "  decision brief (below).\n")
OLD_LEAN = "with no view given, name the\n  options and who decides."
NEW_LEAN = "with no view given, name the\n  options and who decides (a decision brief, below, may derive a lean from the stated facts)."
HEAD = "## Decision brief (a message that asks its reader to decide)\n\n"
E1 = HEAD + (
    "A message that asks its reader to pick or approve between options is a brief, not a digest;\n"
    "a status message with no decision stays the ~150-word digest. A brief runs about 250 to 350\n"
    "words and keeps every fact that changes the decision. Line 1: the ask with the recommendation\n"
    "and the reason that decides it. Then the situation in two lines; each option with its cost, time,\n"
    "risk and unknowns exactly as the source gives them; the recommendation and its rationale drawn\n"
    "from those facts; the next step if approved; the ask last, to the reader, with owner and date if\n"
    "given. The author's own lean stays at its stated strength; with none given, derive one from the\n"
    "stated facts and mark it \"derived from <fact>\", or name who decides. Never invent a number,\n"
    "date or owner.\n\n")
E2 = HEAD + (
    "A message that asks its reader to pick or approve between options is a brief, not a digest;\n"
    "a status message with no decision stays the ~150-word digest. A brief runs about 250 to 350\n"
    "words. Fixed skeleton, every line from the source only:\n\n"
    "    **Decision needed: <ask>, by <date if given>. Recommend <option>: <the reason that decides it>.**\n"
    "    Situation: <two lines: what is true now and what forces the choice>\n"
    "    - Option A: cost <x>, time <y>, risk <z>, upside\n"
    "    - Option B: cost, time, risk, upside\n"
    "    Recommendation: <option>, because <rationale from the stated facts>.\n"
    "    Not known: <gaps that could change the answer>\n"
    "    If approved: <the one next step, owner and date if given>.\n\n"
    "The author's own lean stays at its stated strength; with none given, derive one from the stated\n"
    "facts and mark it \"derived from <fact>\", or name who decides. Drop a field the source cannot\n"
    "fill; never invent a number, date or owner.\n\n")
EX = ("\n**Decision brief.**\n"
      "Before: \"Need Priya to pick: rebuild the importer (6 weeks, 2 engineers) or patch it (1 week, breaks again at\n"
      "50k rows). Customer demo is Nov 12. Not sure the patch survives the demo data. Priya decides by Friday; a patch would start Monday.\"\n"
      "After: \"**Priya, please pick rebuild or patch by Friday. Recommend patch: it is the only option\n"
      "ready before the Nov 12 demo (derived from 1 week vs 6).** Situation: the importer fails above 50k\n"
      "rows and the demo is Nov 12. Rebuild: 6 weeks, 2 engineers, no row limit. Patch: 1 week, fails again\n"
      "at 50k rows. Not known: whether the demo data stays under 50k. If approved: start the patch Monday.\"\n"
      )
E3 = E1.rstrip("\n") + "\n" + EX + "\n"
arms = {"V0": BASE}
for name, sec in (("E1", E1), ("E2", E2), ("E3", E3)):
    t = BASE.replace(OLD_TIME, NEW_TIME).replace(OLD_LEAN, NEW_LEAN)
    assert t != BASE and t.count(NEW_TIME) == 1 and t.count(NEW_LEAN) == 1
    marker = "## Deliverables, not just messages"
    assert t.count(marker) == 1
    arms[name] = t.replace(marker, sec + marker)
for k, v in arms.items():
    p = D / "prompts" / f"{k}.txt"
    assert not p.exists(), f"{p} exists: never overwrite"
    p.write_text(v)
    print(k, len(v.split()), "words")
