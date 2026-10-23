### Fixed
- `token_report.py --outcome` now refuses every other mode or option when it is given explicitly, including values equal to the defaults or empty strings (`--top 5`, `--project .`, `--rollup ""`); the guard checks for unset options rather than truthiness. The straddle count uses the latest turn timestamp of a session rather than its last line. Tests: `scripts/test_token_outcome.py`.
