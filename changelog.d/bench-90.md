### Added
- Review benchmark corpus expanded from 18 to 90 held-out TEST cases (Go 31, Python 25, JS 19, shell 15) and from 9 to 44 TRAIN cases. The 62 newest cases come from permissive-licence public repositories through the existing builder and filters (introducing-commit diff of at most 600 lines, non-trivial fix, ground truth inside the diff, no duplicate of an existing case). TEST answers, patches and SHAs stay out of the repository exactly as before; the committed manifest carries hashed TEST ids, language, repository URL and licence only. TRAIN fixtures and upstream licence texts are committed under `scripts/eval-fixtures/bench/`. New check: `scripts/test_bench_corpus_90.py`.

No-Mechanism-Reason: data and test-only change; no SKILL.md or references file touched.
