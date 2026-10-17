Loss-fix re-test, 2026-10-17. Cost: $0 (free PCSS models only; ledger.jsonl has every call's token usage).

BLUF
- product-discovery: KEEP the edit. Win rate against the rival 0.800, 95% CI [0.700, 0.900], n=20, primary judge DeepSeek-V4-Flash, both orders. Meets the frozen rule (lower bound above 0.5). The unedited skill scored 0.675 [0.550, 0.800] on the same scenarios, so the edit's own share is about +0.125 and the intervals overlap. Do not read this as "the edit alone turned a loss into a win".
- communication-structure: REVERT the edit. Win rate 0.175 [0.075, 0.275], n=20. The unedited skill scored 0.150 [0.050, 0.275]. The edit changed nothing measurable and neither version beats humanizer on this host. No cs change is committed; only the bench.

Setup (PREREGISTERED.md, hashes in SHA256-frozen.txt and SHA256-amend.txt)
- Generator for all arms: Qwen3.5-397B-A17B, temperature 0.7, max_tokens 3000, thinking off. Arms: PERUN (edited skill), BASE (skill before the edit, descriptive only), RIVAL (humanizer v3.1.0; phuryn/pm-skills).
- 20 fresh scenarios per skill, written by GLM-5.1 from the earlier writer briefs (scenarios_cs.json, scenarios_pd.json). Outputs in outputs/, verdicts in judge/.
- Judges: rubric-free and blind. DeepSeek-V4-Flash is the primary judge and judged every pair in both orders. GLM-5.2 was run on the same basis but finished only part of the pairs (see below).
- Scoring (amendment 4): a scenario counts as a win or loss only when both orders pick the same arm; a split or tie is 0.5. CI: bootstrap over scenarios, 10,000 resamples, seed 1, percentile.

Results (results_cs.json, results_pd.json)
- cs PERUN vs RIVAL, DeepSeek: 0.175 [0.075, 0.275]; 0 clear wins, 13 clear losses, 7 splits or ties. FAIL.
- cs PERUN vs RIVAL, GLM-5.2: n=13 of 20, 0.231 [0.038, 0.462]. Incomplete; same direction.
- cs BASE vs RIVAL, DeepSeek: 0.150 [0.050, 0.275].
- pd PERUN vs RIVAL, DeepSeek: 0.800 [0.700, 0.900]; 12 clear wins, 0 clear losses, 8 splits or ties. PASS.
- pd PERUN vs RIVAL, GLM-5.2: n=5 of 20, 5 clear wins. Too few to read; not used.
- pd BASE vs RIVAL, DeepSeek: 0.675 [0.550, 0.800]; 8 clear wins, 1 clear loss, 11 splits or ties.

Position bias (position_bias.json): slot-1 rate, the share of verdicts that picked Response 1 (0.5 means none). DeepSeek-V4-Flash 0.581 over 160 verdicts (11 ties); GLM-5.2 0.500 over 52 verdicts (0 ties). A Qwen3.5 judge was tried earlier and picked slot 1 in 169 of 240 cases, so it was dropped as a judge (it is the generator and may not judge). The slot-1 rate depends on tie handling: for DeepSeek it is 0.581 counting ties as not-slot-1 and 0.624 excluding the 11 ties (pd 0.609 excluding ties, cs 0.6375), both above 0.6, so it does favor slot 1. Both-order scoring cancels this bias, because each arm sits in each slot once per scenario and only agreement across the two orders counts.

Caveats
- The host and the judges are non-Claude models. Both skills were written and tuned against Claude. A pass here does not show the skill wins on Claude; a fail does not show it loses there. Rates are not comparable with H1d (product-discovery-rubricfree-1016) or H1e (comms-quality-1016), which used a Claude judge.
- GLM-5.2 coverage is partial: it reasons at length and is slow, so each timed run (a fixed BUDGET of seconds, no new call after it) finished only a few of its pairs; of 65 GLM-5.2 calls in the ledger, 5 returned empty and 6 hit a server or read error, the rest succeeded. The primary-judge rule was therefore applied on DeepSeek alone. Cross-judge agreement for pd is untested.
- Amendments 1 to 4 (SHA256-amend.txt) were made after the freeze: 1 to 3 are driver fixes (batching, foreground runs, token limits). Amendment 4 replaced the preregistered GLM-5.2 tiebreak with both-order scoring post hoc, after partial results were seen, on the coordinator's instruction.
- n=20 per skill, one scenario set, sampling not seeded, no lint-and-rewrite loop for communication-structure, product-discovery references unavailable (no tools).
- ledger.jsonl rows with errors early in the log are sandbox refusals (HTTP 403 on the tunnel) from backgrounded runs, not model failures; they cost nothing and were retried.
- docs/perun-vs-rivals.md is deliberately not edited by this change.
