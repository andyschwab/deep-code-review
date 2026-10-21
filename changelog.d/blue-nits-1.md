### Fixed
- `outcome_claim_guard.py` no longer reads `vite-plugin-*`, `vite.config.ts` or `vite-node` as a dev-server restart, and `vite builder` now counts as one (only `vite build` is excluded).
- `perun_policy.py` rewrites the install marker atomically (tmp file + `os.replace`) when `set` disowns the policy file.
- `install.sh --policy k=v` no longer disowns the policy file (only a user-run `perun_policy.py set` does), and it records whether install created `.perun/policy.json` before `--policy` writes it. Uninstall now removes a file install created in full while it is unchanged, so install then uninstall leaves no `.perun/policy.json`. Tests: `scripts/test_install_policy_no_disown.py`.
