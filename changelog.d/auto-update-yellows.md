### Fixed
- Auto-update legacy installs (no `.perun-install.json`) read `version:` only inside a properly closed `---` frontmatter block of the installed `SKILL.md`; with no closing `---` the version is unreadable and the run is a logged skip instead of scanning the whole file.
- A legacy install always updates from the canonical remote: if the cache clone (`$XDG_CACHE_HOME/perun/src`) was cloned from a different origin, the run logs a skip rather than inheriting that origin into the new marker.
- Docs for the legacy path no longer claim uncommitted-change skips apply to it: only git locks and an uncommitted `.claude/settings.local.json` skip; uncommitted skill edits are preserved by install.sh's backup, not by a skip.
