Auto-update now opens a `perun/update-v<ver>` PR so the Perun copy committed on the default branch catches up (policy `auto_update_pr`, default on; never auto-merged, user checkout untouched); `session_brief.py` and `operating_selfcheck.py` warn when the committed copy is behind the installed one.

size-budget-raise: .claude/skills/agentic-delivery/references/host-enforcement.md 39256→40627 documents the auto-update PR step and committed-copy WARN
