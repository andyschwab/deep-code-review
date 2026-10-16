### Fixed
- `perun_doctor.py` no longer exits 1 on a fresh default install. The janitor/scheduler and policy-file rows
  are optional add-ons that install does not ship, so they are now `INFO` rows and never fail the exit
  code; every real problem (version, hooks, drift, sandbox) still warns or fails.
- `install.sh` no longer adds a backup on every unchanged re-run or update: a backup byte-identical to the fresh copy (no symlinks anywhere in it or its path) is dropped. Install never deletes any other backup, and it refuses to back up through a symlinked `skill-backups` path.
- `perun_uninstall.py` now removes everything install wrote, from the install marker: the skill backups
  it created (shipped copies only; your pre-install copy is moved back), `house-defaults.md`, the
  `settings.local.json.bak.<timestamp>` files, the sandbox and permissions values the operating layer added,
  `settings.local.json` itself and `AGENTS.md` when install created them, the `AGENTS.md` blocks, and any
  directory left empty. On default and `--full` installs the tree is back to its pre-install state
  (0 leftovers, was 530 and 933 entries). Deletes are one file at a time, only for paths in the marker,
  each checked to resolve inside the target; no `rm -rf`. Only a provably unmodified, shipped Perun copy is deleted: a backup or skill file is removed only when its hash is one install itself shipped, anything else is kept and listed as `kept: user content`, your pre-install copy is moved back, marker keys with `..`, absolute paths or the wrong shape abort the run, and symlinked paths are skipped and never walked. `docs/getting-started.md` now points at it.
- Hardening: the marker `files` and `agent.path` keys may only name files install itself writes (slash commands, `house-defaults.md`, settings `.bak`, `delivery-lane.md`), so a forged marker cannot delete `src/app.py` or `.git/config`; `.` and `..` are not valid skill or backup names; a marker without shipped hashes keeps every file; empty-dir sweeps never follow a symlink; and the identical-backup check compares every file, `__pycache__` included.
