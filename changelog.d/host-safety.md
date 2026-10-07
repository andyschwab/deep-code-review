### Added
- `docs/host-safety.md`: per-host table (Claude Code, Cursor, Codex, Gemini CLI, Copilot, OpenCode, Windsurf, Hermes, Kiro, shared `.agents`) of OS-sandbox presence and default, the documented switch, auto-approve modes to avoid and residual risk, plus the rule that hosts without an OS sandbox run agents in a dev container or VM. Sources dated in `docs/standards-index.md`.
- `install.sh` prints one `safety:` warning line (with the doc link) per installed host, from the single-source `templates/host-safety.tsv`.
- `host_safety.py` and `operating_selfcheck.py` report `host-safety-<host>: ON | OFF | COULD_NOT_CHECK | NO_OS_SANDBOX` for each installed host. Tests: `scripts/test-host-safety.sh`.
