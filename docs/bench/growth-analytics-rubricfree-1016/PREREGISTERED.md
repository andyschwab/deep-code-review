# Preregistration: growth-analytics vs rival, rubric-free blind judge (2026-10-16)

Written and hashed (SHA256-frozen.txt) before the first call of any of the five re-tests. Harness reused from `docs/bench/comms-rubricfree-1016/` (driver, blind judge, both orders, split counts 0.5, bootstrap 10,000 resamples seed 1, ledger). Two harness differences, both declared here: the cap is read from the `CAP` environment variable (so the five runs share one $6 total), and the task wrapper and judge sentence are generalized from "message" to "deliverable" (same for all five skills, `prompts/gen_task.txt`, `prompts/judge.txt`).

## Why this pair, and the order

H1 claimed growth-analytics beat its rival with a rubric judge whose rubric was not preserved; product-output-safety (rubric 1.000 against rubric-free 0.150) and communication-structure (0.800 against 0.500) show the risk. Third: it fires on any measurement or experiment-reading question once something is shipping. Scenarios: metric choice, event design, test reads. Order of the five unchecked H1 wins: idea-critic, product-discovery, growth-analytics, positioning, contribution (by breadth of trigger; no usage telemetry exists). business-ops is not re-run: it did not claim a win.

## Arms (system prompt only, no tools, same model, same task wrapper)

- PERUN: `.claude/skills/growth-analytics/SKILL.md` at 6bb9a707 (frontmatter included), `prompts/perun.txt`. References and scripts are unavailable to either arm (no tools).
- RIVAL: coreyhaines31/marketingskills at commit 365b412152b9542499ca1439426f7fc3cc92bb65, fetched 2026-10-16 from its public source (codeload tarball of the main branch). Files: skills/analytics/SKILL.md and skills/ab-testing/SKILL.md (2 files concatenated, unmodified; matches the pair named in H1). License fetched 2026-10-16 from the LICENSE file of the same repository at the same commit: MIT, Copyright (c) 2025 Corey Haines. Full text in LICENSE.rival.txt. prompts/rival.txt is included unmodified (concatenated in the order listed).
- Generation: claude-sonnet-5-5, `--tools ""`, arm file as `--system-prompt`, wrapper `prompts/gen_task.txt` (under 500 words, same for both arms).

## Scenarios

10 fresh generic scenarios written by claude-opus-5-5 from `prompts/writer_brief.txt` and `prompts/seeds.txt`. The writer never sees either skill. Used unedited, none dropped. Fictional names only.

## Judge

claude-opus-5-5, blind Response 1 / Response 2, no criteria, `prompts/judge.txt`, verdict only. Both orders per scenario; a scenario score is the mean of 1 (Perun preferred), 0.5 (tie) or 0 per order, so a split counts 0.5. No rubric judge is run.

## Bar

Win rate of Perun over the rival, bootstrap over scenarios. PASS only if the 95% CI lower bound is above 0.5. Otherwise FAIL ("not shown superior"); a tie or loss is reported plainly. n=10 and a same-vendor judge are caveats on any outcome. One set, no skill edits, no re-runs after seeing results.

## Budget and stop rule

Hard cap $6 total across all five skills: each run gets CAP = 6 minus the ledgers of earlier skills, plus `--max-budget-usd` on every call and an in-flight reserve. A skill is started only if the remaining cap is at least 1.25 times the largest cost of an earlier skill (the first skill is always started); otherwise it is skipped and listed. A run that hits the cap mid-way is reported as incomplete, not as a result.
