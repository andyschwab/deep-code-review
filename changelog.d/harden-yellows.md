### Fixed
- `queue_guard.py` fails closed (exit 2) on a null issue `state`; `weekly_receipt.py` rejects `--days <= 0` (exit 2); `token_ratchet.py --write-baseline` refuses to overwrite an existing baseline without `--force`; the `ci-gates.sh rules` lint skips indented code fences; the `host_probe.py` docstring notes the `--lane-type heavy` load1 carve-out.
