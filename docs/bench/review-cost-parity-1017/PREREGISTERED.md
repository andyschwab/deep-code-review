# Pre-registration: cheaper deep-code-review small-diff review, quality parity with pr-review-toolkit

Version 2, frozen 2026-10-17 by its own commit, BEFORE any outcome data. Version 1 (commit 0e2da8b1, Claude Sonnet reviewer, Opus and Qwen judges, $ cap) was replaced before any paid or outcome call because the plan quota was exhausted and paid claude -p calls were stopped. Zero paid calls were made. Edits after this commit go in DEVIATIONS.md, never in place.

## Question
The real skill ties the Anthropic pr-review-toolkit code-reviewer (TK) on F1 but costs $.0537 per review against $.0153 (docs/perun-vs-rivals.md, comparison row 2, Claude Sonnet via claude -p). Can the smallest skill edit cut the review's token cost by 2x or more with no measurable loss against TK? Scope modes and the report contract do not change.

## Host-model caveat (read first)
Both arms run on PCSS Qwen3.5-397B-A17B (https://llm.hpc.psnc.pl/v1), not on Claude, through a minimal tool loop in driver.py (read_file, grep, glob; at most 12 turns), with no Claude Code system prompt. Token counts carry over to any model because the skill text, patch and the number of turns are the same inputs; the quality result (F1 against TK) is measured on Qwen only and may not transfer to Claude. The earlier $ figures (Claude, claude -p, whose default system prompt TK's --system-prompt replaces) are context, not a baseline. Prior Claude outputs and Opus verdicts are not reused. Nothing here shows the edit keeps Claude's quality.

## Materials (frozen)
- Base: origin/main at v1.587.0. Corpus: scripts/eval-fixtures/bench/train, 43 patch-only cases; reviewer sees change.patch only (plus the skill copy for the skill arm).
- Split: split.json (from the lead's bench-local/cf-vs-tk-1016/split.json: sort ids by sha256, first 21 = tune, last 22 = held-out). The brief says "21 held-out"; the file holds 21 tune and 22 held-out and is authoritative: held-out n=22.
- Arms, all one run per case, one retry on error, temperature 0: BASE = the unedited skill (copy in the workspace, scripts/bench_corpus.py PERUN prompt, same as the earlier REAL arm); NEW = the edited skill with the same prompt; TK = tk_system.txt as system prompt with the PRODUCER request. Tools: read_file, grep, glob in the case workspace. BASE and TK run on all 43 cases; NEW variants on tune, the final one on held-out.
- Judges (free, PCSS, no tools, patch text inlined, runner VERIFY prompt, blind to arm): DeepSeek-V4-Flash judges every strict-unmatched finding of every arm. Tiebreak: if its verdict for a finding is missing, unparsable or "unverifiable", GLM-5.2 judges that finding and its verdict stands (my reading of "GLM-5.2 as tiebreak"). Crediting, strict matcher (score_review), and the paired case-level bootstrap (10000 resamples, seed 1, pooled ratios, 95% percentile CI) are unchanged from docs/bench/review-real-skill-1016-heldout/driver.py. Key read from the repo-root .env, never printed.
- Tokens per review T = sum over all turns of (prompt_tokens + completion_tokens) from the API usage field (completion includes reasoning). Also reported: turns, first-turn prompt tokens, output tokens. Cache effects are not modelled; the sum counts each turn's re-sent context, which is the unit that shrinks when the skill file shrinks.

## Procedure
1. Diagnostic (free): decompose BASE tokens on the 21 tune cases into skill-file tokens (SKILL.md read, counted on every later turn it stays in context), patch, and output. Abort rule: if BASE mean T minus its skill-file share is still > 50% of BASE mean T, no skill edit can meet the bar; stop, make no skill edit, commit the bench only.
2. Tuning: at most 3 variants of the skill edit, run on the 21 tune cases only. Choose the cheapest variant with tune mean T <= 50% of BASE tune mean T and tune F1 NEW - TK point difference >= -0.03. If none qualifies, stop: revert, commit the bench only. Held-out is not run before the final variant is committed. BASE and TK held-out runs are allowed earlier (they are not the edit).
3. Freeze the chosen variant in a commit, then run it once on the 22 held-out cases. No second held-out run, no re-tuning after seeing held-out data.

## Keep rule (held-out, n=22, all must hold)
(a) NEW - TK F1: 95% bootstrap CI lower bound >= -0.05.
(b) No significant precision drop: the NEW - TK precision CI is not entirely below 0 (upper bound >= 0).
(c) Mean T of NEW <= 50% of mean T of BASE on the same 22 cases.
A case that errors after retry is dropped from all arms and reported. If the keep rule is met the skill edit ships; otherwise it is reverted and only this bench is committed.

## Limits
- No paid claude -p call, no Claude spend at all. At most 2 parallel PCSS calls.
- Known limits stated in advance: one run per arm per case; n=22 gives a CI about +-0.13 wide on F1, so (a) can fail even when the true difference is zero; the judges are open models that see only the patch (extra findings may be marked unverifiable and count as not good); Qwen as the host model; a minimal tool loop instead of Claude Code (no skill discovery, no Skill tool: the skill is reached by the prompt's explicit read instruction, as in the earlier bench); nondeterminism at temperature 0 on a shared endpoint.
