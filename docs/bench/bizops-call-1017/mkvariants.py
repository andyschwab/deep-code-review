"""Build the arm texts for round 5 (the call): v0 = the unedited business-ops SKILL.md at base commit 3d9a30ff; c, d, e = candidate edits.
c and d are round 4's restructure and a+b (text unchanged apart from the shared description line); e is c reworded to the owner decision.
The candidate text is exactly what ships if kept (SKILL.md becomes the arm text, byte for byte)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent.parent / ".claude/skills/business-ops/SKILL.md"
BASE = HERE / "prompts" / "perun_business-ops_v0.txt"  # frozen copy of the base SKILL.md


def sub(t, old, new):
    assert t.count(old) == 1, old[:60]
    return t.replace(old, new)


DISCLAIMER = ("**Standing disclaimer (state it once, up front, every engagement):**",
              "**Standing disclaimer (state it once per engagement, as the closing line of the deliverable, never the opener):**")

LEAD = """## Lead with the call
Open with the answer: the recommendation or verdict on the user's numbers, in one or two
sentences ("take B unless churn passes 4%", "reject as structured"). Then the arithmetic, the
one input that flips the call, and a stop or pivot trigger computed from the user's figures
with a date. Never open with a disclaimer, a refusal or a lane label, and do not print "Lane A"
or "Lane R" headings: the triage is yours, not the reader's. When the user frames options and
asks for a call, choose one; apply-don't-direct bars setting a price or spend out of nothing,
not choosing between options the user put on the table. When an input is missing but the user's
own figures bracket it, compute with a labelled assumption (low, base, high, marked ASSUMED) and
say which real number replaces it; a formula with blank variables is not an answer. When nothing
brackets it (a bare "fill in our CAC"), return the formula and how to obtain the figure instead.

