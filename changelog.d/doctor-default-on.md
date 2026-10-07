### Added
- `scripts/perun_doctor.py` (`--fix`): reports installed-but-never-runs hooks, missing hook files, stale repo/global versions, drifted forks, missing janitor/scheduler and policy file. `--fix` prints the plan and what default-on would add, then needs a typed "yes" on a TTY (or `--yes`, which warns) and fails loudly if the reinstall fails. See `docs/perun-doctor.md`.
- `scripts/perun_uninstall.py`: dry run by default, `--apply` to act. Driven by the install marker `.claude/.perun-install.json` (written by `install.sh` via `scripts/perun_marker.py`): removes only recorded hook entries, env values, a model pin Perun set, and skill files whose hash still matches; your added or edited files are kept and listed. Settings are validated first and written by temp file plus rename.
- `land-release.sh tag`: creates and pushes the annotated tag `vX.Y.Z` only after the release commit is on origin/main; an existing local tag is skipped with a message. Land itself never tags (tags had stopped at v1.211.0).

### Changed
- `install.sh --with-delivery` / `--full` applies the operating layer by default and prints a what-changed and undo summary that names the model pin; `--no-operating-layer` opts out. Settings backups are now timestamped (`settings.local.json.bak.<ts>`) and never overwritten.
