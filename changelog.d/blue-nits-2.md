### Fixed
- `perun_policy.py set` skips disowning the policy file only when `PERUN_POLICY_INSTALL=install.sh` (exact value, set by `install.sh`), so a stray `PERUN_POLICY_INSTALL` export no longer stops a user `set` from disowning. Test: `scripts/test_install_policy_no_disown.py`.
- `agentic-ceo` Delivery-refs routing now matches `agentic-delivery`: Task to entry table first, else its read-when routing / `INDEX.md`. size-budget-raise: .claude/skills/agentic-ceo/SKILL.md 15708→15729 clearer fallback wording; no existing sentence to shorten
