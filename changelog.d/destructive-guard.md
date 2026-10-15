### Added
- agentic-delivery: `destructive_guard.py`, a PreToolUse(Bash) hook wired by the operating layer. It never runs the command; it unwraps `bash -c`, `env`, `sudo`, `xargs` and `/bin/rm`, then denies `rm -r` on a variable, glob, root or home path, `git reset --hard`, `git clean -f`, force-push, `git checkout .`, `find -delete`, `dd` to a device, `mkfs`, `chmod -R /`, `curl | sh` and kill-by-pattern, each with a safe alternative. An owner-authored `destructive-guard-allow:` line in `CLAUDE.md` is the escape hatch. On the 32-command bench corpus it blocks 30 (was 11) with 0 of 30 false positives. Tests: `scripts/test-destructive-guard.sh`.

size-budget-raise: .claude/skills/agentic-delivery/references/operating-discipline.md 9020→9302 destructive_guard pointer in the safety rules
