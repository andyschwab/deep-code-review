### Added
- agentic-delivery: `clock_lint.py [--base REF] [FILES]` flags tests that read the real clock (`Date.now()`, `datetime.now()`, `time.time()`, `time.Now()`, shell `date`) unless a real fake clock (freezegun, time_machine, fake timers, an injected `now=`) is in scope of that test, as `file:line: real clock in test; pin a fake clock or inject now`; exit 1 on findings, 2 and `COULD_NOT_CHECK` on an unreadable file, `clock-lint: allow` as the per-line escape. The pre-push template runs it warn-only on the pushed range, so installed repos get it with no setup. Doctrine: the future-clock run in `verification-handback.md` **Done means verified**; review lens in `testing-situational.md`.

size-budget-raise: .claude/skills/agentic-delivery/references/verification-handback.md 58477→59102 future-clock run bullet
size-budget-raise: .claude/skills/deep-code-review/references/testing-situational.md 40032→40355 real-clock review lens sentence
