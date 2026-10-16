### Fixed
- `install.sh` now prints a `safety:` line for Cline, Roo Code and Factory Droid, as it does for the other hosts. The new rows in `host-safety.tsv` and `docs/host-safety.md` state only what each vendor's docs confirm (fetched 2026-10-16, URLs in `docs/standards-index.md`) and mark the rest `unverified`: Cline and Roo Code document no OS sandbox, Factory Droid has an opt-in one.
- `dcr-gates.sh` now looks for the installed skill under `.cline`, `.roo` and `.factory` too, and `.gitignore` covers their `skill-backups/` folders.
