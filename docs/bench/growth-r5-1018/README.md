# growth-analytics round 5, one edit, held-out n = 150, 2026-10-18

BLUF: NO VERDICT, NOT SHIPPED, NOT A WIN. By the preregistered rule the judge is the first of GLM-5.1, GLM-5.2 and gpt-oss_120b whose pooled slot-1 rate is in 0.4 to 0.6, and none qualified (0.623, 0.659, 0.673), so there is no verdict and `SKILL.md` is unchanged. For the record, GLM-5.1 (not a valid judge under the rule) scored the edit (v1, candidate C3) 0.570 [0.510, 0.630] against the marketingskills analytics and ab-testing rival (53 wins, 65 ties or splits, 32 losses) and the shipped round-4 text (v0) 0.537 [0.473, 0.600] (52 / 57 / 41); paired difference (v1 minus v0) +0.033, 95% bootstrap CI [-0.037, 0.100] (150 of 150 scored). The paired lower bound is below 0, so the keep rule would not have been met either, and the win-rate lower bound (0.510) is above 0.5 only on a judge that is excluded; a win would need the keep rule as well, so none is claimed. Spend $0.00 (PCSS only).

- Rule, arms, scenario drawing, tuning log: `PREREGISTERED.md`. Hash lists: `SHA256-prereg.txt` (after the tuning phase, before any held-out seed) and `SHA256-frozen.txt` (after the held-out scenarios, before any held-out answer). `ledger.jsonl` records the hash of `SHA256-frozen.txt` first, then `run_start`, then the results hash (`used`, `keep` and `superior` are null: no healthy judge). Tuning runs are in `ledger-tune.jsonl`, never in `ledger.jsonl`.
- Tested text: `frozen/growth-analytics.v1.md` (candidate C3). Against v0 it adds one passage to method step 8 ("Apply the stated numbers": the arithmetic of the net per-visitor or per-unit effect, the break-even and the gap to it, and a table of result, action and what to tell the named audience, before any general framework) and removes three Definition-of-done bullets that restate step 2, step 3 and the Prime directive; 10507 bytes against 10601 for v0 (budget 10795). v0 is `frozen/growth-analytics.v0.md`, the SKILL.md on origin/main at 28660c0d. The rival text is the committed `docs/bench/growth-analytics-rubricfree-1016/prompts/rival.txt`.
- Source of the edit: `losses.py` re-judged the 150 spent round-4 held-out v1-versus-rival pairs (300 orders: 133 rival wins, 167 skill wins) and kept the judge analyses of the 133 rival wins; I read a random sample of 40. The reasons are in `PREREGISTERED.md`: the rival applies the stated numbers and shows a decision framework, it is more buildable (exact events, de-duplication and session rules, a reconciliation check, a dated schedule), and the skill sometimes steps outside a limit the requester stated. C1 targets the last, C2 the buildability, C3 the applied numbers. Tune paired differences against v0 (n=60, exploratory): C1 +0.067 [-0.058, 0.192], C2 +0.067 [-0.042, 0.175], C3 +0.083 [-0.025, 0.200]; C3 was picked by the round-4 rule (highest; ties to the smaller text). No tune interval excluded 0.
- Scenarios: `scenarios-heldout.json` (ids gz001 to gz150) from `prompts/seeds-heldout.txt`; the largest 6-word shingle overlap of any scenario is 0.096 against every text file of docs/bench on origin/main (rounds 1 to 4 included, outputs and judge records excluded), 0.036 against the tune scenarios and 0.081 against another held-out scenario; 150 distinct ids; `scripts/bench_check.py --changed origin/main` passes.
- Raw outputs and verdicts: `results/outputs`, `results/judge-verdicts.json` (every verdict kept, all three judges), `results/verdict.json`. Reproduce: `python3 docs/bench/growth-r5-1018/bench.py run <out>` then `fold <out>` (PCSS key from the repo `.env`).

| Judge (all outside the 0.4 to 0.6 gate) | Slot-1 | v0 | v1 | Paired diff [95% CI] |
|---|---|---|---|---|
| GLM-5.1 | 0.623 | 0.537 [0.473, 0.600] (52 / 57 / 41) | 0.570 [0.510, 0.630] (53 / 65 / 32) | +0.033 [-0.037, 0.100] |
| GLM-5.2 | 0.659 | 0.543 [0.483, 0.607] (51 / 61 / 38) | 0.497 [0.437, 0.557] (42 / 65 / 43) | -0.047 [-0.123, 0.027] |
| gpt-oss_120b | 0.673 | 0.407 [0.347, 0.470] (33 / 56 / 61) | 0.460 [0.400, 0.520] (36 / 66 / 48) | +0.053 [-0.013, 0.120] |

No judge's paired interval excludes 0, and the three point estimates disagree in sign (+0.033, -0.047, +0.053). The edit is not shown better or worse than v0 on this set.

## What this says

- Nothing shipped: no healthy judge, so no verdict. Even read on the least biased judge (GLM-5.1, slot-1 0.623, just above the gate), the paired lower bound is -0.037. The confirmed-win count in `docs/perun-vs-rivals.md` is unchanged.
- The shipped round-4 text scored 0.537 on this fresh set against the rival (round 4: 0.550 on its set), so the shipped text holds up on a second fresh set under GLM-5.1; the sets are not pooled and the judge here is outside the gate, so this is a lead, not a replication.
- All three judges leaned to the first slot on this run (0.62 to 0.67), a larger bias than round 4's 0.600 on the same GLM-5.1; round 4's held-out was already at the top edge of the gate. Slot-1 behaviour moves from set to set for the same judge, which is why the gate decides, not the point estimates.

## Disclosures

- Deviations from the round-4 protocol: ids use new prefixes (`gk` tune, `gz` held-out) and the tune cache directory is renamed in `bench.py`; `losses.py` reads the round-4 held-out; `mkcand.py` is new (three new candidates, a different shared de-duplication); the round-4 retry-hint change in `write_batch` was kept from the start. Nothing else in the harness changed.
- The candidate-selection rule (highest tune paired difference, ties to the smaller text) is the round-4 rule; I did not restate it in a file before the tune runs, it is stated in `PREREGISTERED.md` as written after them. It was fixed in the harness conventions of round 4 and I applied it unchanged. The "tune seeds" are fresh seeds drawn by the writer model (rejected when close to any existing seed), not seeds copied from the loss analyses; the losses fed the candidate wording only.
- The loss sample (40 of 133, seed 5) is a read, not a measurement; one re-judge pass (GLM-5.1, protocol v2).
- Tune slot-1 rates were 0.586 (C1), 0.594 (C2) and 0.636 (C3, outside the gate); the tune result is exploratory and the picked candidate's tune judge was biased.
- No healthy judge was found, so the decision fields are null. The harness always scores all three judges; the table shows all of them as sensitivity, none used.
- The run took about an hour of wall time (PCSS only, no retries beyond the harness's own); some scenario batches needed writer retries for the overlap check (no batch failed). The held-out scenario writer, seeds and judge calls were made only after `SHA256-frozen.txt` and the first `ledger.jsonl` line existed.
- `SKILL.md` and `evals.json` are not changed, so there is no byte comparison of tested versus shipped text.

## Caveats

Qwen3.5-397B-A17B generates every arm (not necessarily the model the skill runs on); judges are PCSS models of other families and all three were position-biased on this set; one rival; one run per arm; scenarios are fictional and written by one blind writer model. A "not shipped" result means the preregistered rule was not met on this synthetic distribution, not a claim about real users.
