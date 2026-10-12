### Added
- Learned-rules lifecycle in `review_feedback.py learn`: candidate, shadow, promoted, disabled derived deterministically from the feedback ledger into a capped `.review/learned-rules.md` that a review loads only if present. Safety-floor rules are never disabled. Tests: `scripts/test_learned_rules.py` (5).
- size-budget-raise: review-config.md and review_feedback.py carry the learn lifecycle.
