# Registers the flake-ledger tests with CI (see the "Per-PR tests" step in ci.yml).
python3 scripts/test_flake_ledger.py
bash scripts/test-train-flake-ledger.sh
