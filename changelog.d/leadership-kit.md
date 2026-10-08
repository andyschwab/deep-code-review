### Added

- `docs/for-leaders.md`: one-page leadership brief (what Perun does, what changes, measured numbers each cited to a repo file or labeled unmeasured, risks and controls, a three-step pilot), linked from the README.
- `scripts/check-leader-doc.sh`: docs gate, wired into CI, that fails when a line of the brief carries a number without a link to an existing file or the word "unmeasured". Includes a self-test.

size-budget-raise: README.md 15804→15853 one-line link to the leadership brief
