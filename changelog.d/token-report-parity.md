### Fixed
- agentic-ceo `token_report.py` now counts nested `usage.iterations[]` spend (e.g. advisor calls, booked on their own model), which it previously dropped (about 3% of tokens, 8-12% of cost on advisor-heavy sessions).

### Changed
- agentic-ceo `token_report.py` prices out of the box with a built-in default rate table (official pricing page, 2026-10-15) and labels the cost "priced with default rates as of 2026-10-15"; `--rates` overrides it and unknown models stay UNPRICED.
