# Registers the changelog-fragment gate and the pr_state tests with CI (see the "Per-PR tests" step in ci.yml).
bash scripts/ci-gates.sh fragments --config scripts/size-budgets.tsv changelog.d
python3 scripts/test_pr_state.py
bash scripts/test-changelog-fragments.sh
