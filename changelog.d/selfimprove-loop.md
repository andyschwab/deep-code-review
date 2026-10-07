### Added

- `learning_to_pr.py` (contribution skill, opt-in primitive): turns a recorded lesson into a local upstream-PR draft (`change.patch` and `body.md`). Requires `--target`; refuses on any `prefile_check.sh` hit or any email, URL, IP or private-host match in title, lesson or target (regex backstop), skips near-duplicates of existing doctrine, honors `share_learnings=off`, never pushes or files. Not called automatically. Refs #1380.
