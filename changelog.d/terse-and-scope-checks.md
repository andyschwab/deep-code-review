### Added
- Opt-in `terse_reply_check.py` Stop hook (`install.sh --with-delivery --with-terse-replies`): blocks a filler-heavy final reply once and asks for a terser rewrite; fails open, honors `stop_hook_active`.
- Warn-only `scope_creep_check.py`: new files, new dependencies and single-implementation classes or interfaces for a git range; run by `pre-push-verify.sh` when installed.
- size-budget-raise: .claude/skills/agentic-delivery/references/host-enforcement.md 36672→38051 documents the two opt-in checks
