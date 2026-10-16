### Fixed
- Shipped scripts no longer call bare `mktemp`. macOS bare `mktemp` ignores `TMPDIR`, which broke sandboxed runs. Every call now takes `"${TMPDIR:-/tmp}/<name>.XXXXXX"` (with `-d` where it was used): `review_checks.sh`, `integrator-gate.sh`, `merge_train.py`, and four test scripts. Existing trap cleanup is unchanged.
- New regression `scripts/test-mktemp-tmpdir.sh` (run in CI) fails on any non-comment bare `mktemp` in `.claude/skills` or `scripts`, after a positive control proves the pattern matches a bare call.
