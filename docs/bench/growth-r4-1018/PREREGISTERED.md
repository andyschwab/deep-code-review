# Preregistration: growth-analytics round 4, one edit, held-out n=150 (2026-10-18)

This file, the harness and the frozen texts are hashed (`SHA256-prereg.txt`) after the tuning phase and before any held-out seed, scenario or answer exists. The scenario hashes follow in `SHA256-frozen.txt`; its hash is the first line of `ledger.jsonl`, before any held-out answer or judge call. Every model call goes to the PCSS endpoint ($0); no `claude -p`; all scenarios are fictional.

Scenarios file: scenarios-heldout.json

## Question

Round 3 (`docs/bench/growth-r3-1018`) shipped one edit: 0.513 [0.450, 0.577] against the marketingskills analytics and ab-testing rival, paired +0.090 [0.017, 0.163] over the text before it, so the paired rule was met and no win was claimed (the win-rate lower bound was 0.450). This round mines the judge reasons for the pairs where the round-3 text still lost, drafts at most three candidate edits, picks one on a fresh tune set by a rule fixed in advance, and tests it once on a fresh n=150 set. v0 here is the shipped round-3 text, `.claude/skills/growth-analytics/SKILL.md` on origin/main at 85a0d84f, which is `docs/bench/growth-r3-1018/frozen/growth-analytics.v1.md` plus one eval id in the Verification list (`frozen/growth-analytics.v0.md`, 10706 bytes).

Does v1 beat v0 against the same rival, and does v1 beat the rival?

## Where the edits come from (round-3 losses)

Round 3 committed verdicts but not judge reasons, so `losses.py` re-judged the 150 spent round-3 held-out v1-versus-rival pairs (GLM-5.1, protocol v2, both orders, analysis text kept; 300 orders) and kept the analyses of the 145 orders the rival won (not committed; the reasons are summarised here). I read a random sample of 45. Counts by keyword over all 145 are in the author's scratch regex and are approximate leads, not measurements (clusters overlap): the rival is described as more granular, specific, comprehensive or detailed 45; the rival gives concrete thresholds, targets or success criteria, or the skill declines to 17; the rival is tailored to an audience, format or deadline the requester named (board, director, deadline) 94 (a broad regex); the skill dismisses or swaps the requester's own metric or option (vanity, North Star, ignores what was asked) 40; the skill adds material nobody asked for (privacy or compliance notes, a stop tripwire, UNVERIFIED relabelling, peeking or statistics points) 40; the skill is rigid or impractical against an urgency or deadline, or answers with a bare wait or re-run 23; the rival's decision matrix, next steps or scenarios 111; the skill is faulted for an incorrect or flawed point 30.

In the sample read, the round-3 text's remaining losses fall in four groups: (1) it replaces the requester's metric, target or constraint with its own North Star or adds notes the decision does not turn on; (2) it is less specific than the rival: fewer named events, formulas, thresholds, sample sizes or dates computed from the figures in the request; (3) its call does not fit the stated deadline or constraint (a bare wait or re-run where the rival proposes a short canary, a partial rollout or a re-run length computed from the traffic), and it declares contaminated data unusable without saying what can be salvaged; (4) occasional arithmetic or logic slips, which prose in the skill cannot target and no candidate addresses.

## Tuning phase (before this file; logged in `ledger-tune.jsonl`)

One fresh tune set of 60 scenarios (ids `gq01` to `gq60`, `scenarios-tune.json`; seeds rejected when close to any earlier seed). All three candidates share one de-duplication that keeps the skill inside its byte budget (10795): the Definition-of-done bullet that restates the identifier seam of step 3, two Anti-rationalization rows that restate the Prime directive and step 3, and a shortened third bullet in the boundary section; step 7 is also reworded shorter. `mkcand.py` rebuilds the candidate files in `prompts/candidates/` from `frozen/growth-analytics.v0.md`. Tune runs used GLM-5.1 only, both orders, v2 protocol, are exploratory, and the judge's slot-1 rate was 0.64 to 0.66 (outside the 0.4 to 0.6 gate that applies to the held-out run). Paired difference against v0 (same rival answers; v0 scored 0.483 against the rival on this tune set), n = 60 (C3: 59 scored):

