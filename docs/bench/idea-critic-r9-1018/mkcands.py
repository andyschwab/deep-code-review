#!/usr/bin/env python3
"""Write the round-9 prompts from prompts/perun_idea-critic_v0.txt (a byte copy of .claude/skills/idea-critic/SKILL.md at the round's start).
c9a edits step 5 only, c9b edits step 6 only, c9c applies both. Each replacement must match exactly once."""
from pathlib import Path

P = Path(__file__).resolve().parent / "prompts"
v0 = (P / "perun_idea-critic_v0.txt").read_text()
S5 = ("   or is marked `assumed` plus the check that would settle it. Recompute the\n"
      "   requester's own figures and dates (totals, timelines) before relying on them.\n")
N5 = ("   or is marked `assumed` plus the check that would settle it. Recompute the\n"
      "   requester's own figures and dates before relying on them: totals, units x\n"
      "   duration against the time or capacity available, ROI and payback, calendar.\n"
      "   Open the answer with each mismatch and its corrected number, and size the\n"
      "   call from the corrected figures.\n")
S6 = ("6. **Close with ONE decision** (go, no-go or go-if: never a menu), its **kill\n"
      "   criteria** (observable tripwire, date, action when it fires), the\n"
      "   **leading metric** to watch and a review date.\n")
N6 = ("6. **Close with ONE decision** (go, no-go or go-if: never a menu). If the plan\n"
      "   commits real money, make it a capped, time-boxed first step and name the\n"
      "   cap. **Kill criteria**: one observable metric with a numeric threshold (the\n"
      "   requester's own when given and sound), a date inside that first window, and\n"
      "   the named pivot or stop action when it fires; then the **leading metric**\n"
      "   to watch and a review date.\n")
for s in (S5, S6):
    assert v0.count(s) == 1, s
for arm, t in (("c9a", v0.replace(S5, N5)), ("c9b", v0.replace(S6, N6)), ("c9c", v0.replace(S5, N5).replace(S6, N6))):
    (P / f"perun_idea-critic_{arm}.txt").write_text(t)
    print(arm, len(t.encode()) - len(v0.encode()), "bytes vs v0")
