#!/usr/bin/env python3
"""Build round-4 candidates from the round-3 frozen C1 (copied to prompts/C1.txt) by exact string replacement.
Each replacement must match exactly once, so a drifted source fails loudly. Run: python3 mk_arms.py
S = C1 plus the round-3 C4 fixes (no sign-off placeholder, a stated recommendation, derived lean with its basis); it is the shared
prefix of A, B, C so the three candidates differ only in the structural lever. A: decision-brief section skeleton. B: coverage
invariant (every fact that changes a decision survives) with no word cap. C: full-length worked examples per artifact kind."""
from pathlib import Path
P = Path(__file__).resolve().parent / "prompts"

def sub(t, old, new):
    assert t.count(old) == 1, old[:70]
    return t.replace(old, new)

s = (P / "C1.txt").read_text()
s = sub(s, "sign off `[Your name]`.", "end there: no sign-off placeholder, sign a name only if the source gives one.")
s = sub(s, """- **A decision message states a lean before the ask.** The author's, at the strength
  given ("leaning B", never upgraded to "I recommend B"); with none given, the one the
  source's own facts support: "I lean toward X because <those facts>", in the message itself. Never invent a fact for it.""",
"""- **A decision message recommends before the ask.** The author's lean keeps the strength given
  ("leaning B", never upgraded to "I recommend B"); with none given, recommend the option the
  source's own facts favor: "I recommend X: <those facts>", then a concrete next step, in the message
  itself. With nothing favoring an option, name the options and who decides. Never invent a fact for it.""")
s = sub(s, "tell me which you prefer.\\n\\n[Your name]\"", "tell me which you prefer.\"")
s = sub(s, "else one derived from the source's facts and flagged as derived (`SKILL.md`)", "else one derived from the source's facts, stated with its basis (`SKILL.md`)")
(P / "S.txt").write_text(s)

UNDER = """- **Under 30 seconds.** ~150 words by default; the budgets in the reference
  are the ceilings. Longer needs a reason per block, or a cut."""
CUTREPORT = """Lead with the lean as `SKILL.md` allows; when the source supports none, "Decision needed between A and B". Cut the long
report to the three findings that change what the reader does; the rest stays behind a link."""
ROWS = [("| `status` | 150 | 14 |", "| `status` | 250 | 24 |"), ("| `pr` | 200 | 28 |", "| `pr` | 300 | 40 |"), ("| `decision` | 200 | 22 |", "| `decision` | 350 | 36 |")]

def budgets(t):
    for old, new in ROWS:
        t = sub(t, old, new)
    return t

# A: decision-brief skeleton (shape lever). Decision and PR templates become labelled sections; length follows the decision.
a = sub(s, UNDER, """- **Length follows the decision.** A status, decision or PR text gives the reader everything needed to
  act without writing back: every option with its source-given cost, time and risk, the open unknown, the
  recommendation and the ask. That is usually 200 to 350 words; the table budgets are lint ceilings, not
  targets. A tracker comment or release note stays short.""")
a = sub(a, """    **<Conclusion or recommendation>. <The number that carries it>.**
    - <Finding or option A, with its number: cost, time, count>
    - <Finding or option B, with its number>
    - Not known: <the gap that could change the answer>
    <Reader>, please <decide or approve X> by <date, if given>.   |   (no ask: omit the line)""",
"""    **<Conclusion>. <The number that carries it>.**
    **Where it stands:** <2 to 3 sentences: outcome, numbers, dates from the source>
    **Options:**
    1. <Option A>: <what it is>. Cost <x>; time <y>; risk <z>.
    2. <Option B>: <same fields>.
    **Not known:** <the gap that could change the answer>
    **Recommendation:** <X, with the source facts that favor it>; next step <concrete action>.
    <Reader>, please <decide or approve X> by <date, if given>.   |   (no ask: omit the line)""")
a = sub(a, CUTREPORT, """Every option keeps its source-given cost, time and risk; a field the source lacks is left out, never filled.
A long report is cut to the findings that change the decision, never to fewer options.""")
a = sub(a, """    <What changes + measured effect + what the reviewer must do. One sentence.>
    **Why:** <problem, with a number>.
    **Change:** <up to 4 bullets: area, effect>.
    **Risk and rollback:** <blast radius>; <exact rollback>.
    **Verified:** ✅ <check → result>  ⏳ <not verified; owner, date>
    <Reviewer>, please <approve or decide> by <date, if given>.   |   (no ask: omit the line)""",
"""    <What changes + measured effect + what the reviewer must do. One sentence.>
    **Changes:** <bullets: area, effect, number>
    **Testing:** ✅ <check → result, counts as given>  ⏳ <what is not tested and why it matters>
    **Open question for <Reviewer>:** <the decision, each option with its cost>; <recommendation and basis>
    Add **Why** or **Risk and rollback** only when the source states them.""")
