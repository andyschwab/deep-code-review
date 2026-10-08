### Added
- Autonomy-ready sandbox profile in the operating layer: `autoAllowBashIfSandboxed`, `gh *` excluded and allowed with destructive `gh` calls denied, common dev hosts pre-allowed, local binding on, `~/.cache` and `~/.npm` writable, so agents run without manual permission edits after install. `install.sh` now deep-merges sandbox and permission keys (existing values win, lists unioned).
- `sandbox_probe.py`: a first-run probe (git, ssl, network, local bind, cache write) that prints the exact fix for each failure; `install.sh` prints its one-line verdict and `perun_doctor.py` shows one row per check.
- `docs/host-safety.md#autonomy-ready-defaults`: each key, why, and its tradeoff.

### Fixed
- `install.sh` temp files honor `TMPDIR`, so an install run inside the macOS sandbox no longer fails on `mktemp`.
