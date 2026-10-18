# Preregistration: growth-analytics round 5, one edit, held-out n=150 (2026-10-18)

This file, the harness and the frozen texts are hashed (`SHA256-prereg.txt`) after the tuning phase and before any held-out seed, scenario or answer exists. The scenario hashes follow in `SHA256-frozen.txt`; its hash is the first line of `ledger.jsonl`, before any held-out answer or judge call. Every model call goes to the PCSS endpoint ($0); no `claude -p`; all scenarios are fictional.

Scenarios file: scenarios-heldout.json

## Question

Round 4 (`docs/bench/growth-r4-1018`) shipped one edit: 0.550 [0.483, 0.617] against the marketingskills analytics and ab-testing rival, paired +0.100 [0.030, 0.170] over the text before it; the paired rule was met and no win was claimed (win-rate lower bound 0.483). This round mines the judge reasons for the pairs where the round-4 text still lost, drafts three candidate edits, picks one on a fresh tune set by the round-4 rule, and tests it once on a fresh n=150 set. v0 here is the shipped round-4 text, `.claude/skills/growth-analytics/SKILL.md` on origin/main at 28660c0d (`frozen/growth-analytics.v0.md`, 10601 bytes).

Does v1 beat v0 against the same rival, and does v1 beat the rival?

## Where the edits come from (round-4 losses)

`losses.py` re-judged the 150 spent round-4 held-out v1-versus-rival pairs (GLM-5.1, protocol v2, both orders, analysis text kept; 300 orders: 133 rival wins, 167 skill wins) and kept the analyses of the 133 orders the rival won (not committed; the reasons are summarised here). I read a random sample of 40 (seed 5). In the sample, the round-4 text still loses for these reasons: (1) the rival applies the stated numbers and shows the arithmetic and a decision framework (break-even, net per-visitor effect, a table of result and action), where the skill stays conceptual or leaves the figures unapplied (gy005, gy065, gy119, gy141); (2) the rival is more buildable: exact event and property names, session-timeout and de-duplication rules, filters for accidental actions, a reconciliation check, a day-by-day schedule to the deadline (gy048, gy087, gy116, gy035, gy097); (3) the skill steps outside a limit the requester stated (a recommendation when told to stay neutral, a metric or tool the requester did not mention, new tracking when existing data was the constraint) (gy056, gy060, gy071, gy086, gy105); (4) arithmetic slips and invented round thresholds, which prose in the skill cannot target and no candidate addresses. Counts are a sample read, not measurements.

## Tuning phase (before this file; logged in `ledger-tune.jsonl`)

One fresh tune set of 60 scenarios (ids `gk01` to `gk60`, `scenarios-tune.json`; seeds rejected when close to any earlier seed, scenarios rejected above 10% 6-word shingle overlap with the docs/bench corpus). The candidates share one de-duplication that keeps the skill inside its byte budget (10795): three Definition-of-done bullets that restate step 2, step 3 and the Prime directive are removed. `mkcand.py` rebuilds the candidate files in `prompts/candidates/` from `frozen/growth-analytics.v0.md`. Tune runs used GLM-5.1 only, both orders, v2 protocol, are exploratory. Paired difference against v0 (same rival answers; v0 scored 0.483 against the rival on this tune set), n = 60:

| Candidate | Change (plus the shared de-duplication) | Bytes | Slot-1 | Paired diff vs v0 [95% CI] |
|---|---|---|---|---|
| C1 | step 7: obey each limit the requester states (no recommendation, no tooling advice, a team size or hours, existing data only); add nothing outside it | 10456 | 0.586 | +0.067 [-0.058, 0.192] |
| C2 | step 8: spell out the build (exact event and property names, session-timeout and de-duplication rules, filters for accidental or duplicate actions, a reconciliation check, a dated schedule before the deadline) | 10550 | 0.594 | +0.067 [-0.042, 0.175] |
| C3 | step 8: apply the stated numbers (show the arithmetic, the break-even and the gap to it) and give a table of result, action and what to tell the named audience, before any framework | 10507 | 0.636 | +0.083 [-0.025, 0.200] |

Selection rule (the round-4 rule, unchanged in the harness; I did not restate it in a file before the tune runs): highest tune paired difference, ties to the smaller text. It picks C3. No tune interval excludes 0 and the three differences are within the noise an identical-text re-run showed in round 2 (0.09), so the tune result is a lead, not evidence: C3 is shipped only if the held-out keep rule below holds. Candidates were not tuned further after seeing the tune result.

## Arms and data

- v0 = `frozen/growth-analytics.v0.md`. v1 = `frozen/growth-analytics.v1.md` (candidate C3), which will be byte-identical to the edited SKILL.md only if the keep rule holds (plus the one eval id that a shipped edit adds to the Verification list, which changes no text the arms see). Both are final: no further tuning, no edit after the held-out result.
- Rival: the committed text `docs/bench/growth-analytics-rubricfree-1016/prompts/rival.txt`, hashed in the frozen list. Its answer to each scenario is generated once and shared by both skill arms, so (v1 minus v0) is paired on identical rival text.
- Scenarios: 150 fresh held-out scenarios (ids `gz001` to `gz150`, a prefix no earlier bench uses), seeds drawn by the blind writer model (Qwen3.5-397B-A17B, temperature 0.9) and rejected if close to any seed in `docs/bench` (including rounds 1 to 4 and the tune seeds); scenarios are written in batches of 10 from the existing writer brief `docs/bench/growth-analytics-rubricfree-1016/prompts/writer_brief.txt` (no skill text shown). Any scenario sharing more than 10% of its 6-word shingles with the `docs/bench` corpus on origin/main (every scenario, seed and record file, including rounds 1 to 4), with the tune scenarios, or with another held-out scenario is regenerated before freezing. `scripts/bench_check.py --changed origin/main` must pass.
- Generator for all arms: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, the harness GEN_TASK wrapper, never a judge.
- Judge: protocol v2 of `scripts/rival_eval.py` unchanged (random three-letter labels, analysis before verdict, both orders). The judge is the first of GLM-5.1, GLM-5.2, gpt-oss_120b whose slot-1 rate, pooled over both arms, is in 0.4 to 0.6; the same judge scores both arms. No healthy judge means no verdict, which means do not ship. A scenario scores 1 when the arm wins in both orders, 0 when it loses in both, else 0.5. Other judges are reported as sensitivity only.

## Decision rule (stated before any held-out call)

- KEEP (ship the SKILL.md edit) only if, with at least 135 of 150 scenarios scored by a healthy judge, the paired difference (v1 minus v0 win rate, mean of per-scenario score differences) has a 95% bootstrap CI (10,000 resamples over scenarios, percentile, seed 1) whose lower bound is above 0. Otherwise SKILL.md is not edited and only this bench record is committed.
- Superiority over the rival is claimed only if v1's win-rate CI (same bootstrap) has a lower bound above 0.5. A win claim requires the keep rule as well: an unshipped text is not claimed as a win.
- One run per arm; no re-runs, no judge swapping, no scenario edits after seeing a result. Records are never overwritten.

## Known limits

Single generator family writes the scenarios and all answers; judges are models; scenarios are fictional; one rival. Tune noise is large (the tune judge was position-biased for C3), so the tune set cannot rank candidates reliably. The round-4 loss reasons come from a single re-judge pass and a 40-order sample read. A FAIL means "not shown better under this judge on this synthetic distribution", not a claim about real users.
