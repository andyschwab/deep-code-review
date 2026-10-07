### Added

- `impact_map.py` maps a diff's changed symbols to out-of-diff callers and callees (capped JSON), and `context_pack.py` bundles that with `git log --follow` history and optional PR intent into a bounded markdown pack. The method's DIFF depth section now makes out-of-diff tracing mandatory for multi-file or contract-changing diffs, and the machine-report rules warn when a contract change opened zero out-of-diff files. Tests use a synthetic multi-file repo (`scripts/test_impact_map.py`); one eval covers the doctrine.

