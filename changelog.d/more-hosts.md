### Added
- `install.sh --with-extra-hosts` now also writes skill roots for Cline (`.cline/skills`), Roo Code (`.roo/skills`) and Factory Droid (`.factory/skills`). Each path and format was confirmed from the vendor docs on 2026-10-16 (URLs in `docs/standards-index.md`); OpenCode, Windsurf and Kiro, already written by that flag, are now docs-validated too. Amp reads `.agents/skills` and `.claude/skills`, so it needed no new directory. Continue documents rules only and was not added.
- `perun_doctor.py` now checks drift in every root `install.sh` can write, not only four.
- New `scripts/test_extra_hosts_install.py` (run in CI): fixture repo and HOME under `$TMPDIR`, install, doctor, then uninstall with 0 leftovers; a user-edited copy is kept and a pre-existing copy is restored.

### Changed
- `docs/perun-vs-rivals.md` H10 now counts 11 native hosts and marks each as smoke-tested (Codex only) or docs-validated. No new host was run on a real install.
