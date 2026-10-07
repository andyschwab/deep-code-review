### Added
- `agentic-delivery/scripts/queue_guard.py`: single priority queue. Given `gh issue list --json` output and `PRIORITIES.md`, it prints the next issue to pull (ranked items first, then remaining P0s oldest first) and flags P0 inflation (more than N unranked P0s) instead of relabeling; tag the rest `p0:unranked`. Read-only, fails closed on bad input, `--selftest` wired into CI. Routed from `agentic-delivery/SKILL.md`.
- size-budget-raise: .claude/skills/agentic-delivery/SKILL.md 23261→23477 one routing bullet for queue_guard.py
