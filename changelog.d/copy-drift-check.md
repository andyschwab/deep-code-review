### Added

- `session_brief.py` (SessionStart hook) now warns with one line when the same Perun skill has different `version:` values across the global `~/.claude/skills` and the project's `.claude/skills`, `.cursor/skills` and `.agents/skills`, so a stale project copy no longer runs silently. Silent when copies agree; missing locations and unparsable versions are skipped. `--selftest` covers positives, negatives, missing dirs and unparsable versions.
