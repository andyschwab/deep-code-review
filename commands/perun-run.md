---
description: Start an owner-authorised autonomous run that works the task ledger queue item by item until it is drained
argument-hint: <goal>
---

The owner started an autonomous run. Goal: $ARGUMENTS

This run only continues across items if it is self-paced by the host's loop mechanism. A model turn ends when the model returns, so prose alone does not keep a run going.

1. Start dynamic (self-paced) loop mode for the goal above, as if the owner had typed `/loop $ARGUMENTS`. Use the `loop` skill if it is available. If you cannot start a loop from here, print exactly this line for the owner to run, then stop: `/loop $ARGUMENTS`
2. Each tick: run `python3 .claude/skills/agentic-ceo/scripts/task_ledger.py next --check` (or read the project's tracker queue). Exit 3 means drained.
3. Do that one item, then record it (`task_ledger.py done --id T-### --evidence ...`). Then take the next item in the same tick. Never end the run while `next --check` exits 0.
4. A question for the absent owner, or any irreversible, destructive or shared-state action (push, merge, deploy, external send, deletion) with no owner-authored standing grant: `task_ledger.py defer --id T-### --question "<q>" --park`, then continue with the next item. Do not ask and wait.
5. When the only work left is waiting on an event (CI, a build, a peer), schedule the next tick with `ScheduleWakeup` at a fallback delay of 1200-1800 seconds instead of ending the run.
6. Stop only when `next --check` exits 3, or the owner says stop. On stop, report what was done with evidence, then `task_ledger.py questions` as one batch.