a = budgets(a)

# B: coverage invariant (content lever). No word target; nothing that changes a decision may be dropped.
b = sub(s, UNDER, """- **Every fact that changes a decision survives.** Before you send, list the source's numbers, dates,
  options (each with its cost, time and risk) and unknowns. Each one is in the draft, or you can say why
  it changes no decision. A shorter draft that drops one has failed; brevity is never the goal. The table
  budgets are lint ceilings, not targets.""")
b = sub(b, "3. Every paragraph after the first changes what the reader does, or it's cut.", "3. Every paragraph after the first changes what the reader does, or it's cut; every source fact that does change it is present.")
b = sub(b, CUTREPORT, """Cut a long report only to what changes the decision; every option keeps its source-given cost, time and risk.""")
b = budgets(b)

# C: worked examples (exemplar lever). Three full-length After texts, one per artifact kind, replace the length bullet.
EX = """## Worked examples (full length; match this completeness)

**Status email to a named person.** Source: 1,900 lanes; 62% moved, target 80% by Oct 31; the label API throttles at
40 requests per second; Ravi (CFO) must choose: pay Northwind $18k for burst capacity (fixes it by Oct 24), accept a slip to
Nov 14 (free), or move only the top 500 lanes by Oct 31 (partial, about 3 days of engineering); unknown whether the
throttle is per key or per IP.

    Subject: Carrier migration at 62% vs 80% target for Oct 31; need your pick on the label-API throttle

    Ravi,

    The carrier migration is at 62% of our 1,900 lanes against an 80% target for Oct 31. The blocker is the
    label API, which throttles us at 40 requests per second.

    There are three ways to close the gap. Paying Northwind $18k for burst capacity fixes the throttle by Oct 24 and
    keeps the target. Accepting the slip costs nothing but moves the target to Nov 14. Moving only the top 500 lanes
    by Oct 31 takes about 3 days of engineering and gives partial coverage; the throttle stays.

    We do not know yet whether the limit is per API key or per IP, and the answer could change which option is cheapest.

    I recommend the burst capacity: it is the only option that keeps Oct 31, for $18k against a free two-week slip.
    Please tell me which option you want.

**PR body.** Source: invoice sync moves from cron to a queue consumer; 14 files, +412/-198; 126 tests pass, 0 fail; load test
of 5,000 invoices, p95 4.1 s to 0.9 s; retries (3, with backoff) now live in the consumer; not tested: month-end rollover in
the Eastern time zone; reviewer Wen; open question: delete the old cron job here or in a follow-up.

    Invoice sync now runs from a queue instead of cron: p95 for 5,000 invoices drops from 4.1 s to 0.9 s.

    **Changes:** the queue consumer replaces the cron entry point (14 files, +412/-198); retries (3, with backoff) move
    from the cron wrapper into the consumer.
    **Testing:** ✅ 126 passed, 0 failed; ✅ load test, 5,000 invoices, p95 4.1 s to 0.9 s. ⏳ Not tested: month-end rollover
    in the Eastern time zone.
    **Open question for Wen:** delete the old cron job in this PR or in a follow-up? I lean toward the follow-up, because
    the rollover case is untested.

**Executive summary.** Source: a report on a data-warehouse migration; options, with the report's figures: migrate now
($240k, 10 weeks, risk of a 2-day reporting freeze); wait for the vendor's Q1 release ($0 now, 16 weeks, current warehouse
stays at 91% capacity); partial migration of finance data only ($90k, 5 weeks, two systems to maintain); unknown: whether
the vendor's Q1 date holds; the reader, the CFO, decides.

    **Migrate now: $240k over 10 weeks, with a 2-day reporting freeze as the main risk.**
    **Where it stands:** the current warehouse is at 91% capacity.
    **Options:**
    1. Migrate now: $240k, 10 weeks; risk of a 2-day reporting freeze.
    2. Wait for the vendor's Q1 release: $0 now, 16 weeks; the warehouse stays at 91% capacity meanwhile.
    3. Migrate finance data only: $90k, 5 weeks; two systems to maintain.
    **Not known:** whether the vendor's Q1 date holds.
    **Recommendation:** option 1; it is the only one that ends the capacity risk within 10 weeks.
    Please approve option 1, or tell me which you prefer.

"""
c = sub(s, UNDER, """- **Match the worked examples.** Their length and completeness are the standard for the same kind: every
  option, number and unknown the source gives is present. A longer draft needs a reason per block.""")
c = sub(c, "## Before → After", EX + "## Before → After")
c = budgets(c)
for n, t in (("A", a), ("B", b), ("C", c)):
    (P / f"{n}.txt").write_text(t)
    print(n, len(t.encode()), "bytes")
