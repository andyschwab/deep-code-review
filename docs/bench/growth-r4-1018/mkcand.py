"""Rebuild prompts/candidates/C1..C3.md from frozen/growth-analytics.v0.md (shared de-duplication plus one or two added passages)."""
from pathlib import Path
B = Path(__file__).resolve().parent
v0 = (B / "frozen/growth-analytics.v0.md").read_text()


def rep(t, a, b):
    assert t.count(a) == 1, a[:50]
    return t.replace(a, b)


# shared de-duplication: restated rules removed to stay inside the size budget
T = v0
T = rep(T, "- When the request involves per-user ids, the identifier seam and PII routing are stated, not restated from\n  `observability.md` / `privacy-compliance.md`.\n", "")
T = rep(T, "| \"Estimate our conversion so the deck is done.\" | An un-instrumented metric is UNVERIFIED. Name what to instrument; do not invent the value. |\n", "")
T = rep(T, "| \"Use the raw user id for cohorts.\" | Cohorts need a *stable* id, but keep it pseudonymous; route PII/consent to `privacy-compliance.md`. |\n", "")
T = rep(T, "- **Not** a source of market benchmarks, and not the user's analytics tool. It\n  designs *what to measure and how to read it*; the figures live in the user's\n  analytics.", "- **Not** a source of market benchmarks or the user's analytics tool: it designs\n  *what to measure and how to read it*; the figures live in their analytics.")

S7_OLD = ("Produce the artifact the requester named (the event list, the plan, the summary\nfor their director, the choice between the options they gave) in the format and\n"
          "for the audience stated, before any caveat. The rules above shape it; they never\nreplace it with a refusal, a smaller list or a lecture. Pick among the\n"
          "requester's own options instead of inventing a third, leave a decision they\nreserved for someone else to them, use data they already have before proposing\n"
          "new tracking, and add an identifier or no-benchmark note only if the request\ntouches one.\n")
S7_BASE = ("Produce the artifact the requester named (the event list, the plan, the summary for their\ndirector, a pick among the options they gave) in the format and for the audience stated,\n"
           "before any caveat. The rules shape it; they never replace it with a refusal, a smaller list\nor a lecture. Leave a decision they reserved for someone else to them, use data they already\n"
           "have before proposing new tracking")
S7_END_OLD = ", and add an identifier or no-benchmark note only if the request touches one.\n"
C1_ADD = (". Build on the metric, target or constraint they stated (their volume target, their retention\nwindow, a regulator, \"no tooling advice\") instead of swapping in your own North Star; add an\n"
          "identifier, benchmark, tripwire, UNVERIFIED or statistics note only when the decision turns\non it, in one line.\n")
C2_ADD = ("Make it runnable: name events with properties, formulas, thresholds, sample sizes and dates\ncomputed from the stated figures (the quarterly volume, days to reach N at their traffic, the\n"
          "break-even rate), and fit the call to the stated deadline and constraint (a short canary, a\npartial rollout) rather than a bare \"wait\" or \"re-run\". If the data is contaminated, say what\n"
          "can still be salvaged. ")
S8_TAIL = "A list of cuts with no reading rule is not an answer."


def build(c1, c2):
    t = rep(T, S7_OLD, S7_BASE + (C1_ADD if c1 else S7_END_OLD))
    if c2:
        t = rep(t, S8_TAIL, C2_ADD + S8_TAIL)
    return t


out = {"C1": build(1, 0), "C2": build(0, 1), "C3": build(1, 1)}
for k, t in out.items():
    (B / "prompts/candidates" / f"{k}.md").write_text(t)
    print(k, len(t.encode()))
