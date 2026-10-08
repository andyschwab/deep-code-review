### Fixed

- `weekly_receipt.py` and `token_ratchet.py` now share one tokens-per-PR measure from `token_report.py`: weighted tokens (input-equivalent plus output, cache reads at 0.1x) and one distinct first-parent `Merge pull request #N` count. The receipt previously summed raw tokens (cache reads at full weight), which inflated its figure about 10x against the ratchet's. Test: `scripts/test_tokens_per_pr_parity.py`.
