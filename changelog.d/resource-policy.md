### Added
- Resource policy: one file, `.perun/policy.json`, sets `efficient` (default), `maximize`, `off` or a numeric cap per dimension (tokens, local_cpu, local_ram, github_actions, paid_api_calls, network). `scripts/perun_policy.py get <dim>` reads it; `train_land.sh`, `land_train.sh` and `host_probe.py` honor it (`github_actions: off` adds `[skip ci]` to merges and never waits on CI; `local_cpu` sets parallelism). Shipped workflows skip when repo variable `PERUN_GITHUB_ACTIONS` is `off`.
- `contribution/scripts/share_learning.py`: policy-gated (`share_learnings: auto|ask|off`, default `ask`), generalizes a lesson, runs `prefile_check.sh`, dedupes against open and closed upstream issues, files an issue only (never a PR), logs to a local ledger.
- `docs/for-fleets.md` "Efficiency by default" section with the self-improvement loop.

No-Mechanism-Reason: mechanisms are the new scripts and tests (scripts/test_resource_policy.py, scripts/test-resource-policy-train.sh); the doctrine lines only point at them.
