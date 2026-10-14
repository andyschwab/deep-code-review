### Added
- `partition_diff.py` splits a large unified diff into deterministic whole-file review chunks (packed to a changed-line budget, optional per-hunk split, binary/lockfile/generated files listed in `skipped`, never dropped) so any agent or orchestrator can fan out a review.

### Changed
- `method-situational.md` records the measured large-diff recipe (one pass finds about a third of known bugs; repeated or chunked passes raise it) and routes `partition_diff.py`; README reports the same numbers.
size-budget-raise: .claude/skills/deep-code-review/references/method-situational.md 39581→40813 measured large-diff recipe
