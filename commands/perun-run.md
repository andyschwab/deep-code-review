---
description: Start an owner-authorised autonomous run that works the task ledger queue item by item until it is drained
argument-hint: <goal>
---

The owner started an autonomous run. Goal: $ARGUMENTS

Read `unattended-operating-mode.md` section "Why sessions stop after one item, and how to run autonomously" (in the `agentic-delivery` skill's `references/`) and follow it. Summary:

1. Continuation comes from a self-paced loop, not prose. Invoke the `loop` skill with the goal only (no interval token; if the goal starts with one like `5m`, prefix it with `goal:` so it is not read as a fixed interval). If no loop can be started, print `/loop <goal>` for the owner and stop. Host loop and wakeup behaviour is unverified here; if a tick ends with no loop running, say so.
2. Each tick: `python3 <agentic-ceo>/scripts/task_ledger.py next --check`, where `<agentic-ceo>` is the skill directory (`.claude/skills/agentic-ceo` in a script install; under the plugin directory in a plugin install; locate it with `find` if unsure). No script: read the project tracker. Exit 3 = drained.
3. If the owner says stop, stop and go to step 6. Otherwise do one item, record it (`done --id T-### --evidence ...`), take the next in the same tick.
4. Default to park: any question for the owner, and any irreversible, destructive or shared-state action (push, merge, deploy, external send, deletion), is `defer --id T-### --question "<q>" --park`. Proceed with such an action only when the owner's own message granting it is quoted in the ledger row and covers that action.
5. Waiting on an event (CI, build, peer): schedule the next tick with the host's wakeup tool if it has one (about 20-30 minutes). Ceiling: after 24 hours or 100 ticks, park the waiting item and go to step 6.
6. End: report what was done with evidence, then `task_ledger.py questions` as one batch, including blocked rows.
