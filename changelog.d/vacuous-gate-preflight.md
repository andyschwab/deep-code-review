### Added
- `scripts/vacuous_test_gate.py`: fails a changed test file that executed 0 tests, skipped every test, or reported 0 assertions (JUnit XML, Jest JSON, pytest-json-report); a changed file missing from the report is `COULD_NOT_CHECK`, never green. Routed from `verification-handback.md`.
- `scripts/preflight.py`: runs all cheap gates from a JSON list first and prints every failure together, runs expensive gates only if they pass (or `--all`), caches per-gate wall time and prints the slowest; an unstartable gate is `COULD_NOT_RUN`. Routed from `red-gate-triage.md`.
- Both have `--selftest`, wired into `scripts/test-ci-gates.sh`.

size-budget-raise: .claude/skills/agentic-delivery/references/verification-handback.md 59384→59723 route the vacuous-test gate
size-budget-raise: .claude/skills/agentic-delivery/references/red-gate-triage.md 21607→22000 route the preflight runner
