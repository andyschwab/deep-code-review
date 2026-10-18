"""Rebuild prompts/candidates/C1..C3.md from frozen/growth-analytics.v0.md (shared de-duplication plus one added passage each)."""
from pathlib import Path
B = Path(__file__).resolve().parent
v0 = (B / "frozen/growth-analytics.v0.md").read_text()


def rep(t, a, b):
    assert t.count(a) == 1, a[:50]
    return t.replace(a, b)


# shared de-duplication: Definition-of-done bullets that restate a method step or the Prime directive, removed to stay inside the size budget
T = v0
T = rep(T, "- The funnel is read bottom-up (retention before acquisition).\n", "")
T = rep(T, "- Every proposed event names the question it answers; nothing instrumented \"just\n  in case\".\n", "")
T = rep(T, "- No benchmark, threshold, or metric value is asserted that the user's data did\n  not supply; unknowns are `UNVERIFIED` and routed to the user's analytics.\n", "")

S7_OLD = ("Leave a decision they reserved for someone else to them, use data they already\nhave before proposing new tracking, and add an identifier or no-benchmark note only if the request touches one.")
C1_NEW = ("Obey each limit they state (no recommendation, no tooling advice, a team size or hours,\nexisting data only): add no metric, tool, call or tracking outside it, leave a decision reserved for\n"
          "someone else to them, and say what data they already have answers before proposing new tracking.\nAdd an identifier or no-benchmark note only if the request touches one.")
S8_TAIL = "A list of cuts with no reading rule is not an answer."
C2_ADD = ("Spell out the build: exact event and property names, session-timeout and de-duplication rules,\nhow accidental or duplicate actions are filtered, one reconciliation check that proves the data is\n"
          "right, and a dated schedule that lands before the stated deadline. ")
C3_ADD = ("Apply the stated numbers: show the arithmetic (the net per-visitor or per-unit effect, the\nbreak-even and the gap to it) and a table of result, action and what to tell the named audience, before any\n"
          "general framework. ")


def build(c1=0, c2=0, c3=0):
    t = rep(T, S7_OLD, C1_NEW) if c1 else T
    return rep(t, S8_TAIL, (C2_ADD if c2 else "") + (C3_ADD if c3 else "") + S8_TAIL) if c2 or c3 else t


out = {"C1": build(c1=1), "C2": build(c2=1), "C3": build(c3=1)}
for k, t in out.items():
    (B / "prompts/candidates" / f"{k}.md").write_text(t)
    print(k, len(t.encode()))
