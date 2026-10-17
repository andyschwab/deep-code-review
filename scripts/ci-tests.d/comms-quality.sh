# Registers the comms-quality tests with CI (see the "Per-PR tests" step in ci.yml).
python3 scripts/test_status_update_lint.py
python3 scripts/test_comms_lint.py
python3 scripts/test_comms_guard.py
