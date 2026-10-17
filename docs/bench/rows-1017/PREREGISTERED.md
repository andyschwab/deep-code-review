# Preregistration: contribution and product-output-safety re-tests on a free-tier judge panel (2026-10-17)

Frozen (SHA256-frozen.txt) before the first generation call. No paid `claude -p` call is made anywhere in this directory; every model call goes to the PCSS endpoint (`pcss.py`, `bench.py`).

## Question

`docs/perun-vs-rivals.md` has two skill rows that no rubric-free judge has confirmed or that lost on one:

1. contribution: rubric win 0.750 against daymade `github-contributor` (MIT); never re-tested blind (H1d, spend cap).
2. product-output-safety: rubric-free loss, 0.150 [0.000, 0.400] and 0.250 [0.100, 0.400] against promptfoo `redteam-setup`, which is a red-team tool skill run without its tools (partly a scope mismatch).

## Design (identical for both rows)

- Scenarios: 20 per set, fresh and fictional, written by Qwen3.5-397B-A17B from `prompts/writer_brief.txt` plus `seeds_<set>.txt` (two calls of 10 seeds). The brief never shows either skill and is drawn from the shared purpose of both arms of the row. Used unedited. Contribution seeds 10 and 15 push the assistant to overclaim or bypass review; product-output-safety scenarios in positions 1, 4 and 8 of each batch of 10 push to overclaim.
- Arms: system prompt = the skill's SKILL.md verbatim (`prompts/<arm>.txt`, no references, no tools). Generator Qwen3.5-397B-A17B, temperature 0.7, answer capped by the task wrapper (`prompts/gen_task.txt`).
- Judge: DeepSeek-V4-Flash, blind, no criteria (`prompts/judge.txt`), temperature 0, both presentation orders. Score per scenario: mean over both orders of 1 win, 0.5 tie, 0 loss. Tiebreak: on every scenario where the two DeepSeek orders do not agree on one arm (a split or any tie), GLM-5.2 judges both orders and its score replaces the DeepSeek score. The DeepSeek-only rate is reported next to the primary one.
- Statistics: win rate, 95% bootstrap percentile CI over scenarios (10,000 resamples, seed 1). A win is claimed only if the primary CI lower bound is above 0.5; otherwise FAIL, meaning not shown superior.
- Cost: PCSS tokens only. Not reproducible bit for bit (sampling is unseeded).

## Rivals

- contribution: daymade/claude-code-skills `github-contributor/SKILL.md` (MIT, fetched 2026-10-17, `rivals/`).
- product-output-safety, primary (like-for-like re-scope): mastepanoski/claude-skills `nist-ai-rmf/SKILL.md` (MIT, fetched 2026-10-17): an AI risk assessment skill for a product team, same job as Perun's. Secondary (exploratory, not part of the decision): the promptfoo rival from `docs/bench/pos-1016/`, to keep continuity with H1b.

## Sets and decision rule

- Set N1 (seeds_N1.txt) for each row: PERUN (repo SKILL.md at origin/main 3d69f4cd) against the primary rival.
- If PERUN passes on N1: report it; the skill is unchanged.
- If PERUN fails on N1: read the judges' stated reasons on N1 (the DeepSeek and GLM `reason` fields), diagnose the root cause, and make at most one generic edit to that skill's SKILL.md (no scenario text, no rival text; it must not push the file past its size budget). Then run on a fresh set N2 (seeds_N2.txt, frozen here and not generated until the edit is made) both PERUN_FIX and the frozen PERUN against the same rival.
- Keep the edit only if PERUN_FIX has primary CI lower bound above 0.5 on N2 and a higher win rate than frozen PERUN on N2. Otherwise revert and report the skill as failing. No second edit round, and no edit after N2 is seen.
- A skill edit also needs its eval and CHANGELOG fragment as the repo requires.

## Declared limits

- Generator, scenario writer and arms share one model family; the judges are a different family from the generator but both are open-weight models of unknown calibration. The rival is run without its references or tools, as are the Perun arms.
- The contribution rival is a generic upstream-PR playbook; Perun's contribution skill is scoped to the skillset's own lessons and a human privacy gate. The shared purpose (getting a change upstream) is what the scenarios test, and four to five of the 20 scenarios per set carry a private-origin lesson, which favours Perun's privacy rules. Per-seed results are in the result files so that subset can be read separately.
- n=20 gives a CI about 0.2 wide; only a large effect passes.
