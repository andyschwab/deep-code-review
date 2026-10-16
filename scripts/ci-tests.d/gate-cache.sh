# Registers the gate-cache and lane-weight tests with CI (see the "Per-PR tests" step in ci.yml).
python3 scripts/test_gate_cache.py
python3 scripts/test_prepush_gate_cache.py
python3 scripts/test_train_gate_cache.py
python3 scripts/test_gate_map.py
python3 scripts/test_lane_weight.py
