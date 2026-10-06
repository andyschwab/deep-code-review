# Peer loop

Runs on a second machine or session. Cadence: every 30 minutes, or on a claim notification. Never faster
than 20 minutes.

## /loop prompt (copy-paste)

```
/loop 30m Peer wake for <machine>. Run once, in order, then stop.
1. Capacity: if the host probe says full (references/fanout-host-sizing.md), post "full" on the coordination
   issue and skip to step 3.
2. Pull: take the oldest open issue labelled `lane:<machine>`. Run `claim_probe.py` first, then assign it
   and post a claim comment (pull-queue doctrine, references/multi-session-coordination.md). Start one lane
   from templates/lane-preamble.md. Never wait for a message to confirm.
3. Clean up after yourself: `ROOT=<repo-root> bash .claude/skills/agentic-delivery/scripts/reap_own.sh`, then
   `ROOT=<repo-root> bash .claude/skills/agentic-delivery/scripts/clean_finished.sh`.
4. Post your free-lane count on the coordination issue.
Nothing labelled and nothing to clean: one line, end the wake.
```

## Scheduled-task template

```
name: peer-wake-<machine>
schedule: every 30 minutes   # never under 20 minutes
prompt: <the text after "/loop 30m" above>
working_dir: <repo-root>
```
