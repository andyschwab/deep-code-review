### Changed

- `agentic-delivery` description now names build intents (build, add, ship, deliver, fix a ticket) and says to invoke it before inspecting files, even in an empty directory. In a 30-prompt routing run (N=1, claude-sonnet-5-5, near-empty directory), build prompts invoked the skill 1/10 before and 10/10 after; review stayed 7/10 and non-code moved 8/10 to 7/10. Adds an `evals.json` case.
