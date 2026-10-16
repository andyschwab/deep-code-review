# Preregistration: communication-structure vs humanizer, rubric-free blind judge (2026-10-16)

Written and hashed (SHA256-frozen.txt) before the first call.

## Why this pair

`docs/perun-vs-rivals.md` H1 claimed communication-structure beat humanizer 0.800 [0.550, 1.000] with a rubric judge whose rubric was not preserved. Among the H1 pairs that claim a win, communication-structure has the broadest trigger: its description fires before any human-facing message or report (PR body, status update, reply, summary), so it loads on far more tasks than a skill used once per plan or per feature. The one pair already re-tested rubric-free (product-output-safety) lost, so the same risk applies here. Scope note: humanizer is a rewriter of AI-sounding prose; half of the scenarios are rewrites and half are writes from facts.

## Arms (system prompt only, no tools, same model, same task wrapper)

- PERUN: `.claude/skills/communication-structure/SKILL.md` at origin/main 350274b2 (v1.2.4), `prompts/perun.txt`. References and scripts are unavailable to either arm (no tools).
- RIVAL: blader/humanizer SKILL.md v3.1.0 at commit 225a6f39, fetched 2026-10-16, `prompts/rival.txt`, unmodified. License MIT, text in `LICENSE.rival.txt`.
- Generation: claude-sonnet-5-5, `--tools ""`, arm file as `--system-prompt`, wrapper `prompts/gen_task.txt` (under 400 words, same for both arms).

## Scenarios

10 fresh generic scenarios written by claude-opus-5-5 from `prompts/writer_brief.txt` and `prompts/seeds.txt`. The writer never sees either skill. Used unedited, none dropped. 5 write-from-facts, 5 rewrite-a-draft. Fictional names only.

## Judge

claude-opus-5-5, blind Response 1 / Response 2, no criteria, `prompts/judge.txt` ("which would you rather receive"), verdict only. Both orders per scenario; a scenario score is the mean of 1 (Perun preferred), 0.5 (tie) or 0 per order, so a split counts 0.5. No rubric judge is run.

## Bar

Win rate of Perun over the rival, bootstrap over scenarios (10,000 resamples, seed 1, percentile). PASS only if the 95% CI lower bound is above 0.5. Otherwise FAIL ("not shown superior"); a tie or loss is reported plainly. n=10 and a same-vendor judge are caveats on any outcome. One set, no skill edits, no re-runs after seeing results.

## Budget

Hard cap $6 over everything in `ledger.jsonl`, plus `--max-budget-usd` on every call and an in-flight reserve; the driver stops at the cap.
