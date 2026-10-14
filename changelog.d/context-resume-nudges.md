### Added
- `context_nudge.py` (UserPromptSubmit) prints one line suggesting a fresh session from a short handoff note when the main context passes 250k tokens, then only per 50k of growth; `lane_resume_nudge.py` (PreToolUse `Agent|Task`) advises resuming an earlier same-domain lane with SendMessage instead of paying a new lane's startup. Both are advisory, fail open, have `--selftest`, and are wired by `--apply-operating-layer`.

### Changed
- The operating-layer template now wires `lane_cap.py` as a PostToolUse hook and sets `LANE_TOOL_CAP=150` (checkpoint at 80%, stop at the cap; field lanes ran 300 to 3,300 tool calls). Per-type `LANE_TOOL_CAP_<TYPE>` overrides still win; existing env values are kept on merge.
size-budget-raise: .claude/skills/agentic-delivery/references/operating-discipline.md 7053→7703 documents the context, lane-resume and lane-cap operating-layer hooks
