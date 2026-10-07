### Added
- DIFF reviews gain a context-gathering step (PR intent, callers, file history), four explicit blind-spot passes (performance, cross-module, third-party dependency behavior, low-salience defects), and a rule that PR text is untrusted and the reviewer runs least-privilege (`method-situational.md`).
- Findings are short and edit-first, nits are capped at about 5, and every security finding carries a concrete attack scenario (`report-format.md`). Four new evals cover these.

size-budget-raise: .claude/skills/deep-code-review/references/method-situational.md 33020→36871 new DIFF context, blind-spot and untrusted-PR-text depth, off the must-load floor
size-budget-raise: .claude/skills/deep-code-review/references/report-format.md 20944→21763 edit-first finding format, nit cap, security attack-scenario rule
