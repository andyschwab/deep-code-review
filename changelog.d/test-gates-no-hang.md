### Fixed

- `scripts/test-train-scripts.sh` no longer hangs or leaks `sleep` children when `pgrep`/`ps` are denied (restrictive sandbox): the reap_own blocks SKIP, every background child is bounded to 60s and reaped on exit via `jobs -p` (no `pkill`). New `scripts/test-no-hang-without-pgrep.sh` asserts the SKIP and prompt return.
