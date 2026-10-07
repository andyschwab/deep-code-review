### Added

- `learning_to_pr.py` (contribution skill, opt-in primitive): turns a recorded lesson into a local upstream-PR draft (`change.patch` and `body.md`). Refuses on any `prefile_check.sh` hit, skips near-duplicates of existing doctrine, honors `share_learnings=off`, never pushes or files. Not called automatically. Refs #1380.
