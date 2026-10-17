# Bench-integrity gate (checks documented in scripts/bench_check.py): tests, then only bench dirs new vs origin/main.
python3 scripts/test_bench_check.py
if git rev-parse --verify -q origin/main >/dev/null; then python3 scripts/bench_check.py --changed origin/main; fi
