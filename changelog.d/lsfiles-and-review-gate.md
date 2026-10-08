### Changed

- Repo-scanning gates now enumerate git files instead of walking the filesystem: `ci-gates.sh privacy` and `size`, the `land-release.sh` size-row regen and `perun_doctor.py` read `git ls-files -co --exclude-standard` at a git work-tree root, so nested worktrees and gitignored build directories are never scanned (a planted violation there no longer fails every push). `find`/full walk remains only outside a git root. Pinned by `scripts/test_scan_tracked_only.py`. The other `os.walk` users (lint/test scanners over caller-named paths, transcript walks) take explicit paths and are unchanged.

### Added

- Per-PR independent review gate (warn-first). `agentic-delivery/scripts/review_gate.py`, called per member PR by `land_train.sh` (so `train_land.sh` inherits it), looks for a review receipt (`.perun/reviews/<pr>.json`, written by `review_gate.py receipt`) or a `perun-review` PR comment marker from a reviewer other than the author, for the exact head being merged. New policy key `review_gate`: `warn` (default), `enforce`, `off`. **Warn-only for this release**: a PR with no receipt prints a WARN and still lands; `enforce` skips it; `review_gate=off` opts out. Expect `enforce` to become the default in a later release. Routed from `agentic-delivery/SKILL.md`; tested by `scripts/test_review_gate.py`.

size-budget-raise: .claude/skills/agentic-delivery/SKILL.md 23879→23999 one routing line for the review gate
size-budget-raise: .claude/skills/agentic-delivery/references/merge-queue-worktrees.md 66147→67237 review-gate section (policy, receipt format, warn-first)
