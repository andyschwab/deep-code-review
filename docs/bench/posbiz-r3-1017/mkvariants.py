"""Build the arm texts: v0 = the unedited SKILL.md at the base commit; a, b, c = v0 plus the candidate snippets below.
The snippets are the exact text that ships if a candidate is kept (the SKILL.md edit is this insertion, nothing else)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent

POS_A = """## Deliver the call, not a menu
When the user asks you to choose a segment, a message or a recommendation, **commit**: one
segment, one lead message, and one line on why, using the user's own numbers. Give a
ready-to-use statement and headline, and answer each named alternative in turn (what the
buyer gives up by leaving it, and the line that wins against it). Say "hypothesis" once, in
one line, not as a hedge on every sentence. Keep caveats to the riskiest assumption and the
test that would prove it wrong. Raise trademark, legal or market-size routing only when the
user asks or the draft makes that kind of claim.

"""
POS_B = """## Check the user's numbers first
Before drafting, check the user's figures against each other (a count that does not sum,
units times price against stated revenue, a share that is not the stated share). Name any
mismatch in the first lines, say which figure you used, and build no claim on the suspect
one. Give each failure mode and the stop metric a threshold computed from the user's own
figures and a date by which to read it.

"""
BIZ_DISCLAIMER = ("**Standing disclaimer (state it once, up front, every engagement):**",
                  "**Standing disclaimer (state it once per engagement, as one closing line after the deliverable):**")
BIZ_A = """- **Commit when asked to choose between the user's own options.** If the user frames options
  (raise or hold, tier A or B, take the deal or decline) and asks for a call, make it on their
  numbers: "take B unless X", the input that flips it, and the concrete terms, clauses or pilot
  size to ask for. Apply-don't-direct bars *setting* a price or spend from nothing; it does not
  bar choosing between options the user put on the table. Where stated churn and the revenue
  trend disagree, compute the effective rate from the trend and say which you used; recompute
  any cost the user's own figures imply (one-time versus recurring, sunk versus marginal).
"""
BIZ_B = """- **Route with substance, not a bare referral.** Beyond naming the regime, say the condition
  that would make it apply to the user's stated facts ("applies if you handle EU residents'
  health data"), the practical obligations it usually brings, which milestone should trigger
  hiring counsel and roughly what the first call should cover, and the questions to bring. Still
  never conclude "you are" or "you are not" covered, and never state a rate, deadline or
  threshold you cannot verify.
"""
POS_ANCHOR = "## The method (on the user's own inputs)"
BIZ_ANCHOR_A = "- **End Lane A with a decision aid, not bare math.**"
BIZ_ANCHOR_B = "- **Fundraising is the boundary crossing.**"


def build(skill, v0):
    if skill == "positioning":
        ins = lambda t, *s: t.replace(POS_ANCHOR, "".join(s) + POS_ANCHOR, 1)
        return {"a": ins(v0, POS_A), "b": ins(v0, POS_B), "c": ins(v0, POS_A, POS_B)}
    a = v0.replace(BIZ_DISCLAIMER[0], BIZ_DISCLAIMER[1], 1).replace(BIZ_ANCHOR_A, BIZ_A + "\n" + BIZ_ANCHOR_A, 1)
    b = v0.replace(BIZ_ANCHOR_B, BIZ_B + BIZ_ANCHOR_B, 1)
    c = a.replace(BIZ_ANCHOR_B, BIZ_B + BIZ_ANCHOR_B, 1)
    return {"a": a, "b": b, "c": c}


def main():
    for skill in ("positioning", "business-ops"):
        v0p = HERE / "prompts" / f"perun_{skill}_v0.txt"
        if not v0p.exists():
            v0p.write_text((ROOT / ".claude/skills" / skill / "SKILL.md").read_text())
        v0 = v0p.read_text()
        for arm, t in build(skill, v0).items():
            assert t != v0 and len(t) > len(v0), (skill, arm)
            (HERE / "prompts" / f"perun_{skill}_{arm}.txt").write_text(t)
            print(skill, arm, len(t) - len(v0), "bytes added")
