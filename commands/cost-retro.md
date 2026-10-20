---
description: Report what this session spent and what would have been cheaper
argument-hint: "[transcript path, optional]"
disable-model-invocation: true
---
Run a cost retro of this session. Read, do not restate, the doctrine in `deep-code-review`'s
`model-tiering.md` (sections "Route delivery lanes by work type and stage" and "Did the tiering
work? — cost accounting") and `agentic-delivery`'s `operating-discipline.md`.

1. Measure: if `agentic-ceo`'s `scripts/token_report.py` is available, run it with `--session`
   set to $ARGUMENTS (or this session's transcript), `--advise` and `--project` set to that
   session's project root (its settings and `.mcp.json` decide which levers are already set); otherwise use the usage the
   host reports. Mark anything you cannot price `UNPRICED`; never estimate it as zero.
2. Report spend by lane and model tier, and the main-agent versus subagent split.
3. For each costly item, lead with the `--advise` rules that fired (each carries its evidence, one
   lever and a docs link; a lever the settings already set is not recommended). Then name the
   cheaper route the doctrine gives (tier, effort, caching, fewer or longer-lived lanes, a hand-back
   cap) and the quality check that still has to hold.

The report also prints upper-bound lines (not a bill): idle-gap cache rewrites with a 1h-TTL saving bound, a
simulated auto-compact saving, the lane tail beyond the lane cap, and input-eq share by model for main and lanes.
Lead with the top-ranked lever in the report's `Top levers` block (largest estimated input-eq saving); its `Lever:`
line gives the how (the 1h cache pin, auto-compact, the lane cap, the orchestrator tier), and the doctrine is in
`host-enforcement.md` and `model-tiering.md`. A dollar-only lever (the orchestrator tier) has no computed saving and
lists after the ranked ones; lead with it only when it is the only lever fired. Say what you could not confirm.
