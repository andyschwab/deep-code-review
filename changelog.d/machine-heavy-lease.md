### Added
- `perun_policy.py heavy-acquire` / `heavy-release`: machine-wide heavy-job lease (one pid file per job under the user cache dir, stale leases ignored) so several sessions on one host stop each taking the full heavy-slots count; wired into the lane-preamble heavy gate.
