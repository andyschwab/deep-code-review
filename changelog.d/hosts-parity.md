### Added
- `install.sh --with-extra-hosts` now also writes skill roots for Qwen Code (`.qwen/skills`) and Grok Build (`.grok/skills`), with `host-safety.tsv` and `docs/host-safety.md` rows that state only what each vendor's sandbox docs confirm. Paths were checked against the vendor docs on 2026-10-16 (URLs in `docs/standards-index.md`), starting from the 16 harnesses in the obra/superpowers README.
- Antigravity, Devin CLI, Kimi Code and Pi read `.agents/skills` per their docs, which the default install already writes; Cursor and Hermes Agent were already written and are now docs-validated. Muse was skipped (no vendor docs found).

### Changed
- `docs/perun-vs-rivals.md` H10 now lists 19 hosts against the 16 names in the superpowers README, with 1 smoke-tested (Codex) and the rest docs-validated or file-placement tested, and states that the rival's per-harness marketplace installs are not like-for-like with Perun's skill-folder copies.