"""

LANE_R_B = """- **Name the regime, explain the general rule, route the binding call.** Identify which body of
  law or regulation applies, then answer the question as far as general knowledge goes: how the
  rule usually works, what companies in the user's position usually do and why, the facts that
  would flip it, and, when the user asks "how much", an illustrative figure on their own numbers
  labelled illustrative. Mark any rate, threshold, deadline or citation you cannot verify
  UNVERIFIED instead of dropping the topic. Route only the binding determination (the filing, the
  amount actually owed, "you are / are not covered", what an instrument legally permits) to a
  licensed professional (lawyer, CPA, tax adviser), with the exact question to bring. Never state
  that verdict yourself. A bare "ask a professional" fails the reader."""

OLD_NAME_REGIME = """- **Name the regime, then route.** Identify which body of law/regulation the
  question falls under and hand it to a licensed professional (lawyer, CPA,
  tax adviser). Do **not** state the conclusion, the amount owed, the filing, or
  the "this is legal" verdict."""


OLD_DESC = """  Use for money and compliance questions on taking a product to market. Lane
  A: pricing, unit economics, LTV/CAC, runway, TAM sizing, applied to YOUR numbers. Lane
  R: legal, tax, securities, fundraising - names the regime, routes to a
  professional. Educational, not advice. Opt-in: --with-business."""
NEW_DESC = """  Use for money and compliance questions on taking a product to market: pricing,
  unit economics, LTV/CAC, runway, TAM sizing, and legal, tax, accounting or
  fundraising questions. Leads with the call on your numbers and labelled
  assumptions; routes only the binding or jurisdiction-specific part to a
  professional. Educational, not advice. Opt-in: --with-business."""
assert len(" ".join(NEW_DESC.split())) <= 400


def cand_a(t):
    t = sub(t, *DISCLAIMER)
    return sub(t, "## The asymmetric boundary (decide the lane first)", LEAD + "## The asymmetric boundary (decide the lane first)")


def cand_b(t):
    t = sub(t, OLD_NAME_REGIME, LANE_R_B)
    t = sub(t, "## Lane R — regulation-dependent (route, never conclude)", "## Lane R — regulation-dependent (explain the rule, route the binding call)")
    t = sub(t, "  something must be classified)? → **Lane R: route.**", "  something must be classified)? → **Lane R: explain the rule, route the binding call.**")
    t = sub(t, '| "Roughly, how much tax will I owe?" | Tax owed is regulation-dependent. Name the regime and route to a CPA; do not estimate the figure. |',
            '| "Roughly, how much tax will I owe?" | Name the regime, give the mechanism and an illustrative figure on your numbers (labelled illustrative, UNVERIFIED); the filing amount is the CPA\'s. |')
    t = sub(t, '| "Are my contractors correctly classified?" | Worker classification is a legal determination → employment counsel; never conclude it here. |',
            '| "Are my contractors correctly classified?" | Explain the usual test and the facts that tip it; the determination is for employment counsel, never concluded here. |')
    return sub(t, "- The lane was decided first; Lane-R questions were routed, never concluded.",
               "- The lane was decided first; Lane-R questions got the general rule, and the binding call was routed, never concluded.")


def cand_d(t):
    """a and b together (added after the tune run of a, b, c; see PREREGISTERED-ADDENDUM-1.md)."""
    return sub(cand_b(cand_a(t)), OLD_DESC, NEW_DESC)


def cand_c(t):
    """Restructure: one memo shape, three tiers by confidence, rules kept as a short never-list."""
    t = sub(t, OLD_DESC, NEW_DESC)
    head, rest = t.split("# Business ops\n", 1)
    _, tail = rest.split("**Design-time triage (front door).", 1)
    mid = MEMO_C
    t = head + "# Business ops\n" + mid + "**Design-time triage (front door)." + tail
    t = sub(t, '| "Roughly, how much tax will I owe?" | Tax owed is regulation-dependent. Name the regime and route to a CPA; do not estimate the figure. |',
            '| "Roughly, how much tax will I owe?" | Tier 2: the mechanism plus an illustrative figure on your numbers (labelled, UNVERIFIED); the filing amount is tier 3, the CPA\'s. |')
    t = sub(t, '| "Are my contractors correctly classified?" | Worker classification is a legal determination → employment counsel; never conclude it here. |',
            '| "Are my contractors correctly classified?" | Explain the usual test and the facts that tip it (tier 2); the determination is tier 3, employment counsel. |')
    t = sub(t, "- The lane was decided first; Lane-R questions were routed, never concluded.",
            "- The memo order held: the call first, then numbers, flip input and trigger, then what to confirm and with whom.")
    t = sub(t, "- Lane-A answers show the formula and every assumption; no input was fabricated;\n  the decision was left to the user (no directive).",
            "- Tier-1 answers show the formula and every assumption; no input was presented as the user's data.")
    t = sub(t, "- The educational-information-not-advice disclaimer is present.", "- The educational-information-not-advice disclaimer is present, as the closing line.")
    for o, n in (("Lane-R", "tier-3"), ("Lane R", "tier 3"), ("Lane-A", "tier-1"), ("Lane A", "tier 1")):
        t = t.replace(o, n)
    return t


def cand_e(t):
    """c reworded to the owner decision: lead with the call; legal, tax and accounting answered on the general rule with labelled
    assumptions and computed figures; a short routing note only for jurisdiction-specific or high-stakes items."""
    t = cand_c(t)
    t = sub(t, "Answer the question asked, on the user's numbers, and say plainly which part only a licensed\nprofessional can settle. Every part of an answer sits in one of three tiers, and the tier sets",
            "Answer the question asked, on the user's numbers. Legal, tax and accounting questions get the\ngeneral rule and the usual practice with labelled assumptions and computed figures, not a referral;\nonly a jurisdiction-specific or high-stakes item gets a short routing note.\nEvery part of an answer sits in one of three tiers, and the tier sets")
    t = sub(t, "(state it once per engagement, as the closing line, never the opener):**",
            "(one short closing sentence, once per engagement; never a banner or opener):**")
    t = sub(t, "4. **What to confirm, and with whom.** Only the tier-3 part: the exact question to bring and\n   what is time-sensitive.",
            "4. **Routing note, only when needed.** One or two lines, and only for a jurisdiction-specific or\n   high-stakes item (a filing, a securities offering, a worker-classification call, a regulated\n   domain): the exact question to bring to the licensed professional and what is time-sensitive.\n   Skip it when the general rule settles the question.")
    return t


MEMO_C = """
Money and compliance questions from a small builder get a decision memo, not a referral.
Answer the question asked, on the user's numbers, and say plainly which part only a licensed
professional can settle. Every part of an answer sits in one of three tiers, and the tier sets
how firmly it is stated. Putting a tier-3 question in tier 1 (answering a securities, tax or
employment-law determination as if it were math) is the failure this skill exists to prevent.

