### Added
- Merge train: new browser-gate failures are re-run alone up to 3 times (`train_flake.sh`); only failures that fail at least 2 of 3 are real, flakes are reported separately, and only PRs that fail the real ids alone on the base are dropped so the rest still land.
- Merge train: the gate holds an exclusive machine-wide heavy lease (`perun_policy.py heavy-exclusive`); `heavy_gate.py` denies other heavy commands with "gate running: wait". Pushes go through one serial queue.
- Merge train: waits use a `_lock.sh` mkdir lock (stale only when older than the timeout and the pid is dead; otherwise reported, never deleted), no process-name matching.

size-budget-raise: .claude/skills/agentic-delivery/references/merge-queue-worktrees.md 66147→67174 documents the three train-resilience behaviors with their env contract, which no existing section holds
