### Added
- Host-native install manifests: `.codex-plugin/plugin.json` plus `.agents/plugins/marketplace.json` for Codex, and a root `gemini-extension.json` for Gemini CLI (context-only: it loads `AGENTS.md`, because Perun's skills live under `.claude/skills`, not the `skills/` Gemini reads). Copilot CLI documents that it reads the existing `.claude-plugin/marketplace.json`, so it gets no new file. The README lists one install command per host.
- Codex was smoke-tested for real with an isolated `CODEX_HOME`: `codex plugin marketplace add` then `codex plugin add deep-code-review@perun` installed the plugin and the model prompt lists all 11 skills. Gemini was validated against the documented fields only.
- `land-release.sh` stamps the new manifests' versions with `plugin.json`, and the `version` gate in `ci-gates.sh` fails if any of them drifts. `scripts/test-host-manifests.sh` checks the manifests' shape and paths.

Tests: test-host-manifests.sh ok; ci-gates version ok; bash -n land-release.sh ci-gates.sh ok.
