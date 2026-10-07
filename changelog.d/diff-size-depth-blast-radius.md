### Added

- DIFF depth in `method-situational.md`, routed from `method.md`: size bands with mandatory chunking by file cluster and a per-file ledger (no "done" while a changed file is unopened), a blast-radius trace that opens shared-state callees (counters, quotas, caches, queues, auth) outside the diff and checks keying and filters across tenants and surfaces, and a state-transition completeness and literal-vs-constant drift check. Three synthetic eval cases and two verified sources in `docs/standards-index.md`.
- size-budget-raise: .claude/skills/deep-code-review/references/method-situational.md 28534→33020 DIFF size-band, blast-radius and transition-completeness depth, kept in the conditional ref outside the must-load floor
