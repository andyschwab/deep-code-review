### Added
- Admission control for heavy local commands: `perun_policy.py heavy-slots` adds a concurrency primitive `max(2, free cores)` and `host_probe.py --lane-type heavy` defers (`HOLD load-high`) when load1 exceeds cores; the existing free-RAM veto already defers on low RAM. Tests inject load and core values. Not yet wired into a hook or lane template; a consumer adopts it explicitly.
