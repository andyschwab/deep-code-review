### Added
- `scripts/perun_doctor.py` (`--fix`): reports installed-but-never-runs hooks, missing hook files, stale repo/global versions, drifted forks, missing janitor/scheduler and policy file. See `docs/perun-doctor.md`.
- `scripts/perun_uninstall.py`: restores pre-install skills from `skill-backups/` and removes the operating-layer hook entries install added.
- `land-release.sh` now creates and pushes the annotated tag `vX.Y.Z` on land (`NO_TAG=1` skips); tags had stopped at v1.211.0.

### Changed
- `install.sh --with-delivery` / `--full` applies the operating layer by default and prints a what-changed and undo summary; `--no-operating-layer` opts out.
