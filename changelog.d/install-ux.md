### Fixed
- `perun_doctor.py` no longer exits 1 on a fresh default install. The janitor/scheduler and policy-file rows
  are optional add-ons that install does not ship, so they are now `INFO` rows and never fail the exit
  code; every real problem (version, hooks, drift, sandbox) still warns or fails.
- `install.sh` no longer grows `<host>/skill-backups/` on every re-run or update. A backup identical to
  the freshly installed copy is dropped, otherwise only the latest Perun backup per skill is kept. A
  pre-Perun original (a copy without a `VERSION` file) is never pruned.
- `perun_uninstall.py` now removes everything install wrote, from the install marker: the skill backups
  it created (a pre-install original only after it was restored), `house-defaults.md`, the
  `settings.local.json.bak.<timestamp>` files, the sandbox and permissions values the operating layer added,
  `settings.local.json` itself and `AGENTS.md` when install created them, the `AGENTS.md` blocks, and any
  directory left empty. On default and `--full` installs the tree is back to its pre-install state
  (0 leftovers, was 530 and 933 entries). Deletes are one file at a time, only for paths in the marker,
  each checked to resolve inside the target; no `rm -rf`. `docs/getting-started.md` now points at it.
