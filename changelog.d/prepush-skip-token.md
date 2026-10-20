### Changed
- Pre-push: a tip commit message that quotes a GitHub skip token (which silently skips pull_request CI) is refused with the token named; `github_actions=off` (env or policy) or `DCR_PREPUSH_ALLOW_SKIP_CI=1` allows it.
