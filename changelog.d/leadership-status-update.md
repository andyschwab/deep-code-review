### Added
- communication-structure: default seven-part leadership status update (bottom line with timestamp and number, what moved as before → after, verified-live user abilities, health, slipped, A/B decision, one detail link) in `references/leadership-status-update.md`, with `scripts/status_update_lint.py` (reuses `status_vocab_lint`), tests and an eval case. agentic-delivery `work-tracking.md` now links to it and posts per milestone instead of weekly.


### Changed
- communication-structure: `status_update_lint.py` accepts natural variants (any date-form timestamp with zone, `X → Y` with optional delta, `Recommended: A`, file-path Detail, "nothing new is live yet"); "merge" is no longer jargon, SHAs are. Adds owner-format regression fixtures and one failing fixture per rule.

size-budget-raise: .claude/skills/communication-structure/SKILL.md 7661→7890 leadership status update pointer
size-budget-raise: .claude/skills/agentic-delivery/references/work-tracking.md 3585→3687 link to leadership status structure
