### Added
- Learned-rules lifecycle in `review_feedback.py learn`: candidate, shadow, promoted, disabled derived deterministically from the feedback ledger into a capped `.review/learned-rules.md` that a review loads only if present. Safety-floor rules are never disabled. Tests: `scripts/test_learned_rules.py` (5).
- size-budget-raise: review-config.md and review_feedback.py carry the learn lifecycle.
- `record` now regenerates `learned-rules.md` beside the ledger and SKILL.md Phase 0 loads it when present; area A joins the never-disable floor; control characters in a rule are rejected; one threshold source (`DISABLE_MIN`).
- Areas F, G and I (reliability, concurrency, contracts) join the never-disable floor.
