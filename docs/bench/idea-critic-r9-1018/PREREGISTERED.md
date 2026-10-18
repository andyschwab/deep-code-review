# idea-critic round 9: one frozen SKILL.md edit, n=150 fresh held-out (2026-10-18)

Written after the tune runs and before any held-out seed, scenario, rival answer or judge call. The tune ledger is `ledger-tune.jsonl`; the held-out ledger `ledger.jsonl` starts with the `preregistered` event whose `sha256` is the hash of `SHA256-frozen.txt`.

## 1. Loss analysis (tune input)

The v0 skill (current `.claude/skills/idea-critic/SKILL.md`, byte copy in `prompts/perun_idea-critic_v0.txt`) lost or tied the rival in rounds 5 to 8; those sets are spent and used only as tune. `losses.py` clusters the judge reasons of every v0 loss (final = rival) by keyword, deterministically (`losses.txt`): of 39 losses in rounds 5 and 6, 38 mention a trigger or stop condition (TRIG), 32 an arithmetic or recomputed figure (ARITH), 14 a pilot or staged first step (STEP); of 56 losses in rounds 7 and 8: 53, 38 and 35. TRIG is close to universal because the judge prompt itself asks about the stop trigger, so the ranking TRIG > ARITH > STEP is weak evidence; it is the preregistered order anyway. The clusters overlap and the keyword rule is rough.

## 2. Candidate edits and the selection rule (tune, n=80)

Tune set: the 40 round-5 and 40 round-6 held-out scenarios, their frozen rival answers, and the v0 judge records already written in those rounds (identical v0 text apart from the version stamp). Candidates (built by `mkcands.py` from the v0 prompt):

- c9a, step 5 only (ARITH): recompute the requester's figures (totals, units x duration against capacity, ROI and payback, calendar), open the answer with each mismatch and its corrected number, size the call from the corrected figures (+188 bytes).
- c9b, step 6 only (TRIG and STEP): a capped, time-boxed first step when real money is committed; kill criteria are one metric with a numeric threshold (the requester's own when given and sound), a date inside the first window, and a named pivot or stop action (+224 bytes). Different from round 8's c8b, which only moved the date.
- c9c: c9a and c9b together (+412 bytes).

Rule (written into `bench9.py` as `TUNE_ORDER`/`tunechoose` before any tune call): take the edit that targets the most frequent loss cluster first, c9b, then c9a, then c9c, and use the first whose tune paired difference over v0 is at least 0; if none, no held-out run. This replaces "highest tune score" so the pick is not the largest of three noisy numbers. Tune result (`CHOICE.json`): v0 0.525 [0.438, 0.613] (27/30/23); c9b 0.512, paired -0.0125 [-0.1125, 0.0875]; c9a 0.512, paired -0.0125 [-0.0938, 0.075]; c9c 0.606 [0.531, 0.681] (30/37/13), paired +0.0813 [-0.0125, 0.175]. c9b and c9a are below 0, so the rule picked c9c, which is also the top score; the winner's-curse risk therefore remains for c9c, and the held-out set is what decides. One tune judge record for c9c (r5-h37) needed a rerun after an unparsed reply; failed network calls from a first attempt blocked by the sandbox (960 error lines, no successful call) were deleted before the real run.

## 3. Held-out design and decision (fixed now)

- Frozen edit: c9c only (`prompts/perun_idea-critic_c9c.txt`). The other arms were tune only.
- Set: 150 fresh fictional scenarios r9-001..r9-150 written by gpt-oss_120b from 150 fresh invented company seeds (`bench9.py seeds`, `scen`), with the voice and the phrasing of the ask drawn per scenario from a fixed RNG so earlier rounds' template tail is not reused. A scenario is kept only if its 6-word shingles overlap at most 0.10 (unrounded, share of its own shingles) with all text in docs/bench outside this directory, the eval fixtures and the idea-critic evals, and with the rest of the batch; ids, company names and exact texts are also disjoint (`bench9.py check`); `python3 scripts/bench_check.py --changed origin/main` must pass.
- Rival: the same gstack plan-ceo-review text as rounds 5 to 8, answers generated once and hashed in `RIVAL-sha256-held.json` before any arm is judged. Arms: v0 and c9c, generator Qwen3.5-397B-A17B with the skill as system prompt (temperature 0.7, under 500 words, as `../exec-1017/prompts/gen_task.txt`).
- Judges: the round 5 to 8 panel (GLM-5.1, GLM-5.2, gpt-oss_120b), judge prompt v2 byte-identical, both answer orders, strict agreement else tie, then majority of three, ties 0.5. Bootstrap 10,000 resamples, seed 1, percentile, over scenarios.
- Ship iff the paired (c9c minus v0) 95% interval lower bound is above 0. Win iff c9c against the rival has a 95% interval lower bound above 0.5. Judged once; no rerun, no second edit, no change of rule after unblinding. If the ship test fails, `.claude/skills/idea-critic/SKILL.md` is unchanged and the result is recorded as a null.
- Power: at n=150 with about 0.35 order disagreement the paired interval half-width is near 0.08, so a true gain below about 0.08 will usually not clear the ship test; tune gave +0.08 at n=80 with a lower bound below 0.

## 4. Caveats stated in advance

Open models on one cluster; system-prompt-only arms; one run per arm; the writer model gpt-oss_120b also judges; scenario sets are model-written and this round's phrasing varies more than earlier rounds, so rates are not strictly comparable with rounds 5 to 8; the tune baseline for v0 is one earlier sample per scenario; the edit text was written after reading the loss reasons.
