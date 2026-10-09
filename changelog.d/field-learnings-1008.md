### Added
- `wired_check.py` (agentic-delivery): warns for each new script under `scripts/` that no hook, settings template, CI workflow, command, package.json, Makefile, other script or SKILL.md/reference run line calls (a script referenced only by its own test counts as unwired). Warn-only; wired into the pre-push template and CI.
- `scrub_env.sh` (agentic-delivery): runs a command with every `GIT_*` var plus DB env unset; `train_land.sh` uses it for verify runs, and the lane preamble gains the matching testing rule.

### Fixed
- `ci-gates.sh privacy` now fails closed inside a linked git worktree that lacks `.banlist.local.txt` while the main checkout has it, and prints the exact `cp` command to fix it.

size-budget-raise: .claude/skills/agentic-delivery/SKILL.md 23879→23996 one routing line for wired_check.py
