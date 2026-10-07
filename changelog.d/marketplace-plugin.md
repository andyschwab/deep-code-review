### Added
- Claude Code plugin marketplace: `.claude-plugin/marketplace.json` (name `perun`) lists the plugin with source `.`; `docs/team-install.md` (linked from the README) documents add, admin managed-settings push, update propagation and pinning; `ci-gates.sh version` now fails when `plugin.json` drifts from `VERSION` or the marketplace entry sets its own version.
- Plugin slash commands `/deep-code-review:review`, `:deliver` and `:cost-retro` (`commands/`), each pointing at existing skills and doctrine.
- Spend attribution convention (`<tracker-project-id>-<handle>` key names, per-project keys, alerts before caps) in `operating-discipline.md`, and `agentic-delivery/scripts/spend_report.py` to total a provider usage export per project (offline, stdlib).
- `docs/token-cost-tips.md`: short token-cost tips for teams, each with a number already measured in this repo.
- `agentic-ceo` routing: if a kickoff skill is installed, run it first; Perun reviews and delivers.

size-budget-raise: .claude/skills/agentic-delivery/references/operating-discipline.md 4875→5402 spend attribution item
size-budget-raise: .claude/skills/agentic-ceo/SKILL.md 12616→12725 kickoff interop line
