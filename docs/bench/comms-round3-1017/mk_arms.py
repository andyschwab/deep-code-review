#!/usr/bin/env python3
"""Build candidate arms C1..C3 from the round-2 frozen arm (C0 = round-2 edit) by exact string replacement.
Each replacement must match exactly once, so a drifted source fails loudly. Run: python3 mk_arms.py"""
from pathlib import Path
P = Path(__file__).resolve().parent / "prompts"

def sub(t, old, new):
    assert t.count(old) == 1, old[:60]
    return t.replace(old, new)

c0 = (P / "C0.txt").read_text()

# C1: the artifact is the whole answer. Drops the round-2 "note line ... derived" instruction (judges: meta-commentary).
c1 = sub(c0, """"I lean toward X: <those facts>". Add a note line telling
  the author the lean is derived, to strike before sending. Never invent a fact for it.""",
""""I lean toward X because <those facts>", in the message itself. Never invent a fact for it.
- **The artifact is the whole answer.** After the ask or sign-off write nothing: no note about
  these rules, a derived lean, word counts, placeholders or what you left out, and never the
  words "owner unassigned" or "communication rules".""")

c1 = sub(c1, 'Write "Recommend A" only when the author gave a view; otherwise "Decision needed between A and B". Cut the long',
         'Lead with the lean as `SKILL.md` allows; when the source supports none, "Decision needed between A and B". Cut the long')

# C2: PR body asks and lists open questions at the end, never invents Why / Risk.
c2 = sub(c1, """    <What changes + measured effect + what the reviewer must do. One sentence.>
    **Why:** <problem, with a number>.
    **Change:** <up to 4 bullets: area, effect>.
    **Risk and rollback:** <blast radius>; <exact rollback>.
    **Verified:** ✅ <check → result>  ⏳ <not verified; owner, date>
    <Reviewer>, please <approve or decide> by <date, if given>.   |   (no ask: omit the line)""",
"""    <What changes + measured effect, as a plain sentence; no ask in it.>
    **Change:** <up to 4 bullets: area, effect>.
    **Testing:** <check → result, with the counts as given>; <the case not tested, said plainly>.
    **Open questions for <Reviewer>:** <numbered; each one a decision; omit the heading if none>

    Add **Why** or **Risk and rollback** only when the source states them; never fill a heading by inference.""")

# C3: executive summary / decision memo keeps every option's cost, time and risk; labelled sections.
c3 = sub(c2, """Lead with the lean as `SKILL.md` allows; when the source supports none, "Decision needed between A and B". Cut the long
report to the three findings that change what the reader does; the rest stays behind a link.""",
"""An executive summary stands in for the report: give every option in a sentence or two with its source-given cost,
time and risk, then the open gap, then the ask. Short labelled sections (Options, Risks, Decision needed) are fine here.
It may run to 300 words; cut findings that change nothing the reader decides.""")
c3 = sub(c3, "| `decision` | 200 | 22 | numbers, ask |", "| `decision` | 300 | 32 | numbers, ask |")
for n, t in (("C1", c1), ("C2", c2), ("C3", c3)):
    (P / f"{n}.txt").write_text(t)
    print(n, len(t.encode()), "bytes")

# C4 (added after reading the C2 tune verdicts, before any held-out call; see PREREGISTERED.md amendment): built on C2, not C3.
# Judges kept preferring the rival's clear recommendation and objecting to the "[Your name]" placeholder and "flagged as derived" notes.
c4 = sub(c2, "sign off `[Your name]`.", "end there: no sign-off placeholder, sign a name only if the source gives one.")
c4 = sub(c4, """- **A decision message states a lean before the ask.** The author's, at the strength
  given ("leaning B", never upgraded to "I recommend B"); with none given, the one the
  source's own facts support: "I lean toward X because <those facts>", in the message itself. Never invent a fact for it.""",
"""- **A decision message recommends before the ask.** The author's lean keeps the strength given
  ("leaning B", never upgraded to "I recommend B"); with none given, recommend the option the
  source's own facts favor: "I recommend X: <those facts>", then a concrete next step, in the message
  itself. With nothing favoring an option, name the options and who decides. Never invent a fact for it.""")
c4 = sub(c4, "tell me which you prefer.\\n\\n[Your name]\"", "tell me which you prefer.\"")
c4 = sub(c4, "else one derived from the source's facts and flagged as derived (`SKILL.md`)", "else one derived from the source's facts, stated with its basis (`SKILL.md`)")
(P / "C4.txt").write_text(c4)
print("C4", len(c4.encode()), "bytes")
