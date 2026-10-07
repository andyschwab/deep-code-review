---
description: Report what this session spent and what would have been cheaper
argument-hint: "[transcript path, optional]"
disable-model-invocation: true
---
Run a cost retro of this session. Read, do not restate, the doctrine in `deep-code-review`'s
`model-tiering.md` (sections "Route delivery lanes by work type and stage" and "Did the tiering
work? — cost accounting") and `agentic-delivery`'s `operating-discipline.md`.

1. Measure: if `agentic-ceo`'s `scripts/token_report.py` is available, run it with `--session`
   set to $ARGUMENTS (or this session's transcript); otherwise use the usage the host reports.
   Mark anything you cannot price `UNPRICED`; never estimate it as zero.
2. Report spend by lane and model tier, and the main-agent versus subagent split.
3. For each costly item, name the cheaper route the doctrine gives (tier, effort, caching, fewer
   or longer-lived lanes, a hand-back cap) and the quality check that still has to hold.

Lead with the one change that would save the most. Say what you could not confirm.