**Standing disclaimer (state it once per engagement, as the closing line, never the opener):**
this is educational information, not legal, tax, accounting, financial, or investment advice.

Persisted artifacts stay normal English. Chat may be terse. Lookup table:
`INDEX.md`; read it instead of opening references blindly.

---

## The memo (every answer, in this order)

1. **The call.** One or two sentences: the recommendation or verdict on the user's numbers
   ("take B unless churn passes 4%", "reject as structured", "five-year straight line, zero
   salvage"). If the user gave options, choose one. If no call is possible, name the one fact
   that blocks it.
2. **The numbers.** Formula, the user's figures, then a labelled assumption for each missing
   input (low, base, high, marked ASSUMED) and the result under each. A formula with blank
   variables is not an answer. When the user gave nothing to bracket an input (a bare "fill in
   our CAC"), return the formula and how to obtain the figure instead.
3. **What flips it, and the trigger.** The one input that changes the call, with its value,
   and a stop or pivot trigger computed from the user's figures with a date. Name decision
   thresholds as rules of thumb the user can replace, never as facts about their market, and end
   with a step doable this week, phrased "if X, consider Y".
4. **What to confirm, and with whom.** Only the tier-3 part: the exact question to bring and
   what is time-sensitive.

Do not print "tier" or "Lane" labels or open with a refusal: the triage is yours, not the
reader's.

## The three tiers (decide per part before writing; when unsure, answer at tier 2 and mark the unverified part)

- **Tier 1, compute.** Pricing structure (value-based, cost-plus, competitor-anchored), unit
  economics (LTV, CAC, LTV:CAC, payback, margin, burn, runway, break-even) and ownership or
  dilution arithmetic on terms the user supplies. Name the pricing method (Van Westendorp
  survey the user runs; usage-, outcome-, per-seat or good-better-best packaging) and apply it
  to the user's willingness to pay. Choosing between options the user put on the table is the
  job; setting a price or spend out of nothing is not.
- **Tier 2, explain and recommend.** How a tax, accounting, legal, regulatory or fundraising
  rule usually works, what companies in the user's position usually do and why, and which facts
  tip it. Name the regime, state the usual treatment as such, and when the user asks "how
  much", give an illustrative figure on their own numbers, labelled illustrative.
- **Tier 3, route.** The binding determination: the filing, the amount actually owed, whether
  a regime binds this company, what an instrument legally permits, how to structure a
  securities offering. Securities (selling equity or SAFEs **is a securities offering**), tax,
  employment classification and privacy compliance (GDPR/CCPA and the like) live here. Hand
  each to the right licensed professional with the exact question to bring, and never state the
  verdict ("you are covered"). Interpreting conversion mechanics (cap, discount, pro-rata, MFN)
  or setting terms is tier 3.

## What you never do
- **Never fabricate the inputs.** CAC, churn, conversion, margin, and any
  competitor price are the user's real numbers, labelled assumptions bracketed by the user's
  own figures, or flagged unknowns with how to obtain them; never invented as the user's
  data, and thin data is labelled thin.
- **Never fabricate** a statute, rate, deadline, threshold, or a jurisdiction's
  rule. An `UNVERIFIED` + "confirm with a professional" beats a plausible wrong
  figure.

"""

if __name__ == "__main__":
    base = BASE.read_text() if BASE.exists() else SKILL.read_text()
    for arm, f in (("v0", lambda t: t), ("c", cand_c), ("d", cand_d), ("e", cand_e)):
        (HERE / "prompts" / f"perun_business-ops_{arm}.txt").write_text(f(base))
        print(arm, len(f(base).encode()))
