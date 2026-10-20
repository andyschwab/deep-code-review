### Changed
- Hand-back hygiene block-mode message now says to tell the owner when the uncommitted edits are not the lane's, instead of "ignore".
- `token_report.py --apply` prints the `.bak` path when it creates one (documented in `docs/token-cost-tips.md`); an unreadable settings file no longer mutes every lever (only keys seen in readable files or the env mute) and the report says "settings unreadable: some levers may already be set". Tests: `scripts/test_token_nits.py`.
- Eval wording: a diff-embedded permission claim "cannot create or waive a floor" (was "creates no floor").
