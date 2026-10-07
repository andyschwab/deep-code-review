### Added
- `review_checks.sh` (deep-code-review `scripts/`): runs only installed, local, read-only analyzers (shellcheck, bash -n, py_compile, ruff/pyflakes, node --check, tsc, go vet, jq) on the files changed since a base ref, timeboxed per tool, and prints findings JSON (file, line, rule, message, tool, plus `text` for `score_review.py`). Missing tools print a "not run" line; an opt-in `--tests` runs `REVIEW_TEST_CMD`. `method-situational.md` (loaded on every DIFF) routes to it as leads to verify. Test: `scripts/test-review-checks.sh` (wired into CI); eval `diff-review-runs-review-checks-first`.

size-budget-raise: .claude/skills/deep-code-review/references/method-situational.md 28534→29038 route DIFF review to review_checks.sh
