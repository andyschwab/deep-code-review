### Changed
- `lane_guard.py wait` takes `--progress FILE` (and `--progress-every SECS`, default 900) and keeps one liveness line in FILE while waiting. The lane preamble now says: hand back one line plus the path of a committed details file, use `--progress` for long waits, and on a sandbox push/network failure commit and hand back branch plus sha instead of retrying.
