# Pre-registration: CF (Perun small-diff review) vs TK (Anthropic pr-review-toolkit code-reviewer)

Written 2026-10-16 (run date 2026-10-15/16) BEFORE any arm output was produced. Do not edit after the first reviewer call; deviations go in DEVIATIONS.md.

## Hypothesis
CF has higher verified precision than TK on a fresh corpus. The earlier pooled result (+.039, CI [-.018, +.098], n=62) was not significant; its raw data is lost.

## Materials (frozen)
- Source: origin/main at the SHA in src/ORIGIN_MAIN_SHA (fetched at run start).
- Corpus: scripts/eval-fixtures/bench/train/ (43 case directories on disk; manifest.json lists 44 train ids, the 44th, the public PR #1354 held-out fixture, is not stored in that directory and is excluded). Each case: change.patch (reviewer sees this only), ground-truth.json, meta.json. No context/ directories exist in train, so the verifier also sees only the patch.
- CF system prompt: prompts/cf_system.md = .claude/skills/deep-code-review/references/compact-mode.md with the two routing lines above "You are a senior reviewer" removed.
- TK system prompt: prompts/tk_system.md = plugins/pr-review-toolkit/agents/code-reviewer.md from github.com/anthropics/claude-code main (raw SHA-256 recorded in prompts/tk_raw.sha256), frontmatter stripped.
- Same user prompt for both arms: the runner's PRODUCER (scripts/bench_corpus.py), which requests a final-message-only JSON array of findings {file, line, severity, text}. Same opaque temp workspace holding only change.patch.
- Reviewer: `claude -p --model claude-sonnet-5-5 --system-prompt <arm prompt> --strict-mcp-config --setting-sources project,local --tools Read,Grep,Glob --allowedTools Read Grep Glob --no-session-persistence --output-format json`. One run per arm per case (rep 1).
- Judge: claude-opus-5-5 (different strength), same read-only flags, runner's VERIFY prompt, run per arm per case, blind to arm. It labels only strict-unmatched findings (runner scorer, score_review.sr.score per finding) as real | gt_same | not_a_bug | unverifiable.

## Metrics
- Strict match: score_review.score (file basename + mechanism regex).
- Good finding = strict-matched OR labelled real OR gt_same. Verified precision = good findings / findings, pooled over cases (ratio of sums). Missing/unverifiable verdict = not good.
- Adjudicated recall = bugs credited / bugs, credit when a finding strict-matches or the judge labels one gt_same.
- Errored case (reviewer error after one retry, or verifier error after one retry): the case is dropped from BOTH arms (paired). n and drops are reported.

## Decision rules
- PRIMARY: precision difference D = CF - TK. Case-level paired bootstrap, 10000 resamples with replacement of cases, seed 1 (Python random.Random(1)), statistic recomputed as pooled ratio per resample, 95% percentile CI (2.5th, 97.5th). Met iff point D > 0 and CI lower bound > 0.
- SECONDARY: adjudicated recall difference CF - TK point estimate >= -0.03 (CI reported, not gated).
- OVERALL PASS iff primary AND secondary met. Otherwise FAIL. A not-significant primary is FAIL, not "directional".
- POOLED (approximate): case-count-weighted average of the new n and the earlier n=62 point values from docs/perun-vs-rivals.md (CF .951, TK .912; adjudicated recall .258 vs .274 pooled). The earlier raw data is lost, so no CI is computed; possible case overlap with the old set is unknown. Reported as approximate and not a decision input.

## Budget and conduct
- Hard cap $20 total (reviewer + judge + retries), ledger.jsonl in this dir, cost taken from each call's total_cost_usd, checked before every call with a reserve for in-flight calls; on reaching the cap the run stops and reports a partial result as INCOMPLETE. No plan-usage gate. Foreground, jobs=4.
- Known limits stated in advance: single run per arm (sampling noise), n<=43, judge is Claude-family, judge lacks pre-fix context, ground truth has one bug per case so "real" extras are judge opinion, ordering/thread nondeterminism. TK's prompt targets CLAUDE.md compliance and uses confidence >= 80; CF has an explicit confidence >= 80 floor too.
