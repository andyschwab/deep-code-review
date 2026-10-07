### Added
- `REVIEW.md` team config (paths, severity floor, nit cap, plain-language rules with optional regex lead-finders, stage override) read in Phase 0 with documented precedence: the safety floor (security, secrets, data loss, privacy, tenancy) is never relaxed, and on a DIFF review the file is read from the base ref. New `references/review-config.md`, routed from `SKILL.md` and `machine-report.md`.
- `scripts/review_feedback.py`: repo-local accept/dismiss ledger, per-rule accept-rate telemetry, and suggested `skip:` rules for a human to approve; safety-floor rules are never suggested.
- `scripts/post_review.sh <PR> <findings.json> [--post]`: opt-in PR delivery; dry run by default, `--post` creates one pending review via `gh`, refuses on banlist, secret or home-path hits and fails closed without a banlist.
- Tests: `scripts/test_review_feedback.py` (7), `scripts/test-post-review.sh` (10, stubbed `gh`), three evals, wired into CI.
- size-budget-raise: .claude/skills/deep-code-review/SKILL.md 23367→23496 one routing line for REVIEW.md in Phase 0
- size-budget-raise: .claude/skills/deep-code-review/references/machine-report.md 10061→10261 pointer to delivery and feedback tooling
