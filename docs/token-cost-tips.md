# Token cost tips for teams

**BLUF:** the biggest savings come from sending less context, using the cheapest model tier that
clears its own gate, and measuring before you cut. Each tip below carries a number already
measured in this repository; adapt the settings to your own fleet and re-measure.

1. **Load less method text.** Must-read method files for a review dropped from 65,903 to 28,025
   estimated tokens (FULL repo review: 87,137 to 36,096, about 57% less), and CI blocks growth.
   See [README](../README.md), "What you get".
2. **Cap what every turn resends.** Set `bashOutputMaxChars` (start at `10000`) and
   `skillListingMaxDescChars` (start at `300`, default `1536`); use `"name-only"` for skills a
   project never needs. See [`host-enforcement.md`](../.claude/skills/agentic-delivery/references/host-enforcement.md), "Per-turn token levers".
   `token_report.py` measures the lever: `tool_results` in `--json` counts main and lane tool results over 10,000 chars by tool
   (`by_tool`: Bash/PowerShell, Read, other) and estimates their carry (4 chars per token x turns resent until the next compaction x
   0.1 cache-read weight, clamped to input-eq). Above 5% of session input-eq from Bash/PowerShell output past the cap it ranks a
   `cap Bash output with bashOutputMaxChars` row marked `estimate: true`; large Read and MCP results get info lines only, since the setting caps Bash output only.
3. **Default to the cheapest tier that passes its gate.** Mechanical steps get the cheapest tier at
   low effort; build and audit lanes get mid; only verify and judge stages get top at high effort.
   See [`model-tiering.md`](../.claude/skills/deep-code-review/references/model-tiering.md), "Route delivery lanes by work type and stage".
   Thinking tokens bill as output, so lower the effort level (`/effort low` or `/effort medium`) for routine work and set it at the start of a task, since except on Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 (API key or subscription) a mid-session change re-reads the context uncached;
   `--advise` fires `effort` when main output averages 1,500 or more tokens per turn and is at least 30% of main input-eq plus output with no effort level set (heuristic thresholds, not calibrated on a corpus).
   Docs: [Manage costs](https://code.claude.com/docs/en/costs), [Model configuration](https://code.claude.com/docs/en/model-config), [Prompt caching](https://code.claude.com/docs/en/prompt-caching).
4. **Do not use the cheapest tier for judgment.** A cheapest-tier dedupe lane matched 13 of 23
   findings to unrelated issues by keyword and reported comments as posted that did not exist; a
   mid-tier lane found zero such comments. Same file, same section.
5. **Do not let every lane consult a stronger model.** Parallel lanes' own consults were the
   dominant top-tier spend, about the cost of 3 to 4 mid-tier lanes per consult. Omit the consult
   tool from lane toolsets. Same file, same section.
6. **Cache inside one model.** Cache reads cost 0.1x base input on most models (writes 1.25x at a
   5-minute TTL); switching models mid-task forfeits the cached prefix. See
   [`model-tiering.md`](../.claude/skills/deep-code-review/references/model-tiering.md), lever 2.
   A rebuild with no model change is a changed prefix (an MCP server connected or removed, a plugin, a whole-tool deny rule, fast mode, an effort change, many images); do those at a task boundary.
   Editing CLAUDE.md or files mid-session does not invalidate the cache. `--advise` fires `cache-bust` on 2 or more main turns within 150 seconds of the previous turn,
   on the same model, with a context of at least 100,000 tokens where cache read was under 5% of the previous context, whatever the growth; a collapse with a net shrink stays silent because it looks like compaction. It is a heuristic: a clear of the oldest tool results can also fire; `/usage` names the likely cause. Docs: [Prompt caching](https://code.claude.com/docs/en/prompt-caching).
7. **Keep hand-backs short.** Lane narration multiplies across a fleet; cap hand-backs and report
   status first. See [`host-enforcement.md`](../.claude/skills/agentic-delivery/references/host-enforcement.md), "Subagent handback".
8. **Fewer, longer-lived lanes.** Each subagent start pays the project's instruction files again;
   resume a worktree instead of spawning short lanes. See `model-tiering.md`, same section as tip 3.
9. **Measure per session, then per project.** `agentic-ceo/scripts/token_report.py --session
   <transcript> --budget` reports main versus subagent tokens and flags lanes over their caps;
   `/perun:cost-retro` turns that into "what would have been cheaper". Add `--advise` for rule-based
   advice (each rule is one measured signal, one lever, one link back here); a lever you already set is never recommended.
   `--fix-plan` prints the matching settings patch and `--apply PATH` merges it (backup first, absent keys only, safe to re-run; the `.bak` keeps only the first original and its path is printed when created). A reproducible run on a synthetic session, next to six peer tools: [`docs/bench/token-levers/`](bench/token-levers/README.md).
   Add `--project DIR` to price each auto-loaded instruction file (CLAUDE.md, user-level CLAUDE.md, memory) across lanes: file bytes/4 is an estimate (skipped under `--since`), and the report ranks the largest as a trim lever.
10. **Attribute spend before capping it.** Name keys `<tracker-project-id>-<handle>`, prefer one key
    per project, set alerts first, caps last, and total an export with
    `agentic-delivery/scripts/spend_report.py`. See [`operating-discipline.md`](../.claude/skills/agentic-delivery/references/operating-discipline.md), item 9.
11. **Compact on your schedule, not mid-task.** `/clear` between unrelated tasks, `/compact` at
    natural breaks, and set the auto-compact window (`/autocompact 200k`, or `autoCompactWindow` in settings; valid range
    100K to 1M) so a long session compacts before it gets expensive. Every compaction rewrites the cached prefix, and `/context`
    shows what fills the window. Docs: [Manage costs](https://code.claude.com/docs/en/costs), [Commands](https://code.claude.com/docs/en/commands), [Settings reference](https://code.claude.com/docs/en/settings-reference).
    After a gap longer than the cache lifetime the next turn re-reads the whole context uncached, and a `/compact` then reprocesses it uncached too,
    so `/compact` before stepping away or `/clear` if the next task is unrelated. `--advise` fires `idle-resume` on 2 or more main turns that re-wrote
    at least half of a 100,000-token-or-larger context after a gap over 1 hour (past the one-hour TTL, so a pin does not help). Docs: [Prompt caching](https://code.claude.com/docs/en/prompt-caching).
12. **Keep MCP tool definitions out of every turn.** Tool search defers MCP tool definitions by default, so leave
    `ENABLE_TOOL_SEARCH` unset (`false` loads them all upfront), disable servers this project never calls (`/mcp`), and
    prefer a CLI such as `gh` where one exists. Claude Code warns at 10,000 tokens of MCP output (`MAX_MCP_OUTPUT_TOKENS`,
    default 25,000). Docs: [MCP](https://code.claude.com/docs/en/mcp), [Manage costs](https://code.claude.com/docs/en/costs).

An estimate is not a billed total: mark anything you cannot price `UNPRICED`, never zero.