| Candidate | Change (plus the shared de-duplication) | Bytes | Paired diff vs v0 [95% CI] |
|---|---|---|---|
| C1 | step 7 ends "Build on the metric, target or constraint they stated instead of swapping in your own North Star; add an identifier, benchmark, tripwire, UNVERIFIED or statistics note only when the decision turns on it, in one line" | 10392 | +0.042 [-0.050, 0.133] |
| C2 | step 8 adds "Make it runnable": events with properties, formulas, thresholds, sample sizes and dates computed from the stated figures; fit the call to the stated deadline and constraint (a short canary, a partial rollout) rather than a bare wait or re-run; say what can be salvaged from contaminated data | 10566 | +0.050 [-0.058, 0.158] |
| C3 | C1 plus C2 | 10787 | -0.017 [-0.136, 0.102] |

The candidate selection rule was stated before the runs (highest tune paired difference; ties to the smaller text); it picks C2. The tune judge was position-biased (slot-1 above 0.6), no tune interval excludes 0 and the three differences are within the 0.09 that an identical-text re-run moved the tune estimate in round 2, so the tune result is a lead, not evidence: C2 is shipped only if the held-out keep rule below holds. Candidates were not tuned further after seeing the tune result.

## Arms and data

- v0 = `frozen/growth-analytics.v0.md`. v1 = `frozen/growth-analytics.v1.md` (candidate C2), which will be byte-identical to the edited SKILL.md only if the keep rule holds (plus the one eval id that a shipped edit adds to the Verification list, which changes no text the arms see). Both are final: no further tuning, no edit after the held-out result.
- Rival: the committed text `docs/bench/growth-analytics-rubricfree-1016/prompts/rival.txt`, hashed in the frozen list. Its answer to each scenario is generated once and shared by both skill arms, so (v1 minus v0) is paired on identical rival text.
- Scenarios: 150 fresh held-out scenarios (ids `gy001` to `gy150`, a prefix no earlier bench uses), seeds drawn by the blind writer model (Qwen3.5-397B-A17B, temperature 0.9) and rejected if close to any seed in `docs/bench` (including rounds 1 to 3 and the tune seeds); scenarios are written in batches of 10 from the existing writer brief `docs/bench/growth-analytics-rubricfree-1016/prompts/writer_brief.txt` (no skill text shown). Any scenario sharing more than 10% of its 6-word shingles with the `docs/bench` corpus on origin/main (every scenario, seed and record file, including rounds 1 to 3), with the tune scenarios, or with another held-out scenario is regenerated before freezing. `scripts/bench_check.py --changed origin/main` must pass.
- Generator for all arms: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, the harness GEN_TASK wrapper, never a judge.
- Judge: protocol v2 of `scripts/rival_eval.py` unchanged (random three-letter labels, analysis before verdict, both orders). The judge is the first of GLM-5.1, GLM-5.2, gpt-oss_120b whose slot-1 rate, pooled over both arms, is in 0.4 to 0.6; the same judge scores both arms. No healthy judge means no verdict, which means do not ship. A scenario scores 1 when the arm wins in both orders, 0 when it loses in both, else 0.5. Other judges are reported as sensitivity only.

## Decision rule (stated before any held-out call)

- KEEP (ship the SKILL.md edit) only if, with at least 135 of 150 scenarios scored by a healthy judge, the paired difference (v1 minus v0 win rate, mean of per-scenario score differences) has a 95% bootstrap CI (10,000 resamples over scenarios, percentile, seed 1) whose lower bound is above 0. Otherwise SKILL.md is not edited and only this bench record is committed.
- Superiority over the rival is claimed only if v1's win-rate CI (same bootstrap) has a lower bound above 0.5. A win claim requires the keep rule as well: an unshipped text is not claimed as a win.
- One run per arm; no re-runs, no judge swapping, no scenario edits after seeing a result. Records are never overwritten.

## Known limits

Single generator family writes the scenarios and all answers; judges are models; scenarios are fictional; one rival. Tune noise is large and the tune judge was position-biased, so the tune set cannot rank candidates reliably. The round-3 loss reasons come from a single re-judge pass and are keyword-counted. A FAIL means "not shown better under this judge on this synthetic distribution", not a claim about real users.
